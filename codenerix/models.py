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

import json

from bson import json_util
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_delete, pre_delete
from django.dispatch.dispatcher import receiver
from django.utils.encoding import force_str, smart_str
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_stubs_ext.db.models import TypedModelMeta

from codenerix.helpers import daterange_filter
from codenerix.middleware import get_current_user

# Separator to log
SEPARATOR = "\u8594"
SEPARATOR_HTML = " &rarr; "


class CodenerixMetaType(dict):
    """
    Define type for CodenerixMeta of the instance NOT the class
    Example:
    m = CodenerixMetaType({'first_name': 'Eduardo'}, last_name='Pool', age=24,
    sports=['Soccer'])
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for arg in args:
            if isinstance(arg, dict):
                for k in arg:
                    self[k] = arg[k]

        if kwargs:
            for k in kwargs:
                self[k] = kwargs[k]

    def __getattr__(self, attr):
        return self.get(attr)

    def __setattr__(self, key, value):
        self.__setitem__(key, value)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.__dict__.update({key: value})

    def __delattr__(self, item):
        self.__delitem__(item)

    def __delitem__(self, key):
        super().__delitem__(key)
        del self.__dict__[key]

    def __getnewargs__(self):
        return tuple()

    def __getstate__(self):
        return self.__dict__


class CodenerixModelBase(models.Model):
    class Meta(TypedModelMeta):
        abstract = True

    # return method relation objects
    def __getmro__(self):
        return self.__class__.__mro__

    # recolecta informacion de todas las clases que intervienen en la instancia
    # collects information from all classes that intervene in the instance
    def __init__(self, *args, **kwards):
        self.CodenerixMeta = CodenerixMetaType()

        mro = self.__getmro__()
        for cl in reversed(mro):
            if "CodenerixMeta" in cl.__dict__.keys():
                for key in cl.CodenerixMeta.__dict__.keys():
                    if "__" != key[0:2]:
                        value = getattr(cl.CodenerixMeta, key)
                        if value:
                            if key not in self.CodenerixMeta:
                                self.CodenerixMeta[key] = value
                            else:
                                if isinstance(value, dict):
                                    self.CodenerixMeta[key].update(value)
                                elif isinstance(value, list):
                                    if not isinstance(
                                        self.CodenerixMeta[key],
                                        list,
                                    ):
                                        self.CodenerixMeta[key] = list(
                                            self.CodenerixMeta[key],
                                        )
                                    self.CodenerixMeta[key] += value
                                elif isinstance(self.CodenerixMeta[key], list):
                                    self.CodenerixMeta[key] += list(value)

        return super().__init__(*args, **kwards)


class CodenerixModel(CodenerixModelBase):
    """
    Special methods are
        __fields__: it is a list of fields
            Usage:      fields.append(('key','Name',size:int_in_pixels,'alignment:left|right|center'))
            Example 1:  fields.append(('title',_('Title')))
            Example 2:  fields.append(('title',_('Title'),100,'center'))
            Example 3:  fields.append(('title',_('Title'),None,'center'))   # We don't want to define the size but we want to define the alignment
            Example 4:  fields.append((None,_('Title')))                    # We don't want any ordering in the field Title
            Example 5:  fields.append(('user__username',_('Username')))     # You can define here relationships as well

        __limitQ__:
        __searchQ__:
        __searchF__:
    """  # noqa: E501

    created = models.DateTimeField(  # type: ignore[var-annotated]
        _("Created"),
        editable=False,
        auto_now_add=True,
    )
    updated = models.DateTimeField(  # type: ignore[var-annotated]
        _("Updated"),
        editable=False,
        auto_now=True,
    )

    class Meta(TypedModelMeta):
        abstract = True
        default_permissions = ("add", "change", "delete", "view", "list")

    class CodenerixMeta:
        abstract = None

    def __init__(self, *args, **kwards):
        self.CodenerixMeta = CodenerixMetaType()
        return super().__init__(*args, **kwards)

    def __strlog_add__(self):
        return ""

    def __strlog_update__(self, newobj):
        return ""

    def __strlog_delete__(self):
        return ""

    def __limitQ__(self, info):  # noqa: N802
        return {}

    def __searchQ__(self, info, text):  # noqa: N802
        return {}

    def __searchF__(self, info):  # noqa: N802
        return {}

    def lock_update(self, request=None):
        return None

    def internal_lock_delete(self):
        # if we have a specific lock delete from model
        answer = self.lock_delete()
        if answer is None:
            # for each field
            for related in self._meta.get_fields():
                # check if it is protected
                if (
                    "on_delete" in related.__dict__
                    and related.on_delete == models.PROTECT
                ):
                    # if we have a name
                    field = getattr(self, related.related_name, None)
                    if field:
                        # try to get 'exists' function
                        f_exists = getattr(field, "exists", None)
                        # if we didn't get it or the result from it is positive
                        if f_exists is None or f_exists():
                            # answer that the item is locked
                            answer = _(
                                "Cannot delete item, relationship "
                                "with %(model_name)s",
                            ) % {
                                "model_name": related.related_model._meta.verbose_name,  # noqa: E501
                            }
                            break
        return answer

    def lock_delete(self, request=None):
        return None

    # check lock update
    def clean(self):
        if self.lock_update() is not None:
            raise ValidationError(self.lock_update())
        else:
            return super().clean()


class GenInterface(CodenerixModelBase):
    """
    Check force_methods options in CodenerixMeta class and it makes sure that
    the specified methods exists
    """

    class Meta(TypedModelMeta):
        abstract = True

    class CodenerixMeta:
        """
        force_methods = {'alias': ('method_name', 'Description'), }
        """

        pass

    def __init__(self, *args, **kwards):
        self.CodenerixMeta = CodenerixMetaType()
        super().__init__(*args, **kwards)

        # revisamos que esten implementados los metodos indicados
        # we checked that the indicated methods are implemented
        force_methods = getattr(self.CodenerixMeta, "force_methods", None)
        if force_methods:
            for alias in force_methods.keys():
                method = force_methods[alias]
                if not hasattr(self, method[0]) or not callable(
                    getattr(self, method[0]),
                ):
                    raise OSError(
                        "Method {}() not found in class {}: {}".format(
                            method[0],
                            self._meta.object_name,
                            method[1],
                        ),
                    )
        return super().__init__(*args, **kwards)


@receiver(pre_delete)
def codenerixmodel_delete_pre(sender, instance, **kwargs):
    if (
        not hasattr(instance, "name_models_list")
        and hasattr(instance, "internal_lock_delete")
        and callable(instance.internal_lock_delete)
    ):
        lock_delete = instance.internal_lock_delete()
        if lock_delete is not None:
            raise PermissionDenied(lock_delete)


# We don't use log system when PQPRO_CASSANDRA == TRUE
if not (hasattr(settings, "PQPRO_CASSANDRA") and settings.PQPRO_CASSANDRA):  # type: ignore[misc] # noqa: E501
    from django.contrib.admin.models import ADDITION, CHANGE, DELETION

    TYPE_ACTION = (
        (ADDITION, _("Add")),
        (CHANGE, _("Change")),
        (DELETION, _("Delete")),
    )

    class Log(models.Model):
        """
        Control the possible log
        """

        action_time = models.DateTimeField(  # type: ignore[var-annotated]
            "Date",
            auto_now=True,
        )
        user = models.ForeignKey(  # type: ignore[var-annotated]
            settings.AUTH_USER_MODEL,
            on_delete=models.DO_NOTHING,
            blank=True,
            null=True,
        )
        username = models.CharField(  # type: ignore[var-annotated]
            "Username",
            max_length=200,
            blank=True,
            null=False,
            default="",
        )
        content_type = models.ForeignKey(  # type: ignore[var-annotated]
            ContentType,
            on_delete=models.DO_NOTHING,
            blank=True,
            null=True,
        )
        object_id = models.TextField(  # type: ignore[var-annotated]
            "Object id",
            blank=True,
            null=True,
        )
        object_repr = models.CharField(  # type: ignore[var-annotated]
            "Object repr",
            max_length=200,
        )
        action_flag = models.PositiveSmallIntegerField(  # type: ignore[var-annotated] # noqa: E501
            _("Action"),
            choices=TYPE_ACTION,
        )
        change_json = models.TextField(  # type: ignore[var-annotated]
            "Json",
            blank=True,
            null=False,
        )
        change_txt = models.TextField(  # type: ignore[var-annotated]
            "Txt",
            blank=True,
            null=False,
        )
        snapshot_txt = models.TextField(  # type: ignore[var-annotated]
            "Snapshot Txt",
            blank=True,
            null=False,
        )

        class Meta(TypedModelMeta):
            permissions = [
                ("list_log", "Can list log"),
                ("detail_log", "Can view log"),
            ]

        def show(self, view="html"):
            text = []
            if self.change_txt:
                cambios = json.loads(self.change_txt)
            else:
                cambios = ""
            for c in cambios:
                if isinstance(cambios[c], list):
                    text.append("{}: {}".format(cambios[c][0], cambios[c][1]))
                else:
                    text.append("{}: {}".format(_(c), cambios[c]))

            if view == "html":
                result = mark_safe(
                    "<ul><li>{}</li></ul>".format(
                        "</li><li>".join(text),
                    ).replace(SEPARATOR, SEPARATOR_HTML),
                )
            else:
                result = "\n".join(text)

            return result

        def __unicode__(self):
            return self.show(view="txt")

        def __str__(self):
            return self.__unicode__()

        def action(self):
            # Find the action
            if self.action_flag == ADDITION:
                answer = _("Add")
            elif self.action_flag == CHANGE:
                answer = _("Change")
            elif self.action_flag == DELETION:
                answer = _("Delete")
            else:
                answer = "?"
            # Return answer
            return answer

        def __fields__(self, info):
            fields = []
            fields.append(("action_time", _("Date")))
            fields.append(("user__username", _("Actual user")))
            fields.append(("username", _("Original user")))
            fields.append(("get_action_flag_display", _("Action")))
            # fields.append(('content_type__name', _('APP Name')))
            fields.append(("content_type", _("APP Name")))
            fields.append(("content_type__app_label", _("APP Label")))
            fields.append(("content_type__model", _("APP Model")))
            fields.append(("object_id", _("ID")))
            # fields.append(('object_repr', _('Representation')))
            fields.append(("show", _("Txt")))
            return fields

        def __searchQ__(self, info, text):  # noqa: N802
            tf = {}
            tf["user"] = Q(user__username__icontains=text)
            tf["username"] = Q(username__icontains=text)
            # Flag
            if (
                (text.lower() == "add")
                or (text.lower() == "addition")
                or (text.lower() == _("add"))
                or (text.lower() == _("addition"))
            ):
                tf["action_flag"] = Q(action_flag=ADDITION)
            elif (
                (text.lower() == "change")
                or (text.lower() == "changed")
                or (text.lower() == _("change"))
                or (text.lower() == _("changed"))
            ):
                tf["action_flag"] = Q(action_flag=CHANGE)
            elif (
                (text.lower() == "edit")
                or (text.lower() == "edition")
                or (text.lower() == _("edit"))
                or (text.lower() == _("edition"))
            ):
                tf["action_flag"] = Q(action_flag=CHANGE)
            elif (
                (text.lower() == "delete")
                or (text.lower() == "deleted")
                or (text.lower() == _("delete"))
                or (text.lower() == _("deleted"))
            ):
                tf["action_flag"] = Q(action_flag=DELETION)
            # tf['content_type'] = Q(content_type__name__icontains=text)
            tf["object_id"] = Q(object_id__icontains=text)
            tf["object_repr"] = Q(object_repr__icontains=text)
            tf["action_time"] = "datetime"
            return tf

        def __searchF__(self, info):  # noqa: N802
            tf = {}
            tf["action_time"] = (
                _("Date"),
                lambda x: Q(**daterange_filter(x, "action_time")),
                "daterange",
            )
            tf["get_action_flag_display"] = (
                _("Action"),
                lambda x: Q(action_flag=x),
                list(TYPE_ACTION),
            )
            tf["object_id"] = (_("ID"), lambda x: Q(object_id=x), "input")
            tf["user__username"] = (
                _("Actual user"),
                lambda x: Q(user__username__icontains=x),
                "input",
            )
            tf["username"] = (
                _("Original user"),
                lambda x: Q(username__icontains=x),
                "input",
            )
            tf["content_type__app_label"] = (
                _("APP Label"),
                lambda x: Q(content_type__app_label__icontains=x),
                "input",
            )
            # tf['users']=(
            #   _('User'),
            #   lambda x: Q(user__username=x),[('M','M*'),('S','S*')]
            # )
            return tf

    class GenLog:
        class CodenerixMeta(CodenerixModel.CodenerixMeta):
            log_full = False

        def post_save(self, log):
            # custom post save from application
            pass

        def save(self, **kwargs):
            user = get_current_user()
            if user:
                user_id = user.pk
                username = user.username
            else:
                user_id = None
                username = ""

            model = apps.get_model(
                self._meta.app_label,
                self.__class__.__name__,
            )
            isnew = True
            if self.pk is not None:
                list_obj = model.objects.filter(pk=self.pk)
                isnew = list_obj.count() == 0
                # raise IOError,self.__dict__
            # only attributes changes
            attrs = {}
            attrs_txt = {}
            # attributes from database
            attrs_bd = {}
            if isnew:
                action = ADDITION
                pk = None
            else:
                action = CHANGE
                pk = self.pk
                # Instance object
                # obj = model.objects.get(pk=self.pk)
                obj = list_obj.get()
                for key in obj._meta.get_fields():
                    key = key.name
                    # exclude manytomany
                    if obj._meta.model._meta.local_many_to_many and key in [
                        x.name
                        for x in obj._meta.model._meta.local_many_to_many
                    ]:
                        value = None
                    elif obj._meta.get_fields(include_hidden=True) and key in [
                        x.name
                        for x in obj._meta.get_fields(include_hidden=True)
                        if x.many_to_many and x.auto_created
                    ]:
                        value = None
                    else:
                        value = getattr(obj, key, None)
                    attrs_bd[key] = value

            # comparison attributes
            # for key in self._meta.get_fields():
            aux = None
            list_fields = [x.name for x in self._meta.get_fields()]
            for ffield in self._meta.get_fields():
                key = ffield.name
                # exclude manytomany
                if self._meta.model._meta.local_many_to_many and key in [
                    x.name for x in self._meta.model._meta.local_many_to_many
                ]:
                    field = None
                # elif self._meta.get_all_related_many_to_many_objects() and key in [x.name for x in self._meta.get_all_related_many_to_many_objects()]: # noqa: E501
                elif self._meta.get_fields(include_hidden=True) and key in [
                    x.name
                    for x in self._meta.get_fields(include_hidden=True)
                    if x.many_to_many and x.auto_created
                ]:
                    field = None
                else:
                    field = getattr(self, key, None)

                if key in list_fields:
                    # if (not attrs_bd.has_key(key))
                    # or (field != attrs_bd[key]):
                    if (key not in attrs_bd) or (field != attrs_bd[key]):
                        if field is not None or action == CHANGE:
                            aux = ffield
                            field_txt = field
                            if field_txt is None:
                                field_txt = "---"
                            if isinstance(field, CodenerixModel):
                                field = field.pk

                            try:
                                json.dumps(field, default=json_util.default)
                                if (
                                    key not in attrs_bd
                                    or not self.CodenerixMeta.log_full
                                ):
                                    attrs[key] = field
                                else:
                                    if isinstance(
                                        attrs_bd[key],
                                        CodenerixModel,
                                    ):
                                        attrs[key] = (
                                            attrs_bd[key].pk,
                                            field,
                                        )
                                    else:
                                        attrs[key] = (
                                            attrs_bd[key],
                                            field,
                                        )
                            except Exception:
                                # If related, we don't do anything
                                if getattr(field, "all", None) is None:
                                    field = str(field)
                                    if (
                                        key not in attrs_bd
                                        or not self.CodenerixMeta.log_full
                                    ):
                                        attrs[key] = field
                                    else:
                                        attrs[key] = (
                                            attrs_bd[key],
                                            field,
                                        )

                            if hasattr(ffield, "verbose_name"):
                                try:
                                    is_string = isinstance(
                                        ffield.verbose_name,
                                        unicode,
                                    ) or isinstance(ffield.verbose_name, str)

                                except NameError:
                                    is_string = isinstance(
                                        ffield.verbose_name,
                                        str,
                                    )

                                if is_string:
                                    ffield_verbose_name = ffield.verbose_name
                                else:
                                    ffield_verbose_name = str(
                                        ffield.verbose_name,
                                    )

                                if (
                                    key not in attrs_bd
                                    or not self.CodenerixMeta.log_full
                                ):
                                    attrs_txt[ffield_verbose_name] = force_str(
                                        field_txt,
                                        errors="replace",
                                    )
                                else:
                                    if attrs_bd[key] is None:
                                        attrs_bd[key] = "---"
                                    attrs_txt[key] = (
                                        ffield_verbose_name,
                                        "{}{}{}".format(
                                            force_str(
                                                attrs_bd[key],
                                                errors="replace",
                                            ),
                                            SEPARATOR,
                                            force_str(
                                                field_txt,
                                                errors="replace",
                                            ),
                                        ),
                                    )

            log = Log()
            log.user_id = user_id
            log.username = username
            log.content_type_id = ContentType.objects.get_for_model(self).pk
            log.object_id = pk
            log.object_repr = force_str(self, errors="replace")
            try:
                log.change_json = json.dumps(attrs, default=json_util.default)
            except UnicodeDecodeError:
                log.change_json = json.dumps(
                    {"error": "*JSON_ENCODE_ERROR*"},
                    default=json_util.default,
                )
            try:
                log.change_txt = json.dumps(
                    attrs_txt,
                    default=json_util.default,
                )
            except UnicodeDecodeError:
                log.change_txt = json.dumps(
                    {"error": "*JSON_ENCODE_ERROR*"},
                    default=json_util.default,
                )
            log.action_flag = action
            if pk is None:
                log.snapshot_txt = self.__strlog_add__()
            else:
                log.snapshot_txt = obj.__strlog_update__(self)

            aux = super().save(**kwargs)
            if pk is None:
                # if new element, get pk
                log.object_id = self.pk
            log.save()

            # custom post save from application
            self.post_save(log)

            return aux

    class GenLogFull(GenLog):
        class CodenerixMeta(CodenerixModel.CodenerixMeta):
            log_full = True

    @receiver(post_delete)
    def codenerixmodel_delete_post(sender, instance, **kwargs):
        if not hasattr(instance, "name_models_list") and issubclass(
            sender,
            GenLog,
        ):
            user = get_current_user()
            if user:
                user_id = user.pk
                username = user.username
            else:
                user_id = None
                username = "*Unknown*"
            action = DELETION

            attrs = {}
            attrs_txt = {}

            # ._meta.get_fields() return all fields include related name
            # ._meta.fields return all fields of models

            # list_fields = [x.name for x in instance._meta.get_fields()]
            for ffield in instance._meta.get_fields():
                key = ffield.name
                # exclude manytomany
                if instance._meta.model._meta.local_many_to_many and key in [
                    x.name
                    for x in instance._meta.model._meta.local_many_to_many
                ]:
                    field = None
                # elif self._meta.get_all_related_many_to_many_objects() and key in [x.name for x in self._meta.get_all_related_many_to_many_objects()]:  # noqa: E501
                elif instance._meta.get_fields(
                    include_hidden=True,
                ) and key in [
                    x.name
                    for x in instance._meta.get_fields(include_hidden=True)
                    if x.many_to_many and x.auto_created
                ]:
                    field = None
                else:
                    field = getattr(instance, key, None)

                # If we have information to register
                if field is not None:
                    if isinstance(field, CodenerixModel):
                        attrs[key] = field.pk
                    else:
                        try:
                            json.dump(field, default=json_util.default)
                            attrs[key] = field
                        except TypeError:
                            # If related, we don't do anything
                            if getattr(field, "all", None) is None:
                                # field_str = str(field)
                                field_str = smart_str(field)
                                attrs[key] = field_str

                    if hasattr(ffield, "verbose_name"):
                        try:
                            is_string = isinstance(
                                ffield.verbose_name,
                                unicode,
                            ) or isinstance(ffield.verbose_name, str)

                        except NameError:
                            is_string = isinstance(ffield.verbose_name, str)

                        if is_string:
                            ffield_verbose_name = ffield.verbose_name
                        else:
                            ffield_verbose_name = str(ffield.verbose_name)

                        attrs_txt[ffield_verbose_name] = force_str(
                            field,
                            errors="replace",
                        )

            log = Log()
            log.user_id = user_id
            log.username = username
            log.content_type_id = ContentType.objects.get_for_model(
                instance,
            ).pk
            log.object_id = instance.pk
            log.object_repr = force_str(instance)
            log.change_json = json.dumps(attrs, default=json_util.default)
            log.change_txt = json.dumps(attrs_txt, default=json_util.default)
            log.snapshot_txt = instance.__strlog_delete__()
            log.action_flag = action
            log.save()

    class RemoteLog(CodenerixModel):
        """
        RemoteLog system
        """

        user = models.ForeignKey(  # type: ignore[var-annotated]
            settings.AUTH_USER_MODEL,
            on_delete=models.DO_NOTHING,
            blank=True,
            null=True,
        )
        username = models.CharField(  # type: ignore[var-annotated]
            "Username",
            max_length=200,
            blank=True,
            null=False,
            default="",
        )
        data = models.TextField(  # type: ignore[var-annotated]
            "Data",
            blank=False,
            null=False,
        )

        def __fields__(self, info):
            fields = []
            fields.append(("pk", _("ID")))
            fields.append(("created", _("Created")))
            fields.append(("user", _("Actual user")))
            fields.append(("username", _("Original user")))
            return fields

        def save(self, **kwargs):
            if self.user:
                self.username = self.user.username
            super().__init__(**kwargs)
