from django import forms
from django.forms import inlineformset_factory
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Fieldset
from crispy_forms.bootstrap import FormActions
from .models import Employee, Allowance, AllowanceType
from employees.models import EmployeeCategory

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'employee_number', 'name', 'nationality', 'hire_date', 'id_number',
            'category', 'basic_salary', 'insurance_type', 'num_wives', 'num_children',
            'recruitment_cost', 'training_cost', 'photo', 'is_active'
        ]
        widgets = {
            'hire_date': forms.DateInput(attrs={'type': 'date'}),
            'name': forms.TextInput(attrs={'dir': 'rtl'}),
            'nationality': forms.TextInput(attrs={'dir': 'rtl'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'البيانات الأساسية',
                Row(
                    Column('employee_number', css_class='form-group col-md-6 mb-3'),
                    Column('name', css_class='form-group col-md-6 mb-3'),
                ),
                Row(
                    Column('nationality', css_class='form-group col-md-6 mb-3'),
                    Column('hire_date', css_class='form-group col-md-6 mb-3'),
                ),
                Row(
                    Column('id_number', css_class='form-group col-md-6 mb-3'),
                    Column('category', css_class='form-group col-md-6 mb-3'),
                ),
                Row(
                    Column('photo', css_class='form-group col-md-6 mb-3'),
                    Column('is_active', css_class='form-group col-md-6 mb-3'),
                ),
            ),
            Fieldset(
                'البيانات المالية',
                Row(
                    Column('basic_salary', css_class='form-group col-md-6 mb-3'),
                    Column('insurance_type', css_class='form-group col-md-6 mb-3'),
                ),
            ),
            Fieldset(
                'بيانات العائلة',
                Row(
                    Column('num_wives', css_class='form-group col-md-6 mb-3'),
                    Column('num_children', css_class='form-group col-md-6 mb-3'),
                ),
            ),
            Fieldset(
                'التكاليف الإضافية',
                Row(
                    Column('recruitment_cost', css_class='form-group col-md-6 mb-3'),
                    Column('training_cost', css_class='form-group col-md-6 mb-3'),
                ),
            ),
            FormActions(
                Submit('submit', 'حفظ', css_class='btn btn-primary'),
                HTML('<a href="{% url "employees:employee_list" %}" class="btn btn-secondary">إلغاء</a>'),
            )
        )


class AllowanceForm(forms.ModelForm):
    class Meta:
        model = Allowance
        fields = ['allowance_type', 'amount', 'type', 'notes', 'is_active']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2, 'dir': 'rtl'}),
        }


# إنشاء formset للبدلات
AllowanceFormSet = inlineformset_factory(
    Employee,
    Allowance,
    form=AllowanceForm,
    extra=3,
    can_delete=True,
    fields=['allowance_type', 'amount', 'type', 'notes', 'is_active']
)


class ReportFilterForm(forms.Form):
    """نموذج تصفية التقارير المتقدم"""
    
    # البحث برقم الموظف أو الاسم
    employee_search = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'البحث برقم الموظف أو الاسم...',
            'dir': 'rtl'
        }),
        label='البحث عن موظف'
    )
    
    # تصفية بالجنسية
    nationality = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='الجنسية'
    )
    
    # تصفية بالفئة
    category = forms.ModelChoiceField(
        queryset=EmployeeCategory.objects.all(),
        required=False,
        empty_label="جميع الفئات",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='الفئة'
    )
    # تصفية بالتاريخ
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label='من تاريخ التوظيف'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label='إلى تاريخ التوظيف'
    )
    
    # تصفية بحالة النشاط
    is_active = forms.ChoiceField(
        choices=[
            ('', 'جميع الحالات'),
            ('true', 'نشط'),
            ('false', 'غير نشط')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='حالة الموظف'
    )
    
    # تصفية بنطاق الراتب
    salary_min = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'الحد الأدنى',
            'step': '0.01'
        }),
        label='الراتب الأساسي من'
    )
    
    salary_max = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'الحد الأقصى',
            'step': '0.01'
        }),
        label='الراتب الأساسي إلى'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # ملء خيارات الجنسية من قاعدة البيانات
        try:
            nationalities = Employee.objects.values_list('nationality', flat=True).distinct().order_by('nationality')
            nationality_choices = [('', 'جميع الجنسيات')] + [(nat, nat) for nat in nationalities if nat]
            self.fields['nationality'].widget.choices = nationality_choices
        except:
            self.fields['nationality'].widget.choices = [('', 'جميع الجنسيات')]
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        salary_min = cleaned_data.get('salary_min')
        salary_max = cleaned_data.get('salary_max')
        
        # التحقق من صحة التواريخ
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError('تاريخ البداية يجب أن يكون قبل تاريخ النهاية')
        
        # التحقق من صحة نطاق الراتب
        if salary_min and salary_max and salary_min > salary_max:
            raise forms.ValidationError('الحد الأدنى للراتب يجب أن يكون أقل من الحد الأقصى')
        
        return cleaned_data


class ExcelImportForm(forms.Form):
    """نموذج استيراد ملف Excel"""
    
    excel_file = forms.FileField(
        label='ملف Excel',
        help_text='اختر ملف Excel يحتوي على بيانات الموظفين',
        widget=forms.FileInput(attrs={'accept': '.xlsx,.xls', 'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'excel_file',
            FormActions(
                Submit('submit', 'استيراد البيانات', css_class='btn btn-success'),
                HTML('<a href="{% url "employees:employee_list" %}" class="btn btn-secondary">إلغاء</a>'),
            )
        )