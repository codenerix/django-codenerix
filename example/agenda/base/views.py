# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
# Django
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Q
from django.forms.utils import ErrorList
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils.http import urlsafe_base64_decode
from django.utils.translation import ugettext as _

# Codenerix
from codenerix.helpers import get_template
from codenerix.views import GenList, GenCreate, GenCreateModal, GenDetail, GenUpdate, GenUpdateModal, GenDelete, GenForeignKey

# Models
from agenda.base.models import Contact, ContactGroup, Phone

# Forms
from agenda.base.forms import ContactForm, PhoneForm, ContactGroupForm


@login_required
def home(request):
    return render(
        request,
        get_template('home/main', request.user, request.LANGUAGE_CODE),
        {
            'title': _('Home'),
            'contacts': Contact.objects.filter(created_by=request.user)[:10],
            'groups': ContactGroup.objects.filter(created_by=request.user)[:10]
        }
    )


@login_required
def not_authorized(request):
    return render(
        request,
        get_template('base/not_authorized', request.user, request.LANGUAGE_CODE)
    )


@login_required
def status(request, status, answer):
    answerjson = urlsafe_base64_decode(answer)
    status = status.lower()
    if status == 'accept':
        out = 202     # Accepted
    else:
        out = 501     # Not Implemented
    return HttpResponse(answerjson, status=out)


@login_required
def alarms(request):
    return JsonResponse({
        'body': {},
        'head': {
            'total': 0,
            'order': [],
        },
        'meta': {
            'superuser': True,
            'permitsuser': 'DC',
        }
    })


class ContactList(GenList):
    model = Contact
    show_details = True


class ContactCreate(GenCreate):
    model = Contact
    form_class = ContactForm

    def form_valid(self, form):
        if self.model.objects.all().count() > settings.MAX_REGISTERS:
            date_now = datetime.now()
            date_clean = datetime(date_now.year, date_now.month, date_now.day, date_now.hour) + timedelta(hours=1)
            date_diff = date_clean - date_now
            errors = form._errors.setdefault("first_name", ErrorList())
            errors.append(_("Ha llegado al limite de registros. Quedan {} minutos para reestablecer la base de datos".format(date_diff.seconds / 60)))
            return super(ContactCreate, self).form_invalid(form)

        try:
            contact = form.save(commit=False)
        except IntegrityError, e:
            errors = form._errors.setdefault("first_name", ErrorList())
            errors.append(e)
            return super(ContactCreate, self).form_invalid(form)

        contact.created_by = self.request.user
        contact.save()
        return super(ContactCreate, self).form_valid(form)


class ContactDetail(GenDetail):
    model = Contact
    exclude_fields = ['created_by', 'first_name', 'last_name']
    tabs = [
        {
            'id': 'Phone',
            'name': _(u'Teléfonos'),
            'ws': 'phone_sublist',
            'rows': 'base',
        }
    ]
    groups = [
        (
            _(u'Contacto'), 12,
            ['alias', 12, None, None, 'right'],
            ['organization', 12, None, None, 'right'],
            ['borndate', 12, None, None, 'right'],
            ['address', 12, None, None, 'right'],
        )
    ]


class ContactEdit(GenUpdate):
    model = Contact
    form_class = ContactForm


class ContactDelete(GenDelete):
    model = Contact


class ContactForeign(GenForeignKey):
    model = Contact
    label = '{full_name}'

    def get_foreign(self, queryset, search, filters):
        raise Exception('Here!!')
        return queryset.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(alias__icontains=search)
        )[:settings.LIMIT_FOREIGNKEY]


class PhoneList(GenList):
    model = Phone
    linkedit = True
    show_details = False

    def __fields__(self, info):
        return (
            ('get_location_display', _(u'Ubicación')),
            ('country_prefix', _(u'Código País')),
            ('number', _(u'Número')),
        )

    def __limitQ__(self, info):
        return {
            'contact': Q(contact__pk=info.kwargs.get('pk', None))
        }


class PhoneCreate(GenCreateModal):
    model = Phone
    form_class = PhoneForm

    def dispatch(self, *args, **kwargs):
        self._pk = kwargs.get('pk', None)
        return super(PhoneCreate, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        if self.model.objects.all().count() > settings.MAX_REGISTERS:
            date_now = datetime.now()
            date_clean = datetime(date_now.year, date_now.month, date_now.day, date_now.hour) + timedelta(hours=1)
            date_diff = date_clean - date_now
            errors = form._errors.setdefault("location", ErrorList())
            errors.append(_("Ha llegado al limite de registros. Quedan {} minutos para reestablecer la base de datos".format(date_diff.seconds / 60)))
            return super(PhoneCreate, self).form_invalid(form)

        if self._pk is not None:
            contact = get_object_or_404(Contact, pk=self._pk)
            form.instance.contact = contact
        return super(PhoneCreate, self).form_valid(form)


class PhoneDetail(GenDetail):
    model = Phone


class PhoneEdit(GenUpdateModal):
    model = Phone
    form_class = PhoneForm


class PhoneDelete(GenDelete):
    model = Phone


class ContactGroupList(GenList):
    model = ContactGroup


class ContactGroupCreate(GenCreate):
    model = ContactGroup
    form_class = ContactGroupForm
    hide_foreignkey_button = True

    def form_valid(self, form):
        if self.model.objects.all().count() > settings.MAX_REGISTERS:
            date_now = datetime.now()
            date_clean = datetime(date_now.year, date_now.month, date_now.day, date_now.hour) + timedelta(hours=1)
            date_diff = date_clean - date_now
            errors = form._errors.setdefault("name", ErrorList())
            errors.append(_("Ha llegado al limite de registros. Quedan {} minutos para reestablecer la base de datos".format(date_diff.seconds / 60)))
            return super(ContactGroupCreate, self).form_invalid(form)
        try:
            contact = form.save(commit=False)
        except IntegrityError, e:
            errors = form._errors.setdefault("name", ErrorList())
            errors.append(e)
            return super(ContactGroupCreate, self).form_invalid(form)
            
        contact.created_by = self.request.user
        contact.save()
        return super(ContactGroupCreate, self).form_valid(form)


class ContactGroupDetail(GenDetail):
    model = ContactGroup
    exclude_fields = ['created_by']


class ContactGroupEdit(GenUpdate):
    model = ContactGroup
    form_class = ContactGroupForm
    hide_foreignkey_button = True


class ContactGroupDelete(GenDelete):
    model = ContactGroup
