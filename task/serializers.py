from api.models import Task

from django.utils import timezone
from rest_framework import serializers

from api.serializers import TaskCategoriesSerializer


class TaskTrackedTimeSerializer(serializers.ModelSerializer):
    time_difference = serializers.SerializerMethodField()
    category = TaskCategoriesSerializer(read_only=True)
    title = serializers.CharField(allow_blank=False)  # Prevent empty strings

    class Meta:
        model = Task
        fields = ['id', 'title', 'time_difference', 'category']

    @staticmethod
    def get_time_difference(obj) -> int:
        if obj.start_tracked_time:
            print("Received object:", obj)
            now = timezone.now()
            difference = now - obj.start_tracked_time
            print(f"Calculating time difference for task {obj.id}: {difference}")
            return int(difference.total_seconds())
        return 0
