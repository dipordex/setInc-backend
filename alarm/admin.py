from django.contrib import admin

from api.models import Alarm, DefaultAlarm


@admin.register(Alarm)
class AlarmAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'label', 'time_zone', 'time', 'snooze', 'vibration', 'user', 'task', 'active'
    )
    list_display_links = ('id', 'label')
    search_fields = ('label',)
    list_filter = ('active',)
    fieldsets = (
        ('Time Settings', {
            'fields': ('time_zone', 'time')
        }),
        ('Repeat Settings', {
            'fields': (('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'),)
        }),
        ('Sound Settings', {
            'fields': ('sound_name', 'sound_level')
        }),
        ('Additional Settings', {
            'fields': ('snooze', 'vibration')
        }),
        ('User and Task', {
            'fields': ('user', 'task')
        }),
        ('Status', {
            'fields': ('active',)
        }),
    )


@admin.register(DefaultAlarm)
class DefaultAlarmAdmin(admin.ModelAdmin):
    list_display = ('id', 'sound_name', 'sound_level', 'snooze', 'vibration', 'user')
    list_filter = ('sound_level', 'vibration')
    search_fields = ('sound_name', 'user__phone_number')

    fieldsets = (
        ('Sound Settings', {
            'fields': ('sound_name', 'sound_level')
        }),
        ('Alarm Settings', {
            'fields': ('snooze', 'vibration')
        }),
        ('User Information', {
            'fields': ('user',)
        }),
    )


admin.site.site_header = 'Setinc Administration'
admin.site.site_title = 'Setinc Administration'
