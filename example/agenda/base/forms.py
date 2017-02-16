# -*- coding: utf-8 -*-
from django.forms import ModelMultipleChoiceField
from django.utils.translation import ugettext as _

from codenerix.forms import GenForm, GenModelForm
from codenerix.fields import GenReCaptchaField
from codenerix.widgets import MultiStaticSelect

from agenda.base.models import Contact, ContactGroup, Phone


class LoginForm(GenForm):
    recaptcha = GenReCaptchaField()

class ContactForm(GenModelForm):

    class Meta:
        model = Contact
        exclude = ['created_by']

    def __groups__(self):
        return [
            (
                None, 12,
                ['first_name', 6],
                ['last_name', 6],
                ['alias', 6],
                ['organization', 6],
                ['borndate', 6],
                ['address', 6],
            )
        ]


class PhoneForm(GenModelForm):

    def __groups__(self):
        return [
            (
                None, 12,
                ['location', 6],
                ['country_prefix', 2],
                ['number', 4],
            )
        ]

    class Meta:
        model = Phone
        exclude = ['contact']


class ContactGroupForm(GenModelForm):

    class Meta:
        model = ContactGroup
        exclude = ['created_by']

    contacts = ModelMultipleChoiceField(
        queryset=Contact.objects.all(),
        label=_(u'Contactos'),
        required=False,
        widget=MultiStaticSelect(attrs={'manytomany': True})
    )

    def __groups__(self):
        return [
            (
                _('Information'), 12,
                ['name', 6],
                ['contacts', 6],
            )
        ]
