from django.contrib import admin
from django.contrib.auth.models import Group
from .models import User, VerificationCode, TemporaryBlockedPhoneNumber, Stopwatch, Lap, Quote, Receipt


class UserAdmin(admin.ModelAdmin):
    list_display = ("id", 'phone_number', 'name', 'date_joined', 'timezone', 'has_subscription')

    fieldsets = (
        (None, {'fields': ('phone_number', 'name', 'timezone', 'is_active', 'has_subscription')}),
    )


class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'verification_code', 'verified')


class TemporaryBlockedPhoneNumberAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'created_at')


class StopwatchAdmin(admin.ModelAdmin):
    list_display = (
        'label', 'date_time', 'longitude', 'latitude', 'address', 'user'
    )


class LapAdmin(admin.ModelAdmin):
    list_display = ('name', 'duration', 'stopwatch')


class QuoteAdmin(admin.ModelAdmin):
    list_display = ('quote',)


class ReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'product_id', 'status', 'created', 'modified', 'payment_expires')
    list_filter = ('status', 'created', 'modified')
    search_fields = ('user__username', 'user__phone_number', 'product_id')


admin.site.register(Receipt, ReceiptAdmin)

admin.site.register(User, UserAdmin)
admin.site.register(VerificationCode, VerificationCodeAdmin)
admin.site.register(TemporaryBlockedPhoneNumber,
                    TemporaryBlockedPhoneNumberAdmin)
admin.site.register(Stopwatch, StopwatchAdmin)
admin.site.register(Lap, LapAdmin)
admin.site.register(Quote, QuoteAdmin)
admin.site.unregister(Group)
