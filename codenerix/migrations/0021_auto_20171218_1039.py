# Generated by Django 2.0 on 2017-12-18 09:39

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("codenerix", "0020_remotelog"),
    ]

    operations = [
        migrations.AddField(
            model_name="log",
            name="username",
            field=models.CharField(
                blank=True,
                default="",
                max_length=200,
                verbose_name="Username",
            ),
        ),
        migrations.AddField(
            model_name="remotelog",
            name="username",
            field=models.CharField(
                blank=True,
                default="",
                max_length=200,
                verbose_name="Username",
            ),
        ),
        migrations.AlterField(
            model_name="remotelog",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
