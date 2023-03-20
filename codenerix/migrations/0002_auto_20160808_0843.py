# -*- coding: utf-8 -*-
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ("codenerix", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="log",
            name="action_time",
            field=models.DateTimeField(auto_now=True, verbose_name="Fecha"),
        ),
    ]
