from django.db import models
from multi_email_field.fields import MultiEmailField


class TestModel(models.Model):
    f = MultiEmailField(null=True, blank=True)
    f_default = MultiEmailField(
        default=["test@example.com"],
        null=True,
        blank=True,
    )
