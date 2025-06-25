from django.contrib import admin
from .models import Employee, AllowanceType, Allowance


class AllowanceInline(admin.TabularInline):
    model = Allowance
    extra = 1
    fields = ['allowance_type', 'amount', 'type', 'notes', 'is_active']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_number', 'name', 'nationality', 'category', 'basic_salary', 'hire_date', 'is_active']
    list_filter = ['category', 'nationality', 'insurance_type', 'is_active']
    search_fields = ['employee_number', 'name', 'id_number']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [AllowanceInline]
    
    fieldsets = (
        ('البيانات الأساسية', {
            'fields': ('employee_number', 'name', 'nationality', 'hire_date', 'id_number', 'category', 'photo')
        }),
        ('البيانات المالية', {
            'fields': ('basic_salary', 'insurance_type')
        }),
        ('بيانات العائلة', {
            'fields': ('num_wives', 'num_children')
        }),
        ('التكاليف الإضافية', {
            'fields': ('recruitment_cost', 'training_cost')
        }),
        ('معلومات النظام', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AllowanceType)
class AllowanceTypeAdmin(admin.ModelAdmin):
    list_display = ['name_arabic', 'name', 'frequency', 'is_active']
    list_filter = ['frequency', 'is_active']
    search_fields = ['name', 'name_arabic']


@admin.register(Allowance)
class AllowanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'allowance_type', 'amount', 'type', 'is_active']
    list_filter = ['allowance_type', 'type', 'is_active']
    search_fields = ['employee__name', 'employee__employee_number', 'allowance_type__name_arabic']