# -*- coding: utf-8 -*-
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ("codenerix", "0005_auto_20160824_1332"),
    ]

    operations = [
        migrations.AlterField(
            model_name="log",
            name="action_flag",
            field=models.PositiveSmallIntegerField(verbose_name=b"Action"),
        ),
    ]
