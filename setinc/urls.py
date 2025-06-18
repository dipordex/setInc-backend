from drf_yasg import openapi
from api.views import MainView, PublicStopwatchAPI
  # Adjust the import path if send_task_start is in a different module
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view

schema_view = get_schema_view(
    openapi.Info(
        title="Set Inc API documentation",
        default_version='v1',
        description="Set Inc",
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),  # <--- Allow all users
)

urlpatterns = [
    path('', MainView.as_view(), name='main'),
    path('admin/', admin.site.urls),
    path('api/', include(('api.urls', 'api'))),
    path('api/task-tracked-time/', include(('task.urls', 'task'))),
    path('api/alarm/', include(('alarm.urls', 'alarm'))),
    path('swagger.<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),    
    path('accounts/', include('django.contrib.auth.urls')),
    path("api/public/stopwatch/", PublicStopwatchAPI.as_view(), name="public_stopwatch"),
]

if settings.MEDIA_URL and settings.MEDIA_ROOT:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.STATIC_URL and settings.STATIC_ROOT:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
from django.conf.urls.static import static
from django.conf import settings
from django.urls import path, include
# Ensure that the static files are served correctly in development  