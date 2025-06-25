from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm

def login_view(request):
    """صفحة تسجيل الدخول"""
    if request.user.is_authenticated:
        return redirect('employees:dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'مرحباً بك {user.get_full_name() or user.username}')
                
                # إعادة التوجيه للصفحة المطلوبة أو لوحة التحكم
                next_page = request.GET.get('next', 'employees:dashboard')
                return redirect(next_page)
            else:
                messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة')
        else:
            messages.error(request, 'يرجى التحقق من البيانات المدخلة')
    else:
        form = AuthenticationForm()
    
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def logout_view(request):
    """تسجيل الخروج"""
    logout(request)
    messages.success(request, 'تم تسجيل الخروج بنجاح')
    return redirect('accounts:login')

@login_required
def profile_view(request):
    """عرض الملف الشخصي"""
    return render(request, 'accounts/profile.html', {'user': request.user})