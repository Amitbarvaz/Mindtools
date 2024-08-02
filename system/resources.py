import logging

from import_export.resources import ModelResource

from system.application_services import ProgramAfterImportRowHandler, ProgramBeforeImportRowHandler
from system.models import Program

logger = logging.getLogger("debug")


class ProgramImportResource(ModelResource):
    class Meta:
        model = Program
        fields = ['title', 'display_title', 'about', 'style', 'default_program_start_time',
                  'admin_note', 'is_lock']
        import_id_fields = ['title']

    def import_row(self, row, instance_loader, **kwargs):
        logger.debug(f"Starting import, row data\n{row}")
        edited_row = ProgramBeforeImportRowHandler(row).run()
        return super().import_row(edited_row, instance_loader, **kwargs)

    def after_import_row(self, row, row_result, **kwargs):
        program = row_result.instance if row_result.instance else row_result.original
        if program is None:
            program = Program.objects.get(id=row_result.object_id)
        logger.debug(f"Handling program after import")
        ProgramAfterImportRowHandler(program, row).import_program_data()
        return super().after_import_row(row, row_result, **kwargs)
