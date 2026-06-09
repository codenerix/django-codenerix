from django.db import models

from codenerix.multi_email_field.forms import MultiEmailField as MultiEmailFormField


class MultiEmailField(models.Field):
    description = "A multi e-mail field stored as a multi-lines text"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("default", [])
        super().__init__(*args, **kwargs)

    def formfield(self, *args, **kwargs):
        # This is a fairly standard way to set up some defaults
        # while letting the caller override them.
        defaults = {"form_class": MultiEmailFormField}
        defaults.update(kwargs)
        return super().formfield(*args, **defaults)

    def from_db_value(self, value, expression, connection, context=None):
        del expression, connection, context  # Unused parameters
        if value is None:
            return []
        return value.splitlines()

    def get_db_prep_value(self, value, connection, prepared=False):
        if isinstance(value, str):
            return value
        elif isinstance(value, list):
            return "\n".join(value)
        else:
            return ""

    def to_python(self, value):
        if not value:
            return []
        if isinstance(value, list):
            return value
        return value.splitlines()

    def get_internal_type(self):
        return "TextField"
