from django.core import validators
from django.core.exceptions import ValidationError
from django.forms.widgets import Textarea

MULTI_EMAIL_FIELD_EMPTY_VALUES = validators.EMPTY_VALUES + ("[]",)


class MultiEmailWidget(Textarea):
    is_hidden = False

    def prep_value(self, value):
        """Prepare value before effectively render widget"""
        if value in MULTI_EMAIL_FIELD_EMPTY_VALUES:
            return ""
        elif isinstance(value, str):
            return value
        elif isinstance(value, list):
            return "\n".join(value)
        raise ValidationError("Invalid format.")

    def render(self, name, value, **kwargs):
        value = self.prep_value(value)
        return super().render(name, value, **kwargs)
