# Generated by Django 4.2.6 on 2023-10-27 11:24

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("codenerix", "0021_auto_20171218_1039"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="log",
            options={
                "permissions": [
                    ("list_log", "Can list log"),
                    ("detail_log", "Can view log"),
                ],
            },
        ),
    ]
