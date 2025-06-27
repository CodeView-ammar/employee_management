from django.core.management.base import BaseCommand
from employees.utils import create_default_allowance_types


class Command(BaseCommand):
    help = 'إنشاء أنواع البدلات الافتراضية'

    def handle(self, *args, **options):
        created_count = create_default_allowance_types()
        self.stdout.write(
            self.style.SUCCESS(
                f'تم إنشاء {created_count} نوع بدل بنجاح'
            )
        )