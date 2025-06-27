from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Sum, Avg, Count
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from io import BytesIO
import xlsxwriter
from datetime import datetime

from .models import Employee, Allowance, AllowanceType,EmployeeCategory
from .forms import EmployeeForm, AllowanceFormSet, ReportFilterForm, ExcelImportForm
from .utils import import_employees_from_excel, export_template_excel


@login_required
def employee_list(request):
    """عرض قائمة الموظفين"""
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    nationality_filter = request.GET.get('nationality', '')
    
    employees = Employee.objects.filter(is_active=True)
    
    # تطبيق المرشحات
    if search_query:
        employees = employees.filter(
            Q(name__icontains=search_query) |
            Q(employee_number__icontains=search_query) |
            Q(id_number__icontains=search_query)
        )
    
    if category_filter:
        employees = employees.filter(category=category_filter)
    
    if nationality_filter:
        employees = employees.filter(nationality=nationality_filter)
    
    employees = employees.order_by('employee_number')
    
    # تقسيم الصفحات
    paginator = Paginator(employees, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # إحصائيات سريعة
    stats = {
        'total_employees': Employee.objects.filter(is_active=True).count(),
        'total_monthly_cost': sum(emp.get_monthly_gross_salary() for emp in Employee.objects.filter(is_active=True)),
        'categories': Employee.objects.values('category').annotate(count=Count('id')).order_by('category'),
        'nationalities': Employee.objects.values('nationality').annotate(count=Count('id')).order_by('nationality')
    }
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'category_filter': category_filter,
        'nationality_filter': nationality_filter,
        'stats': stats,
        'categories': Employee.CATEGORY_CHOICES,
        'nationalities': Employee.objects.values_list('nationality', flat=True).distinct().order_by('nationality')
    }
    
    return render(request, 'employees/employee_list.html', context)


@login_required
def employee_detail(request, pk):
    """عرض تفاصيل الموظف"""
    employee = get_object_or_404(Employee, pk=pk)
    allowances = employee.allowances.filter(is_active=True).select_related('allowance_type')
    
    # حساب الإحصائيات
    monthly_allowances = employee.get_total_monthly_allowances()
    monthly_gross = employee.get_monthly_gross_salary()
    annual_cost = employee.get_annual_total_cost()
    cost_factor = employee.get_cost_factor()
    
    context = {
        'employee': employee,
        'allowances': allowances,
        'monthly_allowances': monthly_allowances,
        'monthly_gross': monthly_gross,
        'annual_cost': annual_cost,
        'cost_factor': cost_factor,
    }
    
    return render(request, 'employees/employee_detail.html', context)


@login_required
def employee_create(request):
    """إضافة موظف جديد"""
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        allowance_formset = AllowanceFormSet(request.POST, prefix='allowances')
        
        if form.is_valid() and allowance_formset.is_valid():
            try:
                employee = form.save()
                
                # حفظ البدلات
                allowances = allowance_formset.save(commit=False)
                for allowance in allowances:
                    allowance.employee = employee
                    allowance.save()
                
                # حذف البدلات المحددة للحذف
                for obj in allowance_formset.deleted_objects:
                    obj.delete()
                
                messages.success(request, f'تم إضافة الموظف {employee.name} بنجاح')
                return redirect('employees:employee_detail', pk=employee.pk)
            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء حفظ البيانات: {str(e)}')
        else:
            if not form.is_valid():
                messages.error(request, 'يرجى تصحيح الأخطاء في بيانات الموظف')
            if not allowance_formset.is_valid():
                messages.error(request, 'يرجى تصحيح الأخطاء في بيانات البدلات')
    else:
        form = EmployeeForm()
        allowance_formset = AllowanceFormSet(queryset=Allowance.objects.none(), prefix='allowances')
    
    # الحصول على أنواع البدلات للقالب
    allowance_types = AllowanceType.objects.filter(is_active=True)
    
    context = {
        'form': form,
        'allowance_formset': allowance_formset,
        'allowance_types': allowance_types,
        'title': 'إضافة موظف جديد'
    }
    
    return render(request, 'employees/employee_form.html', context)


@login_required
def employee_edit(request, pk):
    """تعديل بيانات الموظف"""
    employee = get_object_or_404(Employee, pk=pk)
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, instance=employee)
        allowance_formset = AllowanceFormSet(request.POST, instance=employee, prefix='allowances')
        
        if form.is_valid() and allowance_formset.is_valid():
            form.save()
            allowance_formset.save()
            
            messages.success(request, f'تم تحديث بيانات الموظف {employee.name} بنجاح')
            return redirect('employees:employee_detail', pk=employee.pk)
    else:
        form = EmployeeForm(instance=employee)
        allowance_formset = AllowanceFormSet(instance=employee, prefix='allowances')
    
    # الحصول على أنواع البدلات للقالب
    allowance_types = AllowanceType.objects.filter(is_active=True)
    
    context = {
        'form': form,
        'allowance_formset': allowance_formset,
        'allowance_types': allowance_types,
        'employee': employee,
        'title': f'تعديل بيانات {employee.name}'
    }
    
    return render(request, 'employees/employee_form.html', context)


@login_required
def employee_delete(request, pk):
    """حذف الموظف (إلغاء تفعيل)"""
    employee = get_object_or_404(Employee, pk=pk)
    
    if request.method == 'POST':
        employee.is_active = False
        employee.save()
        messages.success(request, f'تم حذف الموظف {employee.name} بنجاح')
        return redirect('employees:employee_list')
    
    context = {
        'employee': employee,
        'title': f'حذف الموظف {employee.name}'
    }
    
    return render(request, 'employees/employee_confirm_delete.html', context)


@login_required
def reports_view(request):
    """عرض التقارير المالية المتقدمة"""
    form = ReportFilterForm(request.GET)
    
    # البدء بجميع الموظفين
    employees = Employee.objects.all()
    
    # تطبيق المرشحات
    if form.is_valid():
        # البحث برقم الموظف أو الاسم
        if form.cleaned_data.get('employee_search'):
            search_term = form.cleaned_data['employee_search']
            employees = employees.filter(
                Q(employee_number__icontains=search_term) |
                Q(name__icontains=search_term)
            )
        
        # تصفية بالجنسية
        if form.cleaned_data.get('nationality'):
            employees = employees.filter(nationality=form.cleaned_data['nationality'])
        
        # تصفية بالفئة
        if form.cleaned_data.get('category'):
            employees = employees.filter(category=form.cleaned_data['category'])
        
        # تصفية بالتاريخ
        if form.cleaned_data.get('date_from'):
            employees = employees.filter(hire_date__gte=form.cleaned_data['date_from'])
        
        if form.cleaned_data.get('date_to'):
            employees = employees.filter(hire_date__lte=form.cleaned_data['date_to'])
        
        # تصفية بحالة النشاط
        if form.cleaned_data.get('is_active'):
            is_active = form.cleaned_data['is_active'] == 'true'
            employees = employees.filter(is_active=is_active)
        
        # تصفية بنطاق الراتب
        if form.cleaned_data.get('salary_min'):
            employees = employees.filter(basic_salary__gte=form.cleaned_data['salary_min'])
        
        if form.cleaned_data.get('salary_max'):
            employees = employees.filter(basic_salary__lte=form.cleaned_data['salary_max'])
    
    # ترتيب النتائج
    employees = employees.order_by('employee_number')
    
    # حساب الإحصائيات
    report_data = generate_report_data(employees)
    
    # إضافة تفاصيل إضافية للتقرير
    report_data['filter_applied'] = any(form.cleaned_data.values()) if form.is_valid() else False
    report_data['total_filtered'] = employees.count()
    
    context = {
        'form': form,
        'report_data': report_data,
        'filters': request.GET.dict()
    }
    
    return render(request, 'employees/reports.html', context)


def generate_report_data(employees):
    """توليد بيانات التقرير"""
    total_employees = employees.count()
    total_monthly_cost = sum(emp.get_monthly_gross_salary() for emp in employees)
    total_annual_cost = sum(emp.get_annual_total_cost() for emp in employees)
    avg_cost_factor = sum(emp.get_cost_factor() for emp in employees) / total_employees if total_employees > 0 else 0
    
    # تجميع حسب الفئة
    by_category = {}
    for category_code, category_name in Employee.CATEGORY_CHOICES:
        cat_employees = employees.filter(category=category_code)
        if cat_employees.exists():
            by_category[category_name] = {
                'count': cat_employees.count(),
                'total_monthly': sum(emp.get_monthly_gross_salary() for emp in cat_employees),
                'total_annual': sum(emp.get_annual_total_cost() for emp in cat_employees)
            }
    
    # تجميع حسب الجنسية
    by_nationality = {}
    nationalities = employees.values_list('nationality', flat=True).distinct()
    for nationality in nationalities:
        nat_employees = employees.filter(nationality=nationality)
        by_nationality[nationality] = {
            'count': nat_employees.count(),
            'total_monthly': sum(emp.get_monthly_gross_salary() for emp in nat_employees),
            'total_annual': sum(emp.get_annual_total_cost() for emp in nat_employees)
        }
    
    return {
        'summary': {
            'total_employees': total_employees,
            'total_monthly_cost': total_monthly_cost,
            'total_annual_cost': total_annual_cost,
            'avg_cost_factor': avg_cost_factor
        },
        'by_category': by_category,
        'by_nationality': by_nationality,
        'employees': employees
    }


@login_required
def export_excel(request):
    """تصدير التقارير إلى Excel"""
    # تطبيق نفس المرشحات المستخدمة في التقارير
    form = ReportFilterForm(request.GET)
    employees = Employee.objects.filter(is_active=True)
    
    if form.is_valid():
        if form.cleaned_data.get('nationality'):
            employees = employees.filter(nationality=form.cleaned_data['nationality'])
        
        if form.cleaned_data.get('category'):
            employees = employees.filter(category=form.cleaned_data['category'])
        
        if form.cleaned_data.get('year'):
            year = int(form.cleaned_data['year'])
            employees = employees.filter(hire_date__year__lte=year)
    
    # إنشاء ملف Excel
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    
    # تنسيق الخلايا
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4472C4',
        'font_color': 'white',
        'align': 'center',
        'valign': 'vcenter',
        'border': 1
    })
    
    data_format = workbook.add_format({
        'align': 'center',
        'valign': 'vcenter',
        'border': 1
    })
    
    number_format = workbook.add_format({
        'num_format': '#,##0.00',
        'align': 'center',
        'border': 1
    })
    
    # ورقة التقرير المفصل
    worksheet = workbook.add_worksheet('التقرير المفصل')
    
    # عناوين الأعمدة
    headers = [
        'رقم الموظف', 'الاسم', 'الجنسية', 'الفئة', 'تاريخ التوظيف',
        'الراتب الأساسي', 'البدلات الشهرية', 'الراتب الإجمالي الشهري',
        'التكلفة السنوية', 'المعامل', 'عدد الزوجات', 'عدد الأبناء',
        'تكلفة الاستقدام', 'تكلفة التدريب'
    ]
    
    # كتابة العناوين
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
    
    # كتابة البيانات
    for row, employee in enumerate(employees, start=1):
        worksheet.write(row, 0, employee.employee_number, data_format)
        worksheet.write(row, 1, employee.name, data_format)
        worksheet.write(row, 2, employee.nationality, data_format)
        worksheet.write(row, 3, employee.get_category_display(), data_format)
        worksheet.write(row, 4, employee.hire_date.strftime('%Y-%m-%d'), data_format)
        worksheet.write(row, 5, float(employee.basic_salary), number_format)
        worksheet.write(row, 6, float(employee.get_total_monthly_allowances()), number_format)
        worksheet.write(row, 7, float(employee.get_monthly_gross_salary()), number_format)
        worksheet.write(row, 8, float(employee.get_annual_total_cost()), number_format)
        worksheet.write(row, 9, float(employee.get_cost_factor()), number_format)
        worksheet.write(row, 10, employee.num_wives, data_format)
        worksheet.write(row, 11, employee.num_children, data_format)
        worksheet.write(row, 12, float(employee.recruitment_cost), number_format)
        worksheet.write(row, 13, float(employee.training_cost), number_format)
    
    # تنسيق عرض الأعمدة
    worksheet.set_column('A:A', 15)  # رقم الموظف
    worksheet.set_column('B:B', 25)  # الاسم
    worksheet.set_column('C:C', 15)  # الجنسية
    worksheet.set_column('D:D', 15)  # الفئة
    worksheet.set_column('E:E', 15)  # تاريخ التوظيف
    worksheet.set_column('F:N', 18)  # باقي الأعمدة
    
    workbook.close()
    output.seek(0)
    
    # إعداد الاستجابة
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="تقرير_الموظفين_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    
    return response


@login_required
def import_excel(request):
    """استيراد الموظفين من ملف Excel"""
    if request.method == 'POST':
        form = ExcelImportForm(request.POST, request.FILES)
        
        if form.is_valid():
            excel_file = request.FILES['excel_file']
            
            try:
                result = import_employees_from_excel(excel_file)
                
                success_message = f'تم استيراد {result["imported_count"]} موظف'
                if result.get('allowances_count', 0) > 0:
                    success_message += f' مع {result["allowances_count"]} بدل'
                success_message += ' بنجاح!'
                
                if result['errors']:
                    error_message = success_message + f"<br><br>تم العثور على الأخطاء التالية:<br>"
                    error_message += "<br>".join(result['errors'][:10])  # عرض أول 10 أخطاء فقط
                    if len(result['errors']) > 10:
                        error_message += f"<br>... و {len(result['errors']) - 10} أخطاء أخرى"
                    messages.warning(request, error_message)
                else:
                    messages.success(request, success_message)
                
                return redirect('employees:employee_list')
                
            except Exception as e:
                messages.error(request, f'خطأ في استيراد الملف: {str(e)}')
    
    else:
        form = ExcelImportForm()
    
    context = {
        'form': form,
        'title': 'استيراد الموظفين من Excel'
    }
    
    return render(request, 'employees/import_excel.html', context)


@login_required
def dashboard(request):
    """لوحة التحكم الرئيسية"""
    # إحصائيات عامة
    total_employees = Employee.objects.filter(is_active=True).count()
    active_employees = Employee.objects.filter(is_active=True)
    
    total_monthly_cost = sum(emp.get_monthly_gross_salary() for emp in active_employees)
    total_annual_cost = sum(emp.get_annual_total_cost() for emp in active_employees)
    
    category_stats = []
    categories = EmployeeCategory.objects.all()

    for category in categories:
        count = Employee.objects.filter(category=category, is_active=True).count()
        if count > 0:
            category_stats.append({
                'name': category.name,
                'count': count,
                'percentage': (count / total_employees * 100) if total_employees > 0 else 0
            })    # إحصائيات حسب الجنسية
    nationality_stats = []
    nationalities = Employee.objects.filter(is_active=True).values('nationality').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    for nat in nationalities:
        nationality_stats.append({
            'name': nat['nationality'],
            'count': nat['count'],
            'percentage': (nat['count'] / total_employees * 100) if total_employees > 0 else 0
        })
    
    # الموظفين الجدد (آخر 30 يوم)
    from datetime import timedelta
    recent_date = timezone.now().date() - timedelta(days=30)
    recent_employees = Employee.objects.filter(
        hire_date__gte=recent_date,
        is_active=True
    ).order_by('-hire_date')[:5]
    
    context = {
        'total_employees': total_employees,
        'total_monthly_cost': total_monthly_cost,
        'total_annual_cost': total_annual_cost,
        'category_stats': category_stats,
        'nationality_stats': nationality_stats,
        'recent_employees': recent_employees,
    }
    
    return render(request, 'employees/dashboard.html', context)