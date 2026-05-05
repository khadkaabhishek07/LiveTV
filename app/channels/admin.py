from django.contrib import admin

from .models import Channel


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ('channel_number', 'name', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
