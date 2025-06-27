"""
URL configuration for employee_management project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns  # Import i18n_patterns
from django.shortcuts import redirect
from django.views.i18n import set_language

def redirect_to_dashboard(request):
    if request.user.is_authenticated:
        return redirect('employees:dashboard')
    else:
        return redirect('accounts:login')

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('employees/', include('employees.urls')),
    path('', include('employees.urls')),  # Redirect root to employees
    path('set_language/', set_language, name='set_language'),
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)