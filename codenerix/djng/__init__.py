from django import VERSION
from django.forms.forms import BaseForm, DeclarativeFieldsMetaclass
from django.forms.models import BaseModelForm

from .angular_base import BaseFieldsModifierMetaclass, NgFormBaseMixin
from .angular_model import NgModelFormMixin  # noqa: F401

if VERSION[:2] >= (1, 5):
    from .angular_validation import NgFormValidationMixin  # noqa: F401
if VERSION[:2] < (1, 7):
    from .models import (  # type: ignore[import-not-found] # noqa: E501
        PatchedModelFormMetaclass as ModelFormMetaclass,
    )
else:
    from django.forms.models import ModelFormMetaclass


class NgDeclarativeFieldsMetaclass(
    BaseFieldsModifierMetaclass,
    DeclarativeFieldsMetaclass,
):
    pass


class NgForm(
    NgFormBaseMixin,
    BaseForm,
    metaclass=NgDeclarativeFieldsMetaclass,
):
    """
    Convenience class to be used instead of Django's internal ``forms.Form``
    when declaring a form to be used with AngularJS.
    """


class NgModelFormMetaclass(BaseFieldsModifierMetaclass, ModelFormMetaclass):
    pass


class NgModelForm(
    NgFormBaseMixin,
    BaseModelForm,
    metaclass=NgModelFormMetaclass,
):
    """
    Convenience class to be used instead of Django's internal
    ``forms.ModelForm`` when declaring a model form to be used with AngularJS.
    """
