from django.core.management.base import BaseCommand
from employees.models import Employee, AllowanceType, Allowance
from employees.utils import create_default_allowance_types
from decimal import Decimal
import random
from datetime import date, timedelta

class Command(BaseCommand):
    help = 'إنشاء بيانات تجريبية للاختبار'

    def handle(self, *args, **options):
        # إنشاء أنواع البدلات أولاً
        create_default_allowance_types()
        
        # بيانات تجريبية للموظفين
        sample_employees = [
            {
                'employee_number': 'EMP001',
                'name': 'أحمد محمد علي',
                'nationality': 'سعودي',
                'category': 'MANAGER',
                'basic_salary': Decimal('8000.00'),
                'insurance_type': 'COMPREHENSIVE'
            },
            {
                'employee_number': 'EMP002',
                'name': 'محمد أحمد السعد',
                'nationality': 'مصري',
                'category': 'ENGINEER',
                'basic_salary': Decimal('6500.00'),
                'insurance_type': 'BASIC'
            },
            {
                'employee_number': 'EMP003',
                'name': 'خالد عبدالله',
                'nationality': 'أردني',
                'category': 'TECHNICIAN',
                'basic_salary': Decimal('4500.00'),
                'insurance_type': 'BASIC'
            },
            {
                'employee_number': 'EMP004',
                'name': 'عبدالرحمن صالح',
                'nationality': 'سعودي',
                'category': 'STAFF',
                'basic_salary': Decimal('5000.00'),
                'insurance_type': 'COMPREHENSIVE'
            },
            {
                'employee_number': 'EMP005',
                'name': 'يوسف العمراني',
                'nationality': 'مغربي',
                'category': 'LABOR',
                'basic_salary': Decimal('3200.00'),
                'insurance_type': 'BASIC'
            }
        ]
        
        created_count = 0
        for emp_data in sample_employees:
            if not Employee.objects.filter(employee_number=emp_data['employee_number']).exists():
                employee = Employee.objects.create(
                    employee_number=emp_data['employee_number'],
                    name=emp_data['name'],
                    nationality=emp_data['nationality'],
                    hire_date=date.today() - timedelta(days=random.randint(30, 365*3)),
                    id_number=f"ID{random.randint(100000, 999999)}",
                    category=emp_data['category'],
                    basic_salary=emp_data['basic_salary'],
                    insurance_type=emp_data['insurance_type'],
                    num_wives=random.randint(0, 2),
                    num_children=random.randint(0, 4),
                    recruitment_cost=Decimal(str(random.randint(1000, 5000))),
                    training_cost=Decimal(str(random.randint(500, 2000)))
                )
                
                # إضافة بدلات عشوائية
                allowance_types = list(AllowanceType.objects.filter(is_active=True))
                for i in range(random.randint(1, 3)):
                    allowance_type = random.choice(allowance_types)
                    if not Allowance.objects.filter(employee=employee, allowance_type=allowance_type).exists():
                        Allowance.objects.create(
                            employee=employee,
                            allowance_type=allowance_type,
                            amount=Decimal(str(random.randint(200, 1000))),
                            type=random.choice(['CASH', 'IN_KIND'])
                        )
                
                created_count += 1
                self.stdout.write(f'تم إنشاء الموظف: {employee.name}')
        
        self.stdout.write(
            self.style.SUCCESS(f'تم إنشاء {created_count} موظف تجريبي بنجاح')
        )