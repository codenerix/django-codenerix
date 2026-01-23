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
from django.utils import timezone
from django.utils.encoding import smart_str
from django.utils.translation import gettext_lazy as _

from codenerix.helpers import clean_memcache_item
from codenerix.middleware import get_current_user
from codenerix.models import CodenerixModel, GenLog


class GenPerson(GenLog):  # META: Abstract class
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

    class Meta(GenLog.Meta):
        abstract = True

    class CodenerixMeta(GenLog.CodenerixMeta):
        pass

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

    def lock_user(self):
        if self.user:
            # Lock the user out by setting is_active to False
            self.user.is_active = False
            # Disabled from now
            self.user.disabled = timezone.now()
            # Set unusable password
            self.user.set_unusable_password()
            # Save changes
            self.user.save()

    def unlock_user(self):
        if self.user:
            # Unlock the user by setting is_active to True
            self.user.is_active = True
            self.user.disabled = None
            self.user.save()

    def profiles(self):
        """
        return the roles this people is related with
        """
        limit = []

        if self.is_admin():
            limit.append(_("Administrator"))
        limit.sort()

        return limit

    def delete(self):
        # Lock user out
        self.lock_user()

        # Clean memcache
        self.clean_memcache()

        # Remove myself from creator field in other persons
        Person = type(self)  # noqa: N806
        Person.objects.filter(creator=self.user).update(creator=None)

        # Delete person
        return self.user.delete()

    def lock_delete(self):
        if get_current_user() == self.user:
            return _("Cannot delete to yourself")
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

    def presave(
        self,
        username,
        password,
        email,
        confirm,
        *,
        unusable=False,
        is_staff=None,
        is_superuser=None,
    ):
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
        if not unusable:
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
            if unusable:
                self.user.set_unusable_password()

            elif password:
                self.user.set_password(password)
            # Update email address
            self.user.email = email
        else:
            # Extra args
            if unusable:
                extra_args = {}
            else:
                extra_args = {"password": password}
            # Create new user
            self.user = User.objects.create_user(
                username=username,
                email=email,
                **extra_args,
            )
            if unusable:
                self.user.set_unusable_password()
            # user creator of the user
            self.creator = get_current_user()

        # Set staff and superuser flags
        if is_staff is not None:
            self.user.is_staff = is_staff
        if is_superuser is not None:
            self.user.is_superuser = is_superuser

        # Save changes
        self.user.save()

    def refresh_permissions(self, quiet=False, using=None):
        # Check which database we are using
        if using is None:
            using = self._state.db or "default"
        # Check we have a user to work with
        if self.user:
            # Clear groups and permisions for this user
            self.user.groups.db_manager(using).clear()
            self.user.user_permissions.db_manager(using).clear()

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
                group = (
                    Group.objects.using(using).filter(name=groupname).first()
                )
                if group is None:
                    # Group not found, remake permissions for all groups with
                    # roles
                    GenPerson.group_permissions(type(self), using=using)
                    # Check again
                    group = (
                        Group.objects.using(using)
                        .filter(name=groupname)
                        .first()
                    )
                    if group is None:
                        raise OSError(
                            f"Group '{groupname} not found in the system. I "
                            "have tried to remake groups but this group is "
                            "not defined as a Role and it doesn't belong to "
                            "the system either",
                        )

                # Add the user to this group
                self.user.groups.db_manager(using).add(group)

            # Add permissions
            for permissionname in set(permissions):
                permission = (
                    Permission.objects.using(using)
                    .filter(
                        codename=permissionname,
                    )
                    .first()
                )
                if permission is None:
                    raise OSError(
                        f"Permission '{permissionname}' not "
                        "found in the system",
                    )

                # Add the permission to this user
                self.user.user_permissions.db_manager(using).add(permission)

        else:
            if not quiet:
                raise OSError(
                    "You can not refresh permissions for a Person wich "
                    "doesn't have an associated user",
                )

    @staticmethod
    def group_permissions(clss, using="default"):
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
                                    perm = (
                                        Permission.objects.using(using)
                                        .filter(
                                            codename=permname,
                                        )
                                        .first()
                                    )
                                    if perm is not None:
                                        perms.append(perm)
                                    # else:
                                    #    raise IOError("Permission '{}' not found for group '{}'!".format(permname, groupname)) # noqa: E501

                            # Remember perms for this group
                            if groupname not in groupsresult:
                                groupsresult[groupname] = []
                            groupsresult[groupname] += perms

        # Set permissions for all groups
        for groupname in groupsresult:
            # Get group
            group = Group.objects.using(using).filter(name=groupname).first()
            if group is None:
                # Add group if doesn't exists
                group = Group(name=groupname)
                group.save(using=using)
            else:
                # Remove all permissions for this group
                group.permissions.db_manager(using).clear()

            # Add permissions to the group
            for perm in groupsresult[groupname]:
                group.permissions.db_manager(using).add(perm)

    def save(self, *args, **kwargs):
        # Save this person
        answer = super().save(*args, **kwargs)

        # Check if using was provided
        using = kwargs.get("using", None)

        # Refresh permissions if possible
        self.refresh_permissions(quiet=True, using=using)

        # Return answer
        return answer


class GenRole(CodenerixModel):  # META: Abstract class
    class Meta(CodenerixModel.Meta):
        abstract = True

    class CodenerixMeta(CodenerixModel.CodenerixMeta):
        pass

    def save(self, *args, **kwargs):
        # Determine which database we are working with
        using = (
            kwargs.get("using")
            or self._state.db  # pylint: disable=no-member
            or "default"
        )

        # Only update permissions for new users
        refresh_permissions = not self.pk  # pylint: disable=no-member
        result = super().save(*args, **kwargs)  # pylint: disable=no-member

        # Update permissions for related person
        if refresh_permissions:
            person = self.__CDNX_search_person_CDNX__()
            if person:
                person.refresh_permissions(quiet=True, using=using)
        return result

    def delete(self, using=None, keep_parents=False):
        # Determine the database
        using = (
            using or self._state.db or "default"  # pylint: disable=no-member
        )

        # Get related person
        person = self.__CDNX_search_person_CDNX__()
        result = super().delete(  # pylint: disable=no-member
            using=using,
            keep_parents=keep_parents,
        )
        if person:
            # update permissions
            person.refresh_permissions(quiet=True, using=using)
        return result

    def __CDNX_search_person_CDNX__(  # pylint: disable=invalid-name # noqa: E501,N802
        self,
    ):
        # Search relation with GenPerson
        person = None
        for field in self._meta.get_fields():  # pylint: disable=no-member
            model = field.related_model
            if model and issubclass(model, GenPerson):
                try:
                    person = getattr(self, field.name)
                except ObjectDoesNotExist:
                    pass
                break
        return person

    def CDNX_refresh_permissions_CDNX(  # pylint: disable=invalid-name # noqa: E501,N802
        self,
        using=None,
    ):
        # Allow manual refresh specifying DB
        using = (
            using or self._state.db or "default"  # pylint: disable=no-member
        )

        # Get related person
        person = self.__CDNX_search_person_CDNX__()
        if person:
            person.refresh_permissions(quiet=True, using=using)
