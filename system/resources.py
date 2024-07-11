import json

from django.core import serializers
from django.db.models import Q, QuerySet
from filer.models import File
from import_export.fields import Field
from import_export.resources import ModelResource

from system.application_services import ProgramImportExportService
from system.models import Chapter, Content, Program, ProgramGoldVariable, Variable


class ProgramExportResource(ModelResource):

    # def filter_export(self, queryset, **kwargs):
    #     qs = super().filter_export(queryset, **kwargs)
    #     qs = ProgramImportExportService.annotate_program_qs_for_export(qs)
    #     return qs

    # NOT SURE THIS IS THREAD SAFE... MAYBE WILL NEED TO REVERT TO ANNOTATION...
    def export_resource(self, instance, fields=None):
        instance = ProgramImportExportService(instance).annotate_program_instance_for_export()
        export_fields = self._get_enabled_export_fields(fields)
        return [self.export_field(field, instance) for field in export_fields]

    class Meta:
        model = Program
        fields = ['title', 'display_title', 'about', 'style', 'cover_image_metadata', 'cover_image_sha1',
                  'sessions', 'chapters', 'modules', 'variables', 'contents', 'files',
                  'admin_note', 'gold_variables', 'is_lock', 'default_program_start_time']

    cover_image_metadata = Field()
    cover_image_sha1 = Field()
    files = Field()
    variables = Field()
    chapters = Field()
    modules = Field()
    contents = Field()
    sessions = Field()

    def dehydrate_contents(self, obj):
        qs = Content.objects.filter(Q(program=obj) | Q(session__program=obj)).distinct()
        return json.loads(
            serializers.serialize('json', qs, use_natural_primary_keys=True, use_natural_foreign_keys=True))

    def dehydrate_cover_image_metadata(self, obj):
        return json.loads(serializers.serialize('json', [obj.cover_image], use_natural_primary_keys=True,
                                                use_natural_foreign_keys=True))[0].get("fields")

    def dehydrate_cover_image_sha1(self, obj):
        return obj.cover_image.sha1

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

    def dehydrate_files(self, obj):
        # https://github.com/django-cms/django-filer/issues/887
        klass = File
        klass.objects.queryset_class = QuerySet
        qs = klass.objects.filter(id__in=obj.file_list_ids).distinct()
        data = json.loads(
            serializers.serialize('json', qs, use_natural_primary_keys=True, use_natural_foreign_keys=True))
        for item in data:
            if "pk" in item:
                del item["pk"]
        return data

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
