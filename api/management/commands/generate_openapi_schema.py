import os
from django.core.management.base import BaseCommand
from django.conf import settings
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg import openapi
from drf_yasg.renderers import SwaggerJSONRenderer, SwaggerYAMLRenderer
import django

class Command(BaseCommand):
    help = 'Generates OpenAPI schema files (JSON and YAML).'

    def handle(self, *args, **options):
        # Ensure Django is set up if this command is run standalone
        if not settings.configured:
            django.setup()

        self.stdout.write(self.style.SUCCESS('Generating OpenAPI schema...'))

        generator = OpenAPISchemaGenerator(
            info=openapi.Info(
                title="My API",
                default_version="v1",
                description="Generated OpenAPI schema file",
            )
        )

        # You might need to adjust this if your API requires specific request context
        # For a public schema, None is often sufficient.
        schema = generator.get_schema(request=None, public=True)

        # Define output paths
        output_dir = settings.BASE_DIR # Or a specific directory like os.path.join(settings.BASE_DIR, 'docs')
        json_file_path = os.path.join(output_dir, "openapi_schema.json")
        yaml_file_path = os.path.join(output_dir, "openapi_schema.yaml")

        # Render and save JSON
        json_output = SwaggerJSONRenderer().render(schema, renderer_context={})
        with open(json_file_path, "wb") as f:
            f.write(json_output)
        self.stdout.write(self.style.SUCCESS(f'JSON schema saved to: {json_file_path}'))

        # Render and save YAML
        yaml_output = SwaggerYAMLRenderer().render(schema, renderer_context={})
        with open(yaml_file_path, "wb") as f:
            f.write(yaml_output)
        self.stdout.write(self.style.SUCCESS(f'YAML schema saved to: {yaml_file_path}'))

        self.stdout.write(self.style.SUCCESS("✅ Schema files generated successfully!"))