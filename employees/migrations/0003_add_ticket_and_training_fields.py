
# Generated migration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0002_employeecategory_alter_employee_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='allowancetype',
            name='custom_months',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='عدد الأشهر المخصص'),
        ),
        migrations.AlterField(
            model_name='allowancetype',
            name='frequency',
            field=models.CharField(choices=[('MONTHLY', 'شهري'), ('ANNUAL', 'سنوي'), ('BIENNIAL', 'كل سنتين'), ('CUSTOM', 'مخصص'), ('ONE_TIME', 'مرة واحدة')], max_length=20, verbose_name='تكرار البدل'),
        ),
        migrations.AddField(
            model_name='employee',
            name='ticket_type',
            field=models.CharField(choices=[('ANNUAL', 'سنوي'), ('BIENNIAL', 'كل سنتين')], default='ANNUAL', max_length=20, verbose_name='نوع التذكرة'),
        ),
        migrations.AddField(
            model_name='employee',
            name='family_ticket_cost',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='تكلفة التذاكر العائلية'),
        ),
    ]
