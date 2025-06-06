from django.db import models
from django.contrib import admin
from django.forms import Textarea

from api.models import TaskCategory, Task


@admin.register(TaskCategory)
class TaskCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name',)
    list_display_links = ('id', 'name',)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'title', 'category', 'send_notification', 'user', 'done'
    )
    list_display_links = ('id', 'title')
    list_editable = ('send_notification', 'done')
    ordering = ('-date',)

    fieldsets = (
        ('Task Details', {
            'fields': ('title', 'description', 'category', 'user')
        }),
        ('Date & Time', {
            'fields': (
            'date', 'start_time', 'end_time', 'start_tracked_time', 'tracked_time', 'send_notification', 'time_zone')
        }),
        ('Completion Status', {
            'fields': ('done',)
        }),
        ('Location', {
            'fields': ('address', 'longitude', 'latitude')
        }),
    )

    formfield_overrides = {
        models.CharField: {'widget': Textarea(attrs={'rows': 1, 'cols': 40})},
        models.DecimalField: {'widget': Textarea(attrs={'rows': 1, 'cols': 20})},
    }
