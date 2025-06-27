from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from datetime import datetime

class EmployeeCategory(models.Model):
    code = models.CharField(max_length=20, unique=True, verbose_name='رمز الفئة')
    name = models.CharField(max_length=100, verbose_name='اسم الفئة')

    def __str__(self):
        return self.name

class Employee(models.Model):
    """نموذج بيانات الموظف"""

 
    INSURANCE_TYPE_CHOICES = [
        ('VIP', 'VIP'),
        ('A+', 'A+'),
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
    ]

    # البيانات الأساسية
    employee_number = models.CharField(max_length=20, unique=True, verbose_name='رقم الموظف')
    name = models.CharField(max_length=200, verbose_name='الاسم')
    nationality = models.CharField(max_length=100, verbose_name='الجنسية')
    hire_date = models.DateField(verbose_name='تاريخ التوظيف')
    id_number = models.CharField(max_length=50, verbose_name='رقم الهوية/الإقامة')
    category = models.ForeignKey(EmployeeCategory, on_delete=models.SET_NULL, null=True, verbose_name='الفئة')
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], verbose_name='آخر راتب أساسي')
    insurance_type = models.CharField(max_length=20, choices=INSURANCE_TYPE_CHOICES, verbose_name='نوع التأمين الطبي')

    # بيانات العائلة
    num_wives = models.PositiveIntegerField(default=0, verbose_name='عدد الزوجات')
    num_children = models.PositiveIntegerField(default=0, verbose_name='عدد الأبناء')

    # بيانات الاستقدام والتدريب
    recruitment_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='تكلفة الاستقدام')
    training_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='تكلفة التدريب')

    # بيانات التذاكر
    TICKET_TYPE_CHOICES = [
        ('ANNUAL', 'سنوي'),
        ('BIENNIAL', 'كل سنتين'),
    ]

    ticket_type = models.CharField(max_length=20, choices=TICKET_TYPE_CHOICES, default='ANNUAL', verbose_name='نوع التذكرة')
    family_ticket_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='تكلفة التذاكر العائلية')

    # معلومات إضافية
    photo = models.ImageField(upload_to='employee_photos/', blank=True, null=True, verbose_name='الصورة')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'موظف'
        verbose_name_plural = 'الموظفين'
        ordering = ['employee_number']

    def __str__(self):
        return f"{self.employee_number} - {self.name}"

    def get_total_monthly_allowances(self):
        """حساب إجمالي البدلات الشهرية"""
        allowances = self.allowances.all()
        monthly_total = sum(allowance.get_monthly_amount() for allowance in allowances)
        return monthly_total

    def get_monthly_gross_salary(self):
        """حساب الراتب الشهري الإجمالي"""
        return self.basic_salary + self.get_total_monthly_allowances()

    def get_annual_allowances(self):
        """حساب البدلات السنوية"""
        allowances = self.allowances.all()
        annual_total = sum(allowance.get_annual_amount() for allowance in allowances)
        return annual_total

    def get_one_time_costs(self):
        """حساب التكاليف لمرة واحدة"""
        return self.recruitment_cost + self.training_cost

    def get_annual_total_cost(self):
        """حساب إجمالي التكلفة السنوية"""
        monthly_gross = self.get_monthly_gross_salary()
        annual_salary = monthly_gross * 12
        annual_allowances = self.get_annual_allowances()
        return annual_salary + annual_allowances

    def get_cost_factor(self):
        """حساب المعامل = إجمالي التكلفة السنوية / الراتب الأساسي"""
        if self.basic_salary > 0:
            return self.get_annual_total_cost() / (self.basic_salary * 12)
        return 0

    def calculate_training_cost_percentage(self):
        """حساب تكلفة التدريب كنسبة مئوية من الراتب"""
        monthly_gross = self.get_monthly_gross_salary()
        if self.nationality.lower() in ['سعودي', 'saudi', 'سعودية']:
            return monthly_gross * Decimal('0.05')  # 5% للسعوديين
        else:
            return monthly_gross * Decimal('0.02')  # 2% للأجانب

    def get_years_of_service(self):
        """حساب عدد سنوات الخدمة"""
        from datetime import date
        today = date.today()
        years = today.year - self.hire_date.year
        if today.month < self.hire_date.month or (today.month == self.hire_date.month and today.day < self.hire_date.day):
            years -= 1
        return max(0, years)

    def calculate_end_of_service_benefit(self):
        """حساب مكافأة نهاية الخدمة حسب نظام العمل السعودي"""
        years_of_service = self.get_years_of_service()
        basic_salary = self.basic_salary

        # البدلات النقدية فقط
        cash_allowances = sum(
            allowance.get_monthly_amount() 
            for allowance in self.allowances.filter(is_active=True, type='CASH')
        )

        monthly_salary = basic_salary + cash_allowances

        # أول 5 سنوات: نصف شهر لكل سنة
        first_five_years = min(years_of_service, 5)
        first_five_amount = first_five_years * (monthly_salary * Decimal('0.5'))

        # السنوات بعد الخامسة: شهر كامل لكل سنة
        remaining_years = max(0, years_of_service - 5)
        remaining_amount = remaining_years * monthly_salary

        total_amount = first_five_amount + remaining_amount

        return {
            'years_of_service': years_of_service,
            'monthly_salary': monthly_salary,
            'first_five_years': first_five_years,
            'first_five_amount': first_five_amount,
            'remaining_years': remaining_years,
            'remaining_amount': remaining_amount,
            'total_amount': total_amount
        }

    def calculate_family_ticket_cost(self):
        """حساب تكلفة التذاكر العائلية"""
        # التذاكر العائلية = راتب شهر واحد
        monthly_salary = self.basic_salary

        # حساب عدد أفراد العائلة المستحقين للتذاكر
        family_members = self.num_wives + self.num_children

        # التكلفة حسب نوع التذكرة
        if self.ticket_type == 'ANNUAL':
            annual_cost = monthly_salary * family_members
        else:  # BIENNIAL
            annual_cost = (monthly_salary * family_members) / 2  # توزيع التكلفة على سنتين

        return {
            'family_members': family_members,
            'monthly_salary': monthly_salary,
            'ticket_type': self.get_ticket_type_display(),
            'annual_cost': annual_cost,
            'total_cost_per_cycle': monthly_salary * family_members
        }


class AllowanceType(models.Model):
    """أنواع البدلات"""

    FREQUENCY_CHOICES = [
        ('MONTHLY', 'شهري'),
        ('ANNUAL', 'سنوي'),
        ('BIENNIAL', 'كل سنتين'),
        ('CUSTOM', 'مخصص'),
        ('ONE_TIME', 'مرة واحدة'),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name='اسم البدل')
    name_arabic = models.CharField(max_length=100, verbose_name='الاسم بالعربية')
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, verbose_name='تكرار البدل')
    custom_months = models.PositiveIntegerField(null=True, blank=True, verbose_name='عدد الأشهر المخصص')
    is_active = models.BooleanField(default=True, verbose_name='نشط')

    class Meta:
        verbose_name = 'نوع البدل'
        verbose_name_plural = 'أنواع البدلات'
        ordering = ['name_arabic']

    def __str__(self):
        return self.name_arabic

    def get_months_cycle(self):
        """حساب دورة الأشهر للبدل"""
        if self.frequency == 'MONTHLY':
            return 1
        elif self.frequency == 'ANNUAL':
            return 12
        elif self.frequency == 'BIENNIAL':
            return 24
        elif self.frequency == 'CUSTOM' and self.custom_months:
            return self.custom_months
        else:
            return 12


class Allowance(models.Model):
    """بدلات الموظفين"""

    ALLOWANCE_TYPE_CHOICES = [
        ('CASH', 'نقدي'),
        ('IN_KIND', 'عيني'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='allowances', verbose_name='الموظف')
    allowance_type = models.ForeignKey(AllowanceType, on_delete=models.CASCADE, verbose_name='نوع البدل')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))], verbose_name='المبلغ')
    type = models.CharField(max_length=10, choices=ALLOWANCE_TYPE_CHOICES, default='CASH', verbose_name='طبيعة البدل')
    notes = models.TextField(blank=True, verbose_name='ملاحظات')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'بدل'
        verbose_name_plural = 'البدلات'
        unique_together = ['employee', 'allowance_type']

    def __str__(self):
        return f"{self.employee.name} - {self.allowance_type.name_arabic}"

    def get_monthly_amount(self):
        """حساب المبلغ الشهري للبدل"""
        if self.allowance_type.frequency == 'MONTHLY':
            return self.amount
        elif self.allowance_type.frequency == 'ANNUAL':
            return self.amount / 12
        elif self.allowance_type.frequency == 'BIENNIAL':
            return self.amount / 24
        elif self.allowance_type.frequency == 'CUSTOM' and self.allowance_type.custom_months:
            return self.amount / self.allowance_type.custom_months
        else:  # ONE_TIME
            return Decimal('0.00')

    def get_annual_amount(self):
        """حساب المبلغ السنوي للبدل"""
        if self.allowance_type.frequency == 'ANNUAL':
            return self.amount
        elif self.allowance_type.frequency == 'MONTHLY':
            return self.amount * 12
        elif self.allowance_type.frequency == 'BIENNIAL':
            return self.amount / 2  # البدل كل سنتين مقسوم على 2 للحصول على المبلغ السنوي
        elif self.allowance_type.frequency == 'CUSTOM' and self.allowance_type.custom_months:
            return (self.amount * 12) / self.allowance_type.custom_months
        else:  # ONE_TIME
            return self.amount