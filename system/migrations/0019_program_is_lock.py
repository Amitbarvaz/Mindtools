# Generated by Django 2.2 on 2020-06-14 17:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0018_program_gold_variable'),
    ]

    operations = [
        migrations.AddField(
            model_name='program',
            name='is_lock',
            field=models.BooleanField(default=False, verbose_name='is program lock'),
        ),
    ]
