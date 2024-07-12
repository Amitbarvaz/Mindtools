import json

from django.core import serializers
from django.db.models import Q, QuerySet
from filer.models import File, Folder, Image
from import_export.fields import Field
from import_export.resources import ModelResource

from system.application_services import ProgramExportService
from system.application_services.program_import_export import ProgramImportService
from system.models import Chapter, Content, Program, ProgramGoldVariable, Variable


class ProgramExportResource(ModelResource):

    # def filter_export(self, queryset, **kwargs):
    #     qs = super().filter_export(queryset, **kwargs)
    #     qs = ProgramImportExportService.annotate_program_qs_for_export(qs)
    #     return qs

    # NOT SURE THIS IS THREAD SAFE... MAYBE WILL NEED TO REVERT TO ANNOTATION...
    def export_resource(self, instance, fields=None):
        instance = ProgramExportService(instance).annotate_program_instance_for_export()
        export_fields = self._get_enabled_export_fields(fields)
        return [self.export_field(field, instance) for field in export_fields]

    class Meta:
        model = Program
        fields = ['title', 'display_title', 'about', 'style', 'cover_image_sha1',
                  'sessions', 'chapters', 'modules', 'variables', 'contents', 'images', 'files', 'folders',
                  'admin_note', 'gold_variables', 'is_lock', 'default_program_start_time']

    cover_image_sha1 = Field()
    images = Field()
    files = Field()
    folders = Field()
    variables = Field()
    chapters = Field()
    modules = Field()
    contents = Field()
    sessions = Field()

    def dehydrate_contents(self, obj):
        qs = Content.objects.filter(Q(program=obj) | Q(session__program=obj)).distinct()
        return json.loads(
            serializers.serialize('json', qs, use_natural_primary_keys=True, use_natural_foreign_keys=True))

    def dehydrate_cover_image_sha1(self, obj):
        return obj.cover_image.sha1 if obj.cover_image else ""

    def dehydrate_gold_variables(self, obj):
        qs = ProgramGoldVariable.objects.filter(program=obj).distinct()
        return json.loads(
            serializers.serialize('json', qs, use_natural_primary_keys=True, use_natural_foreign_keys=True))

    def dehydrate_variables(self, obj):
        qs = Variable.objects.filter(name__in=obj.relevant_variables_names_list).distinct()
        data = json.loads(
            serializers.serialize('json', qs, use_natural_primary_keys=True, use_natural_foreign_keys=True))
        for item in data:
            if "program" in item["fields"]:
                item["fields"]["program"] = obj.natural_key()
        return data

    def dehydrate_images(self, obj):
        qs = Image.objects.filter(id__in=obj.file_list_ids).distinct()
        return json.loads(
            serializers.serialize('json', qs))

    def dehydrate_files(self, obj):
        # https://github.com/django-cms/django-filer/issues/887
        klass = File
        klass.objects.queryset_class = QuerySet
        qs = klass.objects.filter(id__in=obj.file_list_ids).distinct()
        return json.loads(
            serializers.serialize('json', qs))

    def dehydrate_folders(self, obj):
        qs = Folder.objects.filter(all_files__id__in=obj.file_list_ids)
        parent_folders = qs.values_list('parent', flat=True)
        qs = Folder.objects.filter(Q(id__in=parent_folders) | Q(all_files__id__in=obj.file_list_ids)).distinct()
        return json.loads(
            serializers.serialize('json', qs))

    def dehydrate_modules(self, obj: Program):
        return json.loads(serializers.serialize('json', obj.module_set.all(), use_natural_primary_keys=True,
                                                use_natural_foreign_keys=True))

    def dehydrate_chapters(self, obj: Program):
        qs = Chapter.objects.filter(Q(id__in=obj.chapter_set.values_list("id", flat=True)) | Q(
            id__in=obj.module_set.values_list("chapter", flat=True)) | Q(
            id__in=Content.objects.filter(Q(program=obj) | Q(session__program=obj)).values_list("chapter", flat=True)
        )).distinct()
        return json.loads(serializers.serialize('json', qs, use_natural_primary_keys=True,
                                                use_natural_foreign_keys=True))

    def dehydrate_sessions(self, obj: Program):
        return json.loads(serializers.serialize('json', obj.session_set.all(), use_natural_primary_keys=True,
                                                use_natural_foreign_keys=True))


class ProgramImportResource(ModelResource):
    class Meta:
        model = Program
        fields = ['title', 'display_title', 'about', 'style', 'default_program_start_time',
                  'admin_note', 'is_lock']
        import_id_fields = ['title']

    def after_import_row(self, row, row_result, **kwargs):
        program = row_result.instance if row_result.instance else row_result.original
        if program is None:
            program = Program.objects.get(id=row_result.object_id)
        ProgramImportService(program, row).import_program_data()
        return super().after_import_row(row, row_result, **kwargs)
