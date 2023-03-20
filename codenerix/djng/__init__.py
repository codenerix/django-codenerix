# -*- coding: utf-8 -*-
import six
from django.forms.forms import BaseForm
from django.forms.forms import DeclarativeFieldsMetaclass
from django.forms.models import BaseModelForm
from django.forms.models import ModelFormMetaclass

from .angular_base import BaseFieldsModifierMetaclass
from .angular_base import NgFormBaseMixin
from .angular_model import NgModelFormMixin  # noqa: F401
from .angular_validation import NgFormValidationMixin  # noqa: F401


class NgDeclarativeFieldsMetaclass(
    BaseFieldsModifierMetaclass,
    DeclarativeFieldsMetaclass,
):
    pass


class NgForm(
    six.with_metaclass(
        NgDeclarativeFieldsMetaclass,
        NgFormBaseMixin,
        BaseForm,
    ),
):
    """
    Convenience class to be used instead of Django's internal
    ``forms.Form`` when declaring a form to be used with AngularJS.
    """


class NgModelFormMetaclass(BaseFieldsModifierMetaclass, ModelFormMetaclass):
    pass


class NgModelForm(
    six.with_metaclass(NgModelFormMetaclass, NgFormBaseMixin, BaseModelForm),
):
    """
    Convenience class to be used instead of Django's internal
    ``forms.ModelForm`` when declaring a model form to be used with AngularJS.
    """
