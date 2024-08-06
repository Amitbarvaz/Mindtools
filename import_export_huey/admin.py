# Copyright (C) 2019 o.s. Auto*Mat

from django import forms
from django.conf import settings
from django.contrib import admin
from django.core.cache import cache
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from . import admin_actions, models
from .models import ExportJob
from .widgets import CustomAjaxFileUploadWidget


class JobWithStatusMixin:
    @admin.display(description=_("Job status info"))
    def job_status_info(self, obj):
        job_status = cache.get(self.direction + "_job_status_%s" % obj.pk)
        if job_status:
            return job_status
        else:
            return obj.job_status


class ImportJobForm(forms.ModelForm):
    model = forms.ChoiceField(label=_("Name of model to import to"))

    class Meta:
        model = models.ImportJob
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        if not kwargs.get("instance"):
            self.base_fields["file"] = forms.Field(label=_("File to be imported"), widget=CustomAjaxFileUploadWidget)
        super().__init__(*args, **kwargs)
        self.fields["model"].choices = [
            (x, x) for x in getattr(settings, "IMPORT_EXPORT_HUEY_MODELS", {}).keys()
        ]
        self.fields["format"].widget = forms.Select(
            choices=self.instance.get_format_choices()
        )


@admin.register(models.ImportJob)
class ImportJobAdmin(JobWithStatusMixin, admin.ModelAdmin):
    direction = "import"
    form = ImportJobForm
    list_display = (
        "model",
        "job_status_info",
        "file",
        "change_summary",
        "imported",
        "author",
        "updated_by",
    )
    readonly_fields = (
        "job_status_info",
        "change_summary",
        "imported",
        "errors",
        "author",
        "updated_by",
        "processing_initiated",
    )
    exclude = ("job_status",)
    search_fields = ["author", "model"]
    list_filter = ("model", "imported")

    actions = (
        admin_actions.run_import_job_action,
        admin_actions.run_import_job_action_dry,
    )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj:
            readonly_fields = ("file",) + readonly_fields
        return readonly_fields


class ExportJobForm(forms.ModelForm):
    class Meta:
        model = models.ExportJob
        exclude = ("site_of_origin",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["resource"].widget = forms.Select(
            choices=self.instance.get_resource_choices()
        )
        self.fields["format"].widget = forms.Select(
            choices=self.instance.get_format_choices()
        )


@admin.register(models.ExportJob)
class ExportJobAdmin(JobWithStatusMixin, admin.ModelAdmin):
    direction = "export"
    form = ExportJobForm
    list_display = (
        "model",
        "app_label",
        "file_download",
        "file_size",
        "job_status_info",
        "author",
        "updated_by",
    )
    readonly_fields = (
        "job_status_info",
        "author",
        "updated_by",
        "app_label",
        "model",
        "file",
        "processing_initiated",
    )
    exclude = ("job_status",)

    list_filter = ("model",)

    def has_add_permission(self, request, obj=None):
        return False

    actions = (admin_actions.run_export_job_action,)

    # The if is a bit fragile...
    @admin.display(description=_("exported file"))
    def file_download(self, obj: ExportJob):
        return mark_safe(f'<a href="{obj.file.url}" download>{obj.file.url.split("/")[-1]}</a>') \
            if obj.file and "complete" in obj.job_status else ""

    @admin.display(description=_("File Size"))
    def file_size(self, obj: ExportJob):
        from django.template.defaultfilters import filesizeformat
        return filesizeformat(obj.file.size) if obj.file else ""
