"""
نظام تقارير متقدم مطابق لملف Excel
"""
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from decimal import Decimal
from collections import defaultdict, OrderedDict
import json

from .models import Employee, Allowance, AllowanceType


class AdvancedReportsGenerator:
    """مولد التقارير المتقدمة"""
    
    def __init__(self, queryset=None):
        self.employees = queryset or Employee.objects.filter(is_active=True)
    
    def generate_summary_by_category(self):
        """تقرير ملخص حسب الفئة - مطابق لورقة BY CATEGORY"""
        categories = {}
        category_totals = self.employees.values('category').annotate(
            total_count=Count('id'),
            total_basic_salary=Sum('basic_salary'),
            avg_salary=Avg('basic_salary')
        ).order_by('category')
        
        for idx, cat in enumerate(category_totals, 1):
            category_name = dict(Employee.CATEGORY_CHOICES).get(cat['category'], cat['category'])
            categories[idx] = {
                'category': category_name,
                'total_employees': cat['total_count'],
                'total_basic_salary': float(cat['total_basic_salary'] or 0),
                'average_salary': float(cat['avg_salary'] or 0),
                'percentage': round((cat['total_count'] / self.employees.count() * 100), 2) if self.employees.count() > 0 else 0
            }
        
        return categories
    
    def generate_summary_by_nationality(self):
        """تقرير ملخص حسب الجنسية - مطابق لتجميع البيانات بالجنسية"""
        nationalities = {}
        nationality_totals = self.employees.values('nationality').annotate(
            total_count=Count('id'),
            total_basic_salary=Sum('basic_salary'),
            avg_salary=Avg('basic_salary')
        ).order_by('-total_count')
        
        for idx, nat in enumerate(nationality_totals, 1):
            nationalities[idx] = {
                'nationality': nat['nationality'],
                'total_employees': nat['total_count'],
                'total_basic_salary': float(nat['total_basic_salary'] or 0),
                'average_salary': float(nat['avg_salary'] or 0),
                'percentage': round((nat['total_count'] / self.employees.count() * 100), 2) if self.employees.count() > 0 else 0
            }
        
        return nationalities
    
    def generate_detailed_employee_report(self):
        """تقرير مفصل للموظفين - مطابق للبيانات الأساسية في Excel"""
        detailed_report = []
        
        for employee in self.employees.order_by('employee_number'):
            # حساب البدلات
            monthly_allowances = employee.get_total_monthly_allowances()
            annual_allowances = employee.get_annual_allowances()
            monthly_gross = employee.get_monthly_gross_salary()
            annual_cost = employee.get_annual_total_cost()
            
            # حساب سنوات الخدمة
            years_of_service = self._calculate_years_of_service(employee.hire_date)
            
            # حساب الزيادات (افتراضي - يمكن تخصيصه)
            salary_increases = self._calculate_salary_increases(employee)
            
            detailed_report.append({
                'employee_number': employee.employee_number,
                'name': employee.name,
                'category': employee.get_category_display(),
                'nationality': employee.nationality,
                'hire_date': employee.hire_date.strftime('%d/%m/%Y'),
                'basic_salary': float(employee.basic_salary),
                'monthly_allowances': float(monthly_allowances),
                'monthly_gross': float(monthly_gross),
                'annual_cost': float(annual_cost),
                'years_of_service': years_of_service,
                'salary_increases': salary_increases,
                'insurance_type': employee.get_insurance_type_display(),
                'cost_factor': float(employee.get_cost_factor()),
                'efficiency_ratio': self._calculate_efficiency_ratio(employee),
                'project_assignment': 'مشروع افتراضي',  # يمكن إضافة حقل مشروع لاحقاً
                'location': 'المكتب الرئيسي',  # يمكن إضافة حقل الموقع لاحقاً
            })
        
        return detailed_report
    
    def generate_cost_analysis_report(self):
        """تقرير تحليل التكاليف المتقدم"""
        total_employees = self.employees.count()
        
        if total_employees == 0:
            return {
                'summary': {},
                'cost_breakdown': {},
                'trends': {}
            }
        
        # الإجماليات العامة
        total_basic_salary = sum(emp.basic_salary for emp in self.employees)
        total_monthly_cost = sum(emp.get_monthly_gross_salary() for emp in self.employees)
        total_annual_cost = sum(emp.get_annual_total_cost() for emp in self.employees)
        average_cost_factor = sum(emp.get_cost_factor() for emp in self.employees) / total_employees
        
        # تفصيل التكاليف
        cost_breakdown = {
            'basic_salaries': float(total_basic_salary),
            'monthly_allowances': float(total_monthly_cost - total_basic_salary),
            'annual_allowances': float(sum(emp.get_annual_allowances() for emp in self.employees)),
            'recruitment_costs': float(sum(emp.recruitment_cost for emp in self.employees)),
            'training_costs': float(sum(emp.training_cost for emp in self.employees)),
        }
        
        # تحليل حسب الفئات
        category_analysis = {}
        for category_code, category_name in Employee.CATEGORY_CHOICES:
            cat_employees = self.employees.filter(category=category_code)
            if cat_employees.exists():
                category_analysis[category_name] = {
                    'count': cat_employees.count(),
                    'total_cost': float(sum(emp.get_annual_total_cost() for emp in cat_employees)),
                    'average_cost': float(sum(emp.get_annual_total_cost() for emp in cat_employees) / cat_employees.count()),
                    'percentage_of_total': round((cat_employees.count() / total_employees * 100), 2)
                }
        
        return {
            'summary': {
                'total_employees': total_employees,
                'total_basic_salary': float(total_basic_salary),
                'total_monthly_cost': float(total_monthly_cost),
                'total_annual_cost': float(total_annual_cost),
                'average_monthly_cost': float(total_monthly_cost / total_employees),
                'average_annual_cost': float(total_annual_cost / total_employees),
                'average_cost_factor': float(average_cost_factor),
            },
            'cost_breakdown': cost_breakdown,
            'category_analysis': category_analysis,
            'efficiency_metrics': self._calculate_efficiency_metrics()
        }
    
    def generate_salary_distribution_report(self):
        """تقرير توزيع الرواتب"""
        salary_ranges = [
            (0, 1000, 'أقل من 1,000'),
            (1000, 2000, '1,000 - 2,000'),
            (2000, 5000, '2,000 - 5,000'),
            (5000, 10000, '5,000 - 10,000'),
            (10000, float('inf'), 'أكثر من 10,000')
        ]
        
        distribution = {}
        for min_sal, max_sal, label in salary_ranges:
            if max_sal == float('inf'):
                count = self.employees.filter(basic_salary__gte=min_sal).count()
            else:
                count = self.employees.filter(basic_salary__gte=min_sal, basic_salary__lt=max_sal).count()
            
            distribution[label] = {
                'count': count,
                'percentage': round((count / self.employees.count() * 100), 2) if self.employees.count() > 0 else 0
            }
        
        return distribution
    
    def generate_allowances_summary(self):
        """تقرير ملخص البدلات"""
        allowances_summary = {}
        
        # تجميع البدلات حسب النوع
        for allowance_type in AllowanceType.objects.filter(is_active=True):
            allowances = Allowance.objects.filter(
                allowance_type=allowance_type,
                employee__in=self.employees,
                is_active=True
            )
            
            total_amount = sum(a.amount for a in allowances)
            employee_count = allowances.count()
            
            if employee_count > 0:
                allowances_summary[allowance_type.name_arabic] = {
                    'total_amount': float(total_amount),
                    'employee_count': employee_count,
                    'average_amount': float(total_amount / employee_count),
                    'frequency': allowance_type.frequency,
                    'percentage_of_employees': round((employee_count / self.employees.count() * 100), 2)
                }
        
        return allowances_summary
    
    def _calculate_years_of_service(self, hire_date):
        """حساب سنوات الخدمة"""
        today = timezone.now().date()
        years = today.year - hire_date.year
        if today.month < hire_date.month or (today.month == hire_date.month and today.day < hire_date.day):
            years -= 1
        return years
    
    def _calculate_salary_increases(self, employee):
        """حساب زيادات الراتب (افتراضي - يمكن تطويره)"""
        # هذا مجرد مثال - يمكن ربطه بنظام تتبع الزيادات
        years_of_service = self._calculate_years_of_service(employee.hire_date)
        estimated_increases = years_of_service * 0.05  # افتراض زيادة 5% سنوياً
        return round(estimated_increases * 100, 2)
    
    def _calculate_efficiency_ratio(self, employee):
        """حساب نسبة الكفاءة"""
        annual_cost = employee.get_annual_total_cost()
        if annual_cost > 0:
            return float(employee.basic_salary * 12 / annual_cost)
        return 0
    
    def _calculate_efficiency_metrics(self):
        """حساب مقاييس الكفاءة العامة"""
        efficiency_ratios = [self._calculate_efficiency_ratio(emp) for emp in self.employees]
        
        if not efficiency_ratios:
            return {}
        
        return {
            'highest_efficiency': max(efficiency_ratios),
            'lowest_efficiency': min(efficiency_ratios),
            'average_efficiency': sum(efficiency_ratios) / len(efficiency_ratios),
            'efficiency_above_70': len([r for r in efficiency_ratios if r >= 0.7]),
            'efficiency_below_50': len([r for r in efficiency_ratios if r < 0.5])
        }
    
    def export_to_excel_format(self):
        """تصدير التقارير بنفس تنسيق Excel الأصلي"""
        return {
            'summary_by_category': self.generate_summary_by_category(),
            'summary_by_nationality': self.generate_summary_by_nationality(),
            'detailed_employee_report': self.generate_detailed_employee_report(),
            'cost_analysis': self.generate_cost_analysis_report(),
            'salary_distribution': self.generate_salary_distribution_report(),
            'allowances_summary': self.generate_allowances_summary(),
            'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        }


def generate_excel_compatible_report(employees_queryset=None):
    """دالة مساعدة لإنتاج تقرير مطابق لملف Excel"""
    generator = AdvancedReportsGenerator(employees_queryset)
    return generator.export_to_excel_format()