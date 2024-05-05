# Generated by Django 2.2 on 2020-08-24 17:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0027_session_is_recurrent'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='session',
            name='is_recurrent',
        ),
        migrations.AddField(
            model_name='session',
            name='interval',
            field=models.IntegerField(default=0, verbose_name='interval delta'),
        ),
    ]
