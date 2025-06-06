# generate_openapi_schema.py
import os
import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "setinc.settings")  # replace with your settings module
django.setup()

from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.openapi import Info, License
from drf_yasg import openapi
from django.core.management import call_command
import yaml

schema_generator = OpenAPISchemaGenerator(
    info=openapi.Info(
        title="Set Inc API documentation",
        default_version='v1',
        description="Set Inc API",
        license=License(name="BSD License"),
    )
)

# Create schema
schema = schema_generator.get_schema(request=None, public=True)

# Dump to JSON
with open("swagger_schema.json", "w") as f:
    f.write(schema.to_json())

# Dump to YAML
with open("swagger_schema.yaml", "w") as f:
    yaml.dump(schema, f, sort_keys=False)

print("✅ OpenAPI schema generated as 'swagger_schema.json' and 'swagger_schema.yaml'")
