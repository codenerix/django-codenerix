# -*- coding: utf-8 -*-
#
# django-codenerix
#
# Copyright 2017 Centrologic Computational Logistic Center S.L.
#
# Project URL : http://www.codenerix.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import operator
import base64
import hashlib
from functools import reduce

from django.db.models import Q
from django.db import models
from django.utils.encoding import smart_text
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User, Group, Permission
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from codenerix.middleware import get_current_user
from django.conf import settings

from codenerix.helpers import clean_memcache_item
from codenerix.models import GenLog


class GenPerson(GenLog, models.Model):  # META: Abstract class
    '''
    Defines a person
    '''
    # Control fields
    user = models.OneToOneField(User, blank=True, null=True, related_name='person')
    name = models.CharField(_("Name"), max_length=45, blank=False, null=False)
    surname = models.CharField(_("Surname"), max_length=90, blank=False, null=False)
    disabled = models.DateTimeField(_("Disabled from"), null=True, blank=True)
    creator = models.ForeignKey(User, blank=True, null=True, related_name='creators', default=None)

    class Meta:
        abstract = True

    def __unicode__(self):
        if self.name and self.surname:
            output = '%s %s' % (smart_text(self.name), smart_text(self.surname))
        elif self.name:
            output = self.name
        elif self.surname:
            output = self.surname
        else:
            output = "%s*" % (self.user)
        return smart_text(output)

    def __fields__(self, info):
        fields = []
        fields.append(('user__username', _('User')))
        fields.append(('name', _('Name'), 100))
        fields.append(('surname', _('Surname'), 100))
        fields.append(('user__email', _('Email'), 100))
        fields.append(('user__date_joined', _('Created'), 80))
        fields.append(('user__is_active', _('Active'), None, 'center'))
        fields.append(('disabled', _('Disabled from')))
        return fields

    def __limitQ__(self, info):
        l = {}
        # If user is not a superuser, the shown records depends on the profile
        if not info.request.user.is_superuser:

            # All the people records shown below must be related with this user
            criterials = []

            # The criterials are not exclusives
            if criterials:
                l["profile_people_limit"] = reduce(operator.or_, criterials)

        return l

    def __searchF__(self, info):
        tf = {}
        tf['user__is_active'] = (_('Active'), lambda x: Q(user__is_active=x), [(True, _('Yes')), (False, _('No'))])
        return tf

    def __searchQ__(self, info, text):
        tf = {}
        tf['username'] = Q(user__username__icontains=text.lower())
        tf['name'] = Q(name__icontains=text)
        tf['surname'] = Q(surname__icontains=text)
        tf['user_email'] = Q(user__email__icontains=text)
        tf['user__date_joined'] = "datetime"
        return tf

    def is_admin(self):
        try:
            return bool(self.user.is_superuser or self.user.groups.get(name='Admins'))
        except:
            return False

    def profiles(self):
        '''
        return the rolls this people is related with
        '''
        l = []

        if self.is_admin():
            l.append(_("Administrator"))
        l.sort()

        return l

    def delete(self):
        self.clean_memcache()
        return super(GenPerson, self).delete()

    def lock_delete(self, request=None):
        if request is not None:
            if request.user == self.user:
                return _("Cannot delete to yourself")
            else:
                return super(GenPerson, self).lock_delete()
        else:
            return super(GenPerson, self).lock_delete()

    def clean_memcache(self):
        if self.pk:
            prefix = hashlib.md5()
            prefix.update(base64.b64encode(settings.SECRET_KEY))
            clean_memcache_item("person:{}".format(self.pk), prefix.hexdigest())

    def get_grouppermit(self):
        return self.user.groups.all()

    def presave(self, username, password, email, confirm):
        self.clean_memcache()
        # Check username
        # Rewrite username
        username = username.lower()

        # if exist self.user no modify username
        if not self.user and not username:
            raise ValidationError("This person doesn't have a user assigned, can not change password or email without an user")

        # Check passwords
        if password and confirm and password != confirm:
            raise ValidationError("Passwords do not match")
        if password and (len(password) < settings.PASSWORD_MIN_SIZE):
            raise ValidationError("Password can not be smaller than {0} characters".format(settings.PASSWORD_MIN_SIZE))

        # Check email
        if email:
            validate_email(email)
        else:
            raise ValidationError("Missing email when saving a new person without a preassigned user")

        # Create user and save it to the database
        if self.user:
            # Update password if any
            if password:
                self.user.set_password(password)
            # Update email address
            self.user.email = email
        else:
            # Create new user
            self.user = User.objects.create_user(username=username, email=email, password=password)
            # user creator of the user
            self.creator = get_current_user()

        # Save changes
        self.user.save()

    def refresh_permissions(self):
        groups = []
        permissions = []
        # get groups
        if hasattr(self, 'CodenerixMeta') and hasattr(self.CodenerixMeta, 'rol_groups'):
            groups = self.CodenerixMeta.rol_groups

        # get permissions of users
        if hasattr(self, 'CodenerixMeta') and hasattr(self.CodenerixMeta, 'rol_permissions'):
            permissions = self.CodenerixMeta.rol_permissions

        # clear permisions
        self.user.groups.clear()
        self.user.user_permissions.clear()

        # add groups
        if groups:
            groups = list(set(groups))
            for groupname in groups:
                group = Group.objects.filter(name=groupname).first()
                if group is None:
                    # add group if not exists
                    group = Group(name=groupname)
                    group.save()
                self.user.groups.add(group)

        # add permissions
        if permissions:
            permissions = list(set(permissions))
            for permision in permissions:
                self.user.user_permissions.add(Permission.objects.filter(codename=permision).first())

        return None


class GenRole(object):
    def save(self, *args, **kwards):
        # only update permissions for new users
        REFRESH_PERMISSIONS = not self.pk
        result = super(GenRole, self).save(*args, **kwards)
        if REFRESH_PERMISSIONS:
            person = self.__CDNX_search_person_CDNX__()
            if person:
                person.refresh_permissions()
        return result

    def delete(self):
        person = self.__CDNX_search_person_CDNX__()
        result = super(GenRole, self).delete()
        if person:
            # update permissions
            person.refresh_permissions()
        return result

    def __CDNX_search_person_CDNX__(self):
        # search relation with GenPerson
        person = None
        for field in self._meta.related_objects:
            if GenPerson in field.related_model.__mro__:
                person = getattr(self, field.name, None)
        return person
