# Generated by Django 1.10.7 on 2017-09-25 05:39

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("codenerix", "0019_auto_20170725_1822"),
    ]

    operations = [
        migrations.CreateModel(
            name="RemoteLog",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="Created",
                    ),
                ),
                (
                    "updated",
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name="Updated",
                    ),
                ),
                ("data", models.TextField(verbose_name="Data")),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "abstract": False,
                "default_permissions": (
                    "add",
                    "change",
                    "delete",
                    "view",
                    "list",
                ),
            },
        ),
    ]
