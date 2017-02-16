# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Log',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('action_time', models.DateTimeField(auto_now=True, verbose_name='Date')),
                ('object_id', models.TextField(null=True, verbose_name='Object id', blank=True)),
                ('object_repr', models.CharField(max_length=200, verbose_name='Object repr')),
                ('action_flag', models.PositiveSmallIntegerField(verbose_name='Acci\xf3n')),
                ('change_json', models.TextField(verbose_name='Json', blank=True)),
                ('change_txt', models.TextField(verbose_name='Txt', blank=True)),
                ('content_type', models.ForeignKey(blank=True, to='contenttypes.ContentType', null=True)),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'permissions': (('list_log', 'Can list log'), ('detail_log', 'Can view log')),
            },
        ),
    ]
