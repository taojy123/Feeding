# -*- coding: utf-8 -*-
# Generated by Django 1.11.8 on 2018-08-07 03:42
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('feeding', '0002_feeding_ml'),
    ]

    operations = [
        migrations.AlterField(
            model_name='feeding',
            name='position',
            field=models.IntegerField(choices=[(1, '\u5de6'), (2, '\u53f3'), (3, '\u624b\u5582')], default=1),
        ),
    ]
