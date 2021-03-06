# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-03-17 21:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedules', '0007_migrate_schedules_to_slots'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schedule',
            name='type',
            field=models.CharField(
                choices=[
                    ('L', 'live'),
                    ('B', 'broadcast'),
                    ('S', 'broadcast syndication'),
                    ('R', 'repetition')],
                max_length=1,
                verbose_name='type'),
        ),
    ]
