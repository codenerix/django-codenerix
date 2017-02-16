# -*- coding: utf-8 -*-

from django.db import models, IntegrityError
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse_lazy
from django.contrib.auth.models import User
from django.conf import settings

from codenerix.models import CodenerixModel


LANG_CHOICE = (
    ('es', _('Spanish')),
    ('en', _('English')),
)


class Contact(CodenerixModel):
    first_name = models.CharField(verbose_name=_(u'Nombre(s)'), max_length=128)
    last_name = models.CharField(verbose_name=_(u'Apellidos'), max_length=128, blank=True, null=True)
    alias = models.CharField(verbose_name=_(u'Alias'), max_length=32, blank=True, null=True)
    organization = models.CharField(verbose_name=_(u'Organización'), max_length=64, blank=True, null=True)
    borndate = models.DateField(verbose_name=_(u'Cumpleaños'), blank=True, null=True)
    address = models.TextField(verbose_name=_(u'Dirección'), blank=True, null=True)
    created_by = models.ForeignKey(User, verbose_name=_(u'Creado por'), related_name='contacts')

    def __fields__(self, info):
        return (
            ('first_name', _(u'Nombre(s)')),
            ('last_name', _(u'Apellidos')),
            ('alias', _(u'Alias')),
            ('organization', _(u'Organization')),
        )

    @property
    def full_name(self):
        return u'%s %s' % (self.first_name, self.last_name)

    @property
    def details_url(self):
        paths = reverse_lazy('contact_detail', kwargs={'pk': self.pk}).split('/')
        paths[-2] += '#'
        return '/'.join(paths)

    def __searchQ__(self, info, text):
        return {
            'contains_first_name': models.Q(first_name__icontains=text),
            'contains_last_name': models.Q(last_name__icontains=text),
            'contains_alias': models.Q(alias__icontains=text),
            'contains_organization': models.Q(organization__icontains=text),
        }

    def __unicode__(self):
        return self.full_name

    def save(self, *args, **kwards):
        if not self.pk and Contact.objects.all().count() > settings.MAX_REGISTERS:
            raise IntegrityError(_("Ha llegado al limite de registros"))
        return super(Contact, self).save(*args, **kwards)

    class Meta:
        verbose_name = _(u'contacto')
        verbose_name_plural = _(u'contactos')


PHONE_LOCATIONS = (
    (0, _(u'Desconocido')),
    (1, _(u'Móvil')),
    (2, _(u'Trabajo')),
    (3, _(u'Hogar')),
)


class Phone(CodenerixModel):
    location = models.PositiveSmallIntegerField(verbose_name=_(u'ubicación'), choices=PHONE_LOCATIONS, default=0)
    country_prefix = models.PositiveSmallIntegerField(verbose_name=_(u'código pais'), blank=True)
    number = models.PositiveIntegerField(verbose_name=_(u'número'))
    contact = models.ForeignKey(Contact, verbose_name=_(u'contacto'), related_name='phones')

    def __fields__(self, info):
        return (
            ('get_location_display', _(u'Ubicación')),
            ('country_prefix', _(u'Código País')),
            ('number', _(u'Número')),
            ('contact', _(u'Contacto')),
        )

    def __unicode__(self):
        return u'[%s] +%d %d' % (
            self.get_location_display(),
            self.country_prefix,
            self.number
        )

    def save(self, *args, **kwards):
        if not self.pk and Phone.objects.all().count() > settings.MAX_REGISTERS:
            raise IntegrityError(_("Ha llegado al limite de registros"))
        return super(Phone, self).save(*args, **kwards)

    class Meta:
        verbose_name = _(u'teléfono')
        verbose_name_plural = _(u'teléfonos')


class ContactGroup(CodenerixModel):
    name = models.CharField(verbose_name=_(u'nombre'), max_length=32)
    contacts = models.ManyToManyField(Contact, verbose_name=_(u'contactos'), related_name='group')
    created_by = models.ForeignKey(User, verbose_name=_(u'creado por'), related_name='contact_groups')

    @property
    def edit_url(self):
        paths = reverse_lazy('contactgroup_edit', kwargs={'pk': self.pk}).split('/')
        paths[-3] += '#'
        return '/'.join(paths)

    def __fields__(self, info):
        return (
            ('name', _(u'Nombre')),
            ('contacts', _(u'contactos')),
        )

    def __unicode__(self):
        return u'%s' % self.name

    def save(self, *args, **kwards):
        if not self.pk and ContactGroup.objects.all().count() > settings.MAX_REGISTERS:
            raise IntegrityError(_("Ha llegado al limite de registros"))
        return super(ContactGroup, self).save(*args, **kwards)

    class Meta:
        verbose_name = _(u'grupo')
        verbose_name_plural = _(u'grupos')
