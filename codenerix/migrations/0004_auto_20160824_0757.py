# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('codenerix', '0003_auto_20160817_1235'),
    ]

    operations = [
        migrations.AlterField(
            model_name='log',
            name='action_flag',
            field=models.PositiveSmallIntegerField(verbose_name='Action'),
        ),
    ]
