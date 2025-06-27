from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """نموذج المستخدم المخصص"""
    
    # إضافة حقول إضافية إذا لزم الأمر
    phone_number = models.CharField(max_length=20, blank=True, verbose_name='رقم الهاتف')
    department = models.CharField(max_length=100, blank=True, verbose_name='القسم')
    
    class Meta:
        verbose_name = 'مستخدم'
        verbose_name_plural = 'المستخدمين'
    
    def __str__(self):
        return self.username