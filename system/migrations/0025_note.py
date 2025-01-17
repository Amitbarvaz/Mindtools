# Generated by Django 2.2 on 2020-07-14 18:18

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('system', '0024_auto_20200706_0019'),
    ]

    operations = [
        migrations.CreateModel(
            name='Note',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now, verbose_name='timestamp')),
                ('message', models.TextField(verbose_name='message')),
                ('therapist', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='written_notes', to=settings.AUTH_USER_MODEL, verbose_name='therapist')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='notes', to=settings.AUTH_USER_MODEL, verbose_name='user')),
            ],
        ),
    ]
