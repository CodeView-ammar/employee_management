from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Sum, Avg, Count
from django.contrib import messages
from decimal import Decimal
import json
from datetime import datetime, date
import xlsxwriter
from io import BytesIO

from .models import Employee, Allowance, AllowanceType
from .forms import ReportFilterForm
from .reports_advanced import AdvancedReportsGenerator, generate_excel_compatible_report


@login_required
def employee_individual_report(request, employee_id):
    """تقرير مفصل لموظف واحد"""
    employee = get_object_or_404(Employee, pk=employee_id)

    # حساب البدلات حسب معادلات Excel
    allowances = employee.allowances.filter(is_active=True).select_related('allowance_type')
    
    monthly_allowances = {}
    annual_allowances = {}
    one_time_costs = {}
    biennial_allowances = {}
    custom_allowances = {}

    # تصنيف البدلات حسب التكرار
    for allowance in allowances:
        allowance_type = allowance.allowance_type.name_arabic
        
        if allowance.allowance_type.frequency == 'MONTHLY':
            monthly_allowances[allowance_type] = {
                'amount': allowance.amount,
                'type': allowance.get_type_display(),
                'annual_total': allowance.amount * Decimal('12'),
                'monthly_equivalent': allowance.amount
            }
        elif allowance.allowance_type.frequency == 'ANNUAL':
            annual_allowances[allowance_type] = {
                'amount': allowance.amount,
                'type': allowance.get_type_display(),
                'monthly_equivalent': allowance.amount / Decimal('12'),
                'annual_total': allowance.amount
            }
        elif allowance.allowance_type.frequency == 'BIENNIAL':
            biennial_allowances[allowance_type] = {
                'amount': allowance.amount,
                'type': allowance.get_type_display(),
                'monthly_equivalent': allowance.amount / Decimal('24'),
                'annual_equivalent': allowance.amount / Decimal('2')
            }
        elif allowance.allowance_type.frequency == 'CUSTOM':
            months = allowance.allowance_type.custom_months or 12
            custom_allowances[allowance_type] = {
                'amount': allowance.amount,
                'type': allowance.get_type_display(),
                'months': months,
                'monthly_equivalent': allowance.amount / Decimal(str(months)),
                'annual_equivalent': (allowance.amount * Decimal('12')) / Decimal(str(months))
            }
        else:  # ONE_TIME
            one_time_costs[allowance_type] = {
                'amount': allowance.amount,
                'type': allowance.get_type_display()
            }

    # حساب إجماليات البدلات الشهرية (Excel Column H-S)
    total_monthly_allowances = sum(item['amount'] for item in monthly_allowances.values())
    
    # حساب معادل شهري للبدلات السنوية وثنائية السنة والمخصصة
    monthly_from_annual = sum(item['monthly_equivalent'] for item in annual_allowances.values())
    monthly_from_biennial = sum(item['monthly_equivalent'] for item in biennial_allowances.values())
    monthly_from_custom = sum(item['monthly_equivalent'] for item in custom_allowances.values())
    
    # حساب إجمالي البدلات السنوية (Excel Column Y-AN)
    total_annual_allowances = sum(item['amount'] for item in annual_allowances.values())
    annual_from_biennial = sum(item['annual_equivalent'] for item in biennial_allowances.values())
    annual_from_custom = sum(item['annual_equivalent'] for item in custom_allowances.values())
    
    # حساب التكاليف الإضافية
    training_cost_percentage = employee.calculate_training_cost_percentage()
    family_ticket_data = employee.calculate_family_ticket_cost()
    eos_data = employee.calculate_end_of_service_benefit()
    
    # حساب الراتب الإجمالي الشهري (مطابق لمعادلة Excel =H7+I7+...+S7)
    monthly_gross = (
        employee.basic_salary +  # T7
        total_monthly_allowances +  # H7-S7
        monthly_from_annual +  # معادل شهري للبدلات السنوية
        monthly_from_biennial +  # معادل شهري للبدلات ثنائية السنة
        monthly_from_custom  # معادل شهري للبدلات المخصصة
    )
    
    # حساب التكلفة السنوية الأساسية (مطابق لمعادلة Excel =(T7*12)+AO7)
    annual_salary_cost = employee.basic_salary * Decimal('12')  # T7*12
    
    # حساب إجمالي البدلات السنوية (مطابق لمعادلة Excel =Y7+Z7+...+AN7)
    total_annual_benefits = (
        (total_monthly_allowances * Decimal('12')) +  # البدلات الشهرية * 12
        total_annual_allowances +  # البدلات السنوية
        annual_from_biennial +  # معادل سنوي للبدلات ثنائية السنة
        annual_from_custom  # معادل سنوي للبدلات المخصصة
    )
    
    # حساب التكلفة السنوية الإجمالية
    total_annual_cost = (
        annual_salary_cost +  # (T7*12)
        total_annual_benefits +  # (Y7+Z7+...+AN7)
        employee.recruitment_cost +  # تكلفة الاستقدام
        employee.training_cost +  # تكلفة التدريب الفعلية
        training_cost_percentage * Decimal('12') +  # تكلفة التدريب كنسبة مئوية سنوية
        family_ticket_data['annual_cost'] +  # تكلفة التذاكر العائلية
        sum(item['amount'] for item in one_time_costs.values())  # التكاليف لمرة واحدة
    )

    # حساب المعامل (إجمالي التكلفة السنوية ÷ الراتب الأساسي السنوي)
    cost_factor = total_annual_cost / annual_salary_cost if annual_salary_cost > 0 else Decimal('0')

    report_data = {
        'employee': employee,
        'monthly_allowances': monthly_allowances,
        'annual_allowances': annual_allowances,
        'biennial_allowances': biennial_allowances,
        'custom_allowances': custom_allowances,
        'one_time_costs': one_time_costs,
        'training_cost_percentage': training_cost_percentage,
        'family_ticket_data': family_ticket_data,
        'eos_data': eos_data,
        'totals': {
            'basic_salary': employee.basic_salary,
            'total_monthly_allowances': total_monthly_allowances,
            'monthly_from_annual': monthly_from_annual,
            'monthly_from_biennial': monthly_from_biennial,
            'monthly_from_custom': monthly_from_custom,
            'monthly_gross': monthly_gross,
            'annual_salary_cost': annual_salary_cost,
            'total_annual_benefits': total_annual_benefits,
            'one_time_costs_total': sum(item['amount'] for item in one_time_costs.values()),
            'recruitment_cost': employee.recruitment_cost,
            'training_cost': employee.training_cost,
            'training_cost_percentage_annual': training_cost_percentage * Decimal('12'),
            'family_ticket_annual_cost': family_ticket_data['annual_cost'],
            'total_annual_cost': total_annual_cost,
            'cost_factor': cost_factor,
            # للتوافق مع القوالب الموجودة
            'annual_allowances': total_annual_allowances,
            'monthly_allowances': total_monthly_allowances,
            'annual_gross': total_annual_cost,
            'monthly_equivalent_annual_allowances': monthly_from_annual + monthly_from_biennial + monthly_from_custom
        }
    }

    context = {
        'report_data': report_data,
        'employee': employee
    }
    
    return render(request, 'employees/individual_report.html', context)
@login_required
def employee_cost_breakdown(request, employee_id):
    """تفصيل تكاليف الموظف بصيغة JSON للمخططات"""
    employee = get_object_or_404(Employee, pk=employee_id)
    allowances = employee.allowances.filter(is_active=True).select_related('allowance_type')
    
    # تجميع البيانات للمخططات
    cost_breakdown = {
        'basic_salary': float(employee.basic_salary),
        'recruitment_cost': float(employee.recruitment_cost),
        'training_cost': float(employee.training_cost),
        'allowances': {}
    }
    
    for allowance in allowances:
        allowance_name = allowance.allowance_type.name_arabic
        monthly_amount = float(allowance.get_monthly_amount())
        annual_amount = float(allowance.get_annual_amount())
        
        cost_breakdown['allowances'][allowance_name] = {
            'monthly': monthly_amount,
            'annual': annual_amount,
            'frequency': allowance.allowance_type.frequency,
            'type': allowance.type
        }
    
    return JsonResponse(cost_breakdown)


@login_required
def export_individual_report(request, employee_id):
    """تصدير تقرير الموظف الواحد إلى Excel"""
    employee = get_object_or_404(Employee, pk=employee_id)
    
    # إنشاء ملف Excel
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    
    # تنسيقات مختلفة
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 16,
        'align': 'center',
        'valign': 'vcenter',
        'bg_color': '#4472C4',
        'font_color': 'white',
        'border': 1
    })
    
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#D9E2F3',
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
    
    # إنشاء ورقة العمل
    worksheet = workbook.add_worksheet(f'تقرير_{employee.employee_number}')
    
    # عنوان التقرير
    worksheet.merge_range('A1:F1', f'تقرير مفصل للموظف: {employee.name}', title_format)
    worksheet.merge_range('A2:F2', f'رقم الموظف: {employee.employee_number}', header_format)
    
    # البيانات الأساسية
    row = 4
    worksheet.write(row, 0, 'البيانات الأساسية', header_format)
    worksheet.write(row, 1, '', header_format)
    worksheet.write(row, 2, '', header_format)
    worksheet.write(row, 3, '', header_format)
    worksheet.write(row, 4, '', header_format)
    worksheet.write(row, 5, '', header_format)
    
    row += 1
    basic_data = [
        ('الاسم', employee.name),
        ('الجنسية', employee.nationality),
        ('الفئة', employee.category.name),
        ('تاريخ التوظيف', employee.hire_date.strftime('%Y-%m-%d')),
        ('الراتب الأساسي', employee.basic_salary),
    ]
    
    for label, value in basic_data:
        worksheet.write(row, 0, label, data_format)
        if isinstance(value, (int, float, Decimal)):
            worksheet.write(row, 1, float(value), number_format)
        else:
            worksheet.write(row, 1, value, data_format)
        row += 1
    
    # البدلات
    row += 1
    worksheet.write(row, 0, 'البدلات والمزايا', header_format)
    worksheet.write(row, 1, 'المبلغ', header_format)
    worksheet.write(row, 2, 'التكرار', header_format)
    worksheet.write(row, 3, 'النوع', header_format)
    worksheet.write(row, 4, 'شهري', header_format)
    worksheet.write(row, 5, 'سنوي', header_format)
    
    allowances = employee.allowances.filter(is_active=True).select_related('allowance_type')
    row += 1
    
    for allowance in allowances:
        worksheet.write(row, 0, allowance.allowance_type.name_arabic, data_format)
        worksheet.write(row, 1, float(allowance.amount), number_format)
        worksheet.write(row, 2, allowance.allowance_type.get_frequency_display(), data_format)
        worksheet.write(row, 3, allowance.get_type_display(), data_format)
        worksheet.write(row, 4, float(allowance.get_monthly_amount()), number_format)
        worksheet.write(row, 5, float(allowance.get_annual_amount()), number_format)
        row += 1
    
    # الإجماليات
    row += 1
    worksheet.write(row, 0, 'الإجماليات', header_format)
    worksheet.write(row, 1, '', header_format)
    worksheet.write(row, 2, '', header_format)
    worksheet.write(row, 3, '', header_format)
    worksheet.write(row, 4, '', header_format)
    worksheet.write(row, 5, '', header_format)
    
    totals = [
        ('إجمالي البدلات الشهرية', employee.get_total_monthly_allowances()),
        ('الراتب الإجمالي الشهري', employee.get_monthly_gross_salary()),
        ('التكلفة السنوية', employee.get_annual_total_cost()),
        ('المعامل', employee.get_cost_factor()),
    ]
    
    row += 1
    for label, value in totals:
        worksheet.write(row, 0, label, data_format)
        worksheet.write(row, 1, float(value), number_format)
        row += 1
    
    # تنسيق عرض الأعمدة
    worksheet.set_column('A:A', 25)
    worksheet.set_column('B:F', 18)
    
    workbook.close()
    output.seek(0)
    
    # إعداد الاستجابة
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="تقرير_{employee.employee_number}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    
    return response


@login_required
def comparison_report(request):
    """تقرير مقارنة بين الموظفين"""
    form = ReportFilterForm(request.GET)
    employees = Employee.objects.filter(is_active=True)
    
    # تطبيق المرشحات
    if form.is_valid():
        # نفس المرشحات المستخدمة في التقارير العامة
        if form.cleaned_data.get('employee_search'):
            search_term = form.cleaned_data['employee_search']
            employees = employees.filter(
                Q(employee_number__icontains=search_term) |
                Q(name__icontains=search_term)
            )
        
        if form.cleaned_data.get('nationality'):
            employees = employees.filter(nationality=form.cleaned_data['nationality'])
        
        if form.cleaned_data.get('category'):
            employees = employees.filter(category=form.cleaned_data['category'])
        
        if form.cleaned_data.get('date_from'):
            employees = employees.filter(hire_date__gte=form.cleaned_data['date_from'])
        
        if form.cleaned_data.get('date_to'):
            employees = employees.filter(hire_date__lte=form.cleaned_data['date_to'])
    
    # حساب بيانات المقارنة مطابقة لمعادلات Excel
    comparison_data = []
    for employee in employees:
        # التكلفة السنوية مطابقة لمعادلات Excel
        annual_cost = employee.get_annual_total_cost()
        basic_salary_annual = employee.basic_salary * 12
        
        # البدلات الشهرية (H-S)
        monthly_allowances_only = employee.get_total_monthly_allowances()
        
        # الراتب الإجمالي الشهري (T + معادل شهري لجميع البدلات)
        monthly_gross = employee.get_monthly_gross_salary()
        
        # نسبة الكفاءة (الراتب الأساسي السنوي ÷ التكلفة الإجمالية)
        efficiency_ratio = float(basic_salary_annual / annual_cost) if annual_cost > 0 else 0.0
        
        comparison_data.append({
            'employee': employee,
            'basic_salary': float(employee.basic_salary),
            'monthly_allowances': float(monthly_allowances_only),
            'monthly_gross': float(monthly_gross),
            'annual_cost': float(annual_cost),
            'cost_factor': float(employee.get_cost_factor()),
            'efficiency_ratio': efficiency_ratio,
            'years_of_service': employee.get_years_of_service(),
            'training_cost_percentage': float(employee.calculate_training_cost_percentage() * 12),
            'family_ticket_cost': float(employee.calculate_family_ticket_cost()['annual_cost'])
        })
    
    # ترتيب حسب التكلفة السنوية
    comparison_data.sort(key=lambda x: x['annual_cost'], reverse=True)
    
    context = {
        'form': form,
        'comparison_data': comparison_data,
        'filters': request.GET.dict()
    }
    
    return render(request, 'employees/comparison_report.html', context)


@login_required
def advanced_excel_reports(request):
    """تقارير متقدمة مطابقة لملف Excel"""
    form = ReportFilterForm(request.GET)
    employees = Employee.objects.all()
    
    # تطبيق المرشحات
    if form.is_valid():
        if form.cleaned_data.get('employee_search'):
            search_term = form.cleaned_data['employee_search']
            employees = employees.filter(
                Q(employee_number__icontains=search_term) |
                Q(name__icontains=search_term)
            )
        
        if form.cleaned_data.get('nationality'):
            employees = employees.filter(nationality=form.cleaned_data['nationality'])
        
        if form.cleaned_data.get('category'):
            employees = employees.filter(category=form.cleaned_data['category'])
        
        if form.cleaned_data.get('date_from'):
            employees = employees.filter(hire_date__gte=form.cleaned_data['date_from'])
        
        if form.cleaned_data.get('date_to'):
            employees = employees.filter(hire_date__lte=form.cleaned_data['date_to'])
        
        if form.cleaned_data.get('is_active'):
            is_active = form.cleaned_data['is_active'] == 'true'
            employees = employees.filter(is_active=is_active)
        
        if form.cleaned_data.get('salary_min'):
            employees = employees.filter(basic_salary__gte=form.cleaned_data['salary_min'])
        
        if form.cleaned_data.get('salary_max'):
            employees = employees.filter(basic_salary__lte=form.cleaned_data['salary_max'])
    
    # إنتاج التقارير المتقدمة
    generator = AdvancedReportsGenerator(employees)
    excel_reports = generator.export_to_excel_format()
    
    context = {
        'form': form,
        'excel_reports': excel_reports,
        'filters': request.GET.dict()
    }
    
    return render(request, 'employees/advanced_excel_reports.html', context)


@login_required
def export_advanced_excel(request):
    """تصدير التقارير المتقدمة إلى Excel بنفس تنسيق الملف الأصلي"""
    form = ReportFilterForm(request.GET)
    employees = Employee.objects.all()
    
    # تطبيق نفس المرشحات
    if form.is_valid():
        if form.cleaned_data.get('employee_search'):
            search_term = form.cleaned_data['employee_search']
            employees = employees.filter(
                Q(employee_number__icontains=search_term) |
                Q(name__icontains=search_term)
            )
        
        if form.cleaned_data.get('nationality'):
            employees = employees.filter(nationality=form.cleaned_data['nationality'])
        
        if form.cleaned_data.get('category'):
            employees = employees.filter(category=form.cleaned_data['category'])
        
        if form.cleaned_data.get('date_from'):
            employees = employees.filter(hire_date__gte=form.cleaned_data['date_from'])
        
        if form.cleaned_data.get('date_to'):
            employees = employees.filter(hire_date__lte=form.cleaned_data['date_to'])
    
    # إنشاء ملف Excel متقدم
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    
    # تنسيقات Excel
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4472C4',
        'font_color': 'white',
        'align': 'center',
        'valign': 'vcenter',
        'border': 1
    })
    
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 14,
        'align': 'center',
        'valign': 'vcenter',
        'bg_color': '#D9E2F3',
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
    
    # إنتاج التقارير
    generator = AdvancedReportsGenerator(employees)
    reports_data = generator.export_to_excel_format()
    
    # ورقة 1: ملخص حسب الفئة (BY CATEGORY)
    ws_category = workbook.add_worksheet('BY CATEGORY')
    ws_category.write('A1', 'SUMMARY - CATEGORY', title_format)
    ws_category.write('B1', '', title_format)
    ws_category.write('C1', '', title_format)
    
    ws_category.write('A2', 'No.', header_format)
    ws_category.write('B2', 'CATEGORY', header_format)
    ws_category.write('C2', 'TOTAL', header_format)
    
    row = 3
    for idx, data in reports_data['summary_by_category'].items():
        ws_category.write(f'A{row}', idx, data_format)
        ws_category.write(f'B{row}', data['category'], data_format)
        ws_category.write(f'C{row}', data['total_employees'], data_format)
        row += 1
    
    # ورقة 2: ملخص حسب الجنسية  
    ws_nationality = workbook.add_worksheet('BY NATIONALITY')
    ws_nationality.write('A1', 'SUMMARY - NATIONALITY', title_format)
    ws_nationality.write('B1', '', title_format)
    ws_nationality.write('C1', '', title_format)
    
    ws_nationality.write('A2', 'No.', header_format)
    ws_nationality.write('B2', 'NATIONALITY', header_format)
    ws_nationality.write('C2', 'TOTAL', header_format)
    
    row = 3
    for idx, data in reports_data['summary_by_nationality'].items():
        ws_nationality.write(f'A{row}', idx, data_format)
        ws_nationality.write(f'B{row}', data['nationality'], data_format)
        ws_nationality.write(f'C{row}', data['total_employees'], data_format)
        row += 1
    
    # ورقة 3: التقرير المفصل (DETAILED)
    ws_detailed = workbook.add_worksheet('DETAILED REPORT')
    
    headers = [
        'Employee Number', 'Name', 'Category', 'Nationality', 'Hire Date',
        'Basic Salary', 'Monthly Allowances', 'Monthly Gross', 'Annual Cost',
        'Years of Service', 'Cost Factor', 'Efficiency Ratio'
    ]
    
    for col, header in enumerate(headers):
        ws_detailed.write(0, col, header, header_format)
    
    row = 1
    for emp_data in reports_data['detailed_employee_report']:
        ws_detailed.write(row, 0, emp_data['employee_number'], data_format)
        ws_detailed.write(row, 1, emp_data['name'], data_format)
        ws_detailed.write(row, 2, emp_data['category'], data_format)
        ws_detailed.write(row, 3, emp_data['nationality'], data_format)
        ws_detailed.write(row, 4, emp_data['hire_date'], data_format)
        ws_detailed.write(row, 5, emp_data['basic_salary'], number_format)
        ws_detailed.write(row, 6, emp_data['monthly_allowances'], number_format)
        ws_detailed.write(row, 7, emp_data['monthly_gross'], number_format)
        ws_detailed.write(row, 8, emp_data['annual_cost'], number_format)
        ws_detailed.write(row, 9, emp_data['years_of_service'], data_format)
        ws_detailed.write(row, 10, emp_data['cost_factor'], number_format)
        ws_detailed.write(row, 11, emp_data['efficiency_ratio'], number_format)
        row += 1
    
    # ورقة 4: تحليل التكاليف
    ws_cost = workbook.add_worksheet('COST ANALYSIS')
    cost_data = reports_data['cost_analysis']
    
    ws_cost.write('A1', 'تحليل التكاليف الشامل', title_format)
    
    row = 3
    ws_cost.write(f'A{row}', 'البند', header_format)
    ws_cost.write(f'B{row}', 'القيمة', header_format)
    row += 1
    
    for key, value in cost_data['summary'].items():
        ws_cost.write(f'A{row}', key.replace('_', ' ').title(), data_format)
        if isinstance(value, (int, float)):
            ws_cost.write(f'B{row}', value, number_format)
        else:
            ws_cost.write(f'B{row}', value, data_format)
        row += 1
    
    # تنسيق عرض الأعمدة
    for worksheet in [ws_category, ws_nationality, ws_detailed, ws_cost]:
        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:Z', 20)
    
    workbook.close()
    output.seek(0)
    
    # إعداد الاستجابة
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="تقرير_شامل_مطابق_للاكسل_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    
    return response