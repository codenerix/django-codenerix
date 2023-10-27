from django.db import migrations, models


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
