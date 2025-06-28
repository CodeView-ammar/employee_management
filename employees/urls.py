# Adding a print report path to the urlpatterns.
from django.urls import path
from . import views, views_reports

app_name = 'employees'

urlpatterns = [
    # الصفحة الرئيسية
    path('', views.dashboard, name='dashboard'),

    # إدارة الموظفين
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/create/', views.employee_create, name='employee_create'),
    path('employees/<int:pk>/', views.employee_detail, name='employee_detail'),
    path('employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    path('employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),

    # التقارير
    path('reports/', views.reports_view, name='reports'),
    path('reports/print/', views_reports.print_report, name='print_report'),
    path('reports/comparison/print/', views_reports.print_comparison_report, name='print_comparison_report'),
    path('reports/individual/<int:employee_id>/', views_reports.employee_individual_report, name='employee_individual_report'),
    path('reports/comparison/', views_reports.comparison_report, name='comparison_report'),
    path('reports/advanced/', views_reports.advanced_excel_reports, name='advanced_excel_reports'),

    path('reports/export/', views.export_excel, name='export_excel'),

    # تقارير الموظف الواحد
    path('employees/<int:employee_id>/report/', views_reports.employee_individual_report, name='employee_individual_report'),
    path('employees/<int:employee_id>/cost-breakdown/', views_reports.employee_cost_breakdown, name='employee_cost_breakdown'),
    path('employees/<int:employee_id>/export-report/', views_reports.export_individual_report, name='export_individual_report'),

    # تقارير المقارنة
    path('reports/comparison/', views_reports.comparison_report, name='comparison_report'),

    # تقارير Excel المتقدمة
    path('reports/excel-advanced/', views_reports.advanced_excel_reports, name='advanced_excel_reports'),
    path('reports/export-advanced/', views_reports.export_advanced_excel, name='export_advanced_excel'),

    # الاستيراد والتصدير
    path('import/', views.import_excel, name='import_excel'),
    path('export-template/', views.export_template_excel, name='export_template'),
]