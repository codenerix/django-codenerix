# -*- coding: utf-8 -*-
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ("codenerix", "0004_auto_20160824_0757"),
    ]

    operations = [
        migrations.AlterField(
            model_name="log",
            name="action_flag",
            field=models.PositiveSmallIntegerField(verbose_name="Acci\xf3n"),
        ),
    ]
