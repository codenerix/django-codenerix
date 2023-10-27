#
# django-codenerix
#
# Codenerix GNU
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

import base64
import hashlib
import operator
from functools import reduce

from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import validate_email
from django.db import models
from django.db.models import Q
from django.utils.encoding import smart_str
from django.utils.translation import gettext_lazy as _

from codenerix.helpers import clean_memcache_item
from codenerix.middleware import get_current_user
from codenerix.models import CodenerixModel, GenLog


class GenPerson(GenLog, models.Model):  # META: Abstract class
    """
    Defines a person
    """

    # Control fields
    user = models.OneToOneField(  # type: ignore[var-annotated]
        User,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="person",
    )
    name = models.CharField(  # type: ignore[var-annotated]
        _("Name"),
        max_length=45,
        blank=False,
        null=False,
    )
    surname = models.CharField(  # type: ignore[var-annotated]
        _("Surname"),
        max_length=90,
        blank=False,
        null=False,
    )
    disabled = models.DateTimeField(  # type: ignore[var-annotated]
        _("Disabled from"),
        null=True,
        blank=True,
    )
    creator = models.ForeignKey(  # type: ignore[var-annotated]
        User,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="creators",
        default=None,
    )

    class Meta(CodenerixModel.Meta):
        abstract = True

    def __str__(self):
        if self.name and self.surname:
            output = "%s %s" % (smart_str(self.name), smart_str(self.surname))
        elif self.name:
            output = self.name
        elif self.surname:
            output = self.surname
        else:
            output = "%s*" % (self.user)
        return smart_str(output)

    def __unicode__(self):
        return self.__str__()

    def __fields__(self, info):
        fields = []
        fields.append(("user__username", _("User")))
        fields.append(("name", _("Name"), 100))
        fields.append(("surname", _("Surname"), 100))
        fields.append(("user__email", _("Email"), 100))
        fields.append(("user__date_joined", _("Created"), 80))
        fields.append(("user__is_active", _("Active"), None, "center"))
        fields.append(("disabled", _("Disabled from")))
        return fields

    def __limitQ__(self, info):  # noqa: N802
        limit = {}
        # If user is not a superuser, the shown records depends on the profile
        if not info.request.user.is_superuser:
            # All the people records shown below must be related with this user
            criterials = []

            # The criterials are not exclusives
            if criterials:
                limit["profile_people_limit"] = reduce(
                    operator.or_,
                    criterials,
                )

        return limit

    def __searchF__(self, info):  # noqa: N802
        tf = {}
        tf["user__is_active"] = (
            _("Active"),
            lambda x: Q(user__is_active=x),
            [(True, _("Yes")), (False, _("No"))],
        )
        return tf

    def __searchQ__(self, info, text):  # noqa: N802
        tf = {}
        tf["username"] = Q(user__username__icontains=text.lower())
        tf["name"] = Q(name__icontains=text)
        tf["surname"] = Q(surname__icontains=text)
        tf["user_email"] = Q(user__email__icontains=text)
        tf["user__date_joined"] = "datetime"
        return tf

    def is_admin(self):
        try:
            return bool(
                self.user.is_superuser or self.user.groups.get(name="Admins"),
            )
        except Exception:
            return False

    def profiles(self):
        """
        return the rolls this people is related with
        """
        limit = []

        if self.is_admin():
            limit.append(_("Administrator"))
        limit.sort()

        return limit

    def delete(self):
        self.clean_memcache()
        return super().delete()

    def lock_delete(self, request=None):
        if request is not None:
            if request.user == self.user:
                return _("Cannot delete to yourself")
            else:
                return super().lock_delete()
        else:
            return super().lock_delete()

    def clean_memcache(self):
        if self.pk:
            prefix = hashlib.md5(usedforsecurity=False)
            prefix.update(
                base64.b64encode(settings.SECRET_KEY.encode("utf-8")),
            )
            clean_memcache_item(
                "person:{}".format(self.pk),
                prefix.hexdigest(),
            )

    def get_grouppermit(self):
        return self.user.groups.all()

    def presave(self, username, password, email, confirm):
        self.clean_memcache()
        # Check username
        # Rewrite username
        username = username.lower()

        # if exist self.user no modify username
        if not self.user and not username:
            raise ValidationError(
                "This person doesn't have a user assigned, can "
                "not change password or email without an user",
            )

        # Check passwords
        if password and confirm and password != confirm:
            raise ValidationError("Passwords do not match")
        if password and (len(password) < settings.PASSWORD_MIN_SIZE):
            raise ValidationError(
                "Password can not be smaller than {} characters".format(
                    settings.PASSWORD_MIN_SIZE,
                ),
            )

        # Check email
        if email:
            validate_email(email)
        else:
            raise ValidationError(
                "Missing email when saving a new person without a "
                "preassigned user",
            )

        # Create user and save it to the database
        if self.user:
            # Check if the user requested to change the username
            if username != self.user.username:
                # Check if the username already exists in the database and
                # it is not me
                already = (
                    User.objects.filter(username=username)
                    .exclude(pk=self.user.pk)
                    .first()
                )
                if already:
                    # Username already in use
                    raise ValidationError(
                        "Username already exists in the database",
                    )
                else:
                    # Set new username
                    self.user.username = username

            # Update password if any
            if password:
                self.user.set_password(password)
            # Update email address
            self.user.email = email
        else:
            # Create new user
            self.user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
            )
            # user creator of the user
            self.creator = get_current_user()

        # Save changes
        self.user.save()

    def refresh_permissions(self, quiet=False):
        # Check we have a user to work with
        if self.user:
            # Clear groups and permisions for this user
            self.user.groups.clear()
            self.user.user_permissions.clear()

            # Collect all groups and unique permissions for this
            # user relationships
            groups = []
            permissions = []
            for x in self._meta.get_fields():
                model = x.related_model

                # Only check roles
                if model and issubclass(model, GenRole):
                    # Get the link
                    link = getattr(self, x.name, None)

                    # Check if the linked class has CodenerixMeta
                    if link and hasattr(link, "CodenerixMeta"):
                        # Get groups and permissions from that class
                        groups += list(
                            getattr(link.CodenerixMeta, "rol_groups", None)
                            or {},
                        )
                        permissions += list(
                            getattr(
                                link.CodenerixMeta,
                                "rol_permissions",
                                None,
                            )
                            or [],
                        )

            # Add groups
            for groupname in set(groups):
                group = Group.objects.filter(name=groupname).first()
                if group is None:
                    # Group not found, remake permissions for all groups with
                    # roles
                    GenPerson.group_permissions(type(self))
                    # Check again
                    group = Group.objects.filter(name=groupname).first()
                    if group is None:
                        raise OSError(
                            f"Group '{groupname} not found in the system. I "
                            "have tried to remake groups but this group is "
                            "not defined as a Role and it doesn't belong to "
                            "the system either",
                        )

                # Add the user to this group
                self.user.groups.add(group)

            # Add permissions
            for permissionname in set(permissions):
                permission = Permission.objects.filter(
                    codename=permissionname,
                ).first()
                if permission is None:
                    raise OSError(
                        "Permission '{}' not found in the system".format(
                            permissionname,
                        ),
                    )

                # Add the permission to this user
                self.user.user_permissions.add(permission)

        else:
            if not quiet:
                raise OSError(
                    "You can not refresh permissions for a Person wich "
                    "doesn't have an associated user",
                )

    @staticmethod
    def group_permissions(clss):
        groupsresult = {}
        for x in clss._meta.get_fields():
            model = x.related_model

            # Check if it is a role
            if model and issubclass(model, GenRole):
                # Check if the class has CodenerixMeta
                if hasattr(model, "CodenerixMeta"):
                    # Get groups and permissions
                    groups = getattr(model.CodenerixMeta, "rol_groups", [])

                    # Add groups
                    if groups:
                        groups_is_dict = type(groups) is dict
                        groupslist = list(set(groups))
                        for groupname in groupslist:
                            # Check permissions just in case something is wrong
                            perms = []
                            if groups_is_dict:
                                for permname in groups[groupname]:
                                    perm = Permission.objects.filter(
                                        codename=permname,
                                    ).first()
                                    # Commented by Juan Soler on a project we
                                    # both are working on. Since this code is
                                    # preventing a proper execution, I will
                                    # comment it as he has done in our project
                                    # and I will wait for him to validate this
                                    # lines
                                    # if perm is None:
                                    #    raise IOError("Permission '{}' not found for group '{}'!".format(permname, groupname)) # noqa: E501
                                    # else:
                                    if perm is not None:
                                        perms.append(perm)

                            # Remember perms for this group
                            if groupname not in groupsresult:
                                groupsresult[groupname] = []
                            groupsresult[groupname] += perms

        # Set permissions for all groups
        for groupname in groupsresult:
            # Get group
            group = Group.objects.filter(name=groupname).first()
            if group is None:
                # Add group if doesn't exists
                group = Group(name=groupname)
                group.save()
            else:
                # Remove all permissions for this group
                group.permissions.clear()

            # Add permissions to the group
            for perm in groupsresult[groupname]:
                group.permissions.add(perm)

    def save(self, *args, **kwargs):
        # Save this person
        answer = super().save(*args, **kwargs)
        # Refresh permissions if possible
        self.refresh_permissions(quiet=True)
        # Return answer
        return answer


class GenRole:
    def save(self, *args, **kwargs):
        # only update permissions for new users
        refresh_permissions = not self.pk
        result = super().save(*args, **kwargs)
        if refresh_permissions:
            person = self.__CDNX_search_person_CDNX__()
            if person:
                person.refresh_permissions(quiet=True)
        return result

    def delete(self, using=None, keep_parents=False):
        person = self.__CDNX_search_person_CDNX__()
        result = super().delete(using=using, keep_parents=keep_parents)
        if person:
            # update permissions
            person.refresh_permissions(quiet=True)
        return result

    def __CDNX_search_person_CDNX__(self):  # noqa: N802
        # search relation with GenPerson
        person = None
        for field in self._meta.get_fields():
            model = field.related_model
            if model and issubclass(model, GenPerson):
                try:
                    person = getattr(self, field.name)
                except ObjectDoesNotExist:
                    pass
                break
        return person

    def CDNX_refresh_permissions_CDNX(self):  # noqa: N802
        person = self.__CDNX_search_person_CDNX__()
        if person:
            person.refresh_permissions(quiet=True)
