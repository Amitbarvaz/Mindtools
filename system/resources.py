from import_export.resources import ModelResource

from system.models import Program

# This is so the classic behavior of huey import export can behave correctly

class ProgramImportResource(ModelResource):
    class Meta:
        model = Program

class ProgramExportResource(ModelResource):
    class Meta:
        model = Program