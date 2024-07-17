# Generated by Django 2.2.4 on 2019-11-13 11:27

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("import_export_huey", "0002_auto_20190923_1132"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExportJob",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "file",
                    models.FileField(
                        max_length=255,
                        upload_to="django-import-export-huey-export-jobs",
                        verbose_name="exported file",
                    ),
                ),
                (
                    "processing_initiated",
                    models.DateTimeField(
                        blank=True,
                        default=None,
                        null=True,
                        verbose_name="Have we started processing the file? If so when?",
                    ),
                ),
                (
                    "format",
                    models.CharField(
                        choices=[
                            ("text/csv", "text/csv"),
                            ("application/vnd.ms-excel", "application/vnd.ms-excel"),
                            (
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            ),
                            ("text/tab-separated-values", "text/tab-separated-values"),
                            (
                                "application/vnd.oasis.opendocument.spreadsheet",
                                "application/vnd.oasis.opendocument.spreadsheet",
                            ),
                            ("application/json", "application/json"),
                            ("text/yaml", "text/yaml"),
                            ("text/html", "text/html"),
                        ],
                        max_length=40,
                        null=True,
                        verbose_name="Format of file to be exported",
                    ),
                ),
                (
                    "app_label",
                    models.CharField(
                        max_length=160, verbose_name="App label of model to export from"
                    ),
                ),
                (
                    "model",
                    models.CharField(
                        max_length=160, verbose_name="Name of model to export from"
                    ),
                ),
                (
                    "resource",
                    models.CharField(
                        default="",
                        max_length=255,
                        verbose_name="Resource to use when exporting",
                    ),
                ),
                (
                    "queryset",
                    models.TextField(verbose_name="JSON list of pks to export"),
                ),
                (
                    "author",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="exportjob_create",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="author",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="exportjob_update",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="last updated by",
                    ),
                ),
            ],
        ),
    ]
