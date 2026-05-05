from django.contrib import admin

from .models import EmailOTP, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_verified', 'created_at')
    list_filter = ('email_verified',)


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ('user', 'expires_at', 'attempts', 'consumed_at', 'created_at')
    readonly_fields = ('otp_hash', 'created_at')
