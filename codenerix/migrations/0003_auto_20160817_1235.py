from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("codenerix", "0002_auto_20160808_0843"),
    ]

    operations = [
        migrations.AlterField(
            model_name="log",
            name="action_time",
            field=models.DateTimeField(auto_now=True, verbose_name="Date"),
        ),
    ]
