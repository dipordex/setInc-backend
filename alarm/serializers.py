from rest_framework import serializers

from api.models import Alarm
from api.validators import user_friendly_timezone_to_iana


class AlarmSerializer(serializers.ModelSerializer):
    time_zone_nice = serializers.SerializerMethodField()

    class Meta:
        model = Alarm
        exclude = ('user',)

    def get_time_zone_nice(self, obj):
        if obj.time_zone:
            time_zone_nice, _ = user_friendly_timezone_to_iana(obj.time_zone, obj.user)
            return time_zone_nice
        return None
