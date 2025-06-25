from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from datetime import datetime


class Employee(models.Model):
    """نموذج بيانات الموظف"""
    
    CATEGORY_CHOICES = [
        ('LABOR', 'عمالة'),
        ('STAFF', 'موظفين'),
        ('MANAGER', 'إداري'),
        ('ENGINEER', 'مهندس'),
        ('TECHNICIAN', 'فني'),
    ]
    
    INSURANCE_TYPE_CHOICES = [
        ('BASIC', 'أساسي'),
        ('COMPREHENSIVE', 'شامل'),
        ('PREMIUM', 'ممتاز'),
    ]
    
    # البيانات الأساسية
    employee_number = models.CharField(max_length=20, unique=True, verbose_name='رقم الموظف')
    name = models.CharField(max_length=200, verbose_name='الاسم')
    nationality = models.CharField(max_length=100, verbose_name='الجنسية')
    hire_date = models.DateField(verbose_name='تاريخ التوظيف')
    id_number = models.CharField(max_length=50, verbose_name='رقم الهوية/الإقامة')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name='الفئة')
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], verbose_name='آخر راتب أساسي')
    insurance_type = models.CharField(max_length=20, choices=INSURANCE_TYPE_CHOICES, verbose_name='نوع التأمين الطبي')
    
    # بيانات العائلة
    num_wives = models.PositiveIntegerField(default=0, verbose_name='عدد الزوجات')
    num_children = models.PositiveIntegerField(default=0, verbose_name='عدد الأبناء')
    
    # بيانات الاستقدام والتدريب
    recruitment_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='تكلفة الاستقدام')
    training_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='تكلفة التدريب')
    
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


class AllowanceType(models.Model):
    """أنواع البدلات"""
    
    FREQUENCY_CHOICES = [
        ('MONTHLY', 'شهري'),
        ('ANNUAL', 'سنوي'),
        ('ONE_TIME', 'مرة واحدة'),
    ]
    
    name = models.CharField(max_length=100, unique=True, verbose_name='اسم البدل')
    name_arabic = models.CharField(max_length=100, verbose_name='الاسم بالعربية')
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, verbose_name='تكرار البدل')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    
    class Meta:
        verbose_name = 'نوع البدل'
        verbose_name_plural = 'أنواع البدلات'
        ordering = ['name_arabic']
    
    def __str__(self):
        return self.name_arabic


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
        else:  # ONE_TIME
            return Decimal('0.00')
    
    def get_annual_amount(self):
        """حساب المبلغ السنوي للبدل"""
        if self.allowance_type.frequency == 'ANNUAL':
            return self.amount
        elif self.allowance_type.frequency == 'MONTHLY':
            return self.amount * 12
        else:  # ONE_TIME
            return self.amount