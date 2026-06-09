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
import imghdr  # pylint: disable=deprecated-module  # provided by standard-imghdr on 3.13+
import io
import json
import os
import random
import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any, Protocol

from captcha.widgets import ReCaptcha
from django import forms
from django.conf import settings
from django.core.files.base import File
from django.core.serializers.json import DjangoJSONEncoder
from django.urls import resolve, reverse
from django.utils import formats
from django.utils.choices import BlankChoiceIterator
from django.utils.encoding import smart_str
from django.utils.html import escapejs
from django.utils.safestring import mark_safe
from django.utils.translation import get_language, gettext as _

from codenerix.helpers import get_class


class _ChoiceFieldLike(Protocol):
    # Minimal structural type for the bound form field these widgets use:
    # only `.choices` (iterable of (value, label)) is accessed on it.
    choices: Iterable[tuple[Any, Any]]


class StaticSelectMulti(forms.widgets.SelectMultiple):
    __language = None
    # Contract attributes set by concrete subclasses (static/dynamic) or by the
    # bound field (field). Declared for the type checker only; no runtime default,
    # so the existing `hasattr(self, "field")` guards keep working unchanged.
    static: bool
    dynamic: bool
    field: _ChoiceFieldLike

    def __init__(self, *args, **kwargs):
        targs = None
        if args:
            targs = args[0]
        if kwargs:
            targs = kwargs
        if targs:
            # common
            self.is_required = targs.get("is_required", False)
            self.form_name = targs.get("form_name", "")
            self.field_name = targs.get("field_name", "")
            # static
            self.choices = targs.get("choices", "")
            # dynamic
            self.autofill_deepness = targs.get("autofill_deepness", 2)
            self.autofill_url = targs.get("autofill_url", "")
            self.autofill = targs.get("autofill_related", [])
        super().__init__(*args, **kwargs)

    def set_language(self, language):
        self.__language = language

    def value_from_datadict(self, data, files, name):
        # Get value
        value = super().value_from_datadict(data, files, name)

        # Decompress list(list) to list
        if isinstance(value, list) and len(value) == 1 and isinstance(value[0], list):
            value = value[0]

        # Let Django do its work
        return value

    def render(self, name, value, attrs=None, renderer=None):
        # Initialization
        # required=self.attrs.get('ng-required','false')
        vmodel = self.field_name
        # vid=attrs.get('id','id_{0}'.format(name))
        # vstyle=attrs.get('style','')
        vform = self.form_name
        placeholder = escapejs(_("Press * and select an option"))
        if value is None:
            value = []
        valuejs = []

        # Prepare dynamic search
        if self.dynamic:
            # Check if autofill_url is defined
            if not self.autofill_url:
                raise OSError("autofill_url not defined")

            # Prepare link
            vurl = reverse(self.autofill_url, kwargs={"search": "a"})[:-1]
            # Get access to the get_label() method and request for the
            # label of the bound input
            if value:
                func = resolve(vurl + "*").func
                clss = get_class(func)
                if clss and self.__language:
                    clss.language = self.__language  # pyright: ignore[reportAttributeAccessIssue]
                # label = clss().get_label(value)

            # Prepare foreign params
            foreign_params = f"http,'{vurl}',amc_items,{{"
            comma = False
            for field in self.autofill:
                if ":" in field:
                    field_filter = field.split(":")[-1]
                    field = field.split(":")[0]
                else:
                    field_filter = field
                if comma:
                    foreign_params += ","
                else:
                    comma = True
                foreign_params += f"'{field}':{vform}.{field_filter}"
            foreign_params += (
                f"}},amc_select.{vmodel},amc_searchText.{vmodel},{self.autofill_deepness}"
            )
        else:
            foreign_params = ""

        # Prepare initialization string
        init = ""
        if not value:
            value = []
        if self.static and hasattr(self, "field"):
            for key, label in self.field.choices:
                if value == key:
                    valuejs.append(
                        f'{{"id":"{key}","label":"{escapejs(smart_str(label))}"}},',
                    )
                init += f'{{"id":"{key}","label":"{escapejs(smart_str(label))}"}},'
        elif isinstance(self.choices, (BlankChoiceIterator, list)):
            for key, label in self.choices:
                if value == key:
                    valuejs.append(
                        f'{{"id":"{key}","label":"{escapejs(smart_str(label))}"}},',
                    )
                init += f'{{"id":"{key}","label":"{escapejs(smart_str(label))}"}},'
        else:
            # FORCE RELOAD DATAS
            elements = self.choices.queryset  # pyright: ignore[reportAttributeAccessIssue]
            elements._result_cache = None
            if self.dynamic:
                if value and isinstance(value, list):
                    elements = elements.filter(pk__in=value)
                else:
                    elements = []
            for choice in elements:
                init += f'{{"id":"{choice.pk}","label":"{escapejs(smart_str(choice))}"}},'
                if value and isinstance(value, list) and (choice.pk in value):
                    valuejs.append(
                        f'{{"id":"{int(choice.pk)}","label":"{escapejs(smart_str(choice))}"}},',
                    )

        # Build HTML
        html = (
            f'<md-chips ng-model="amc_select.{vmodel}" '
            f'md-autocomplete-snap id="{vmodel}" name="{vmodel}" '
        )
        html += '    md-transform-chip="amc_transformChip($chip)"'
        # html += u'    initial = "loadVegetables()"'
        html += f"    ng-init = 'amc_items.{vmodel} = "
        html += "[" + init + "]"
        if valuejs:
            # html += u" ng-init = 'amc_select.{0} = [".format(vmodel)
            html += f"; amc_select.{vmodel} = ["
            html += "".join(valuejs)
            html += "]'"
        html += "'"
        html += '    md-require-match="amc_autocompleteDemoRequireMatch">'
        html += "    <md-autocomplete"
        html += f'            md-selected-item="amc_selectedItem.{vmodel}"'
        html += f'            md-search-text="amc_searchText.{vmodel}"'
        html += (
            f"            md-items=\"item in amc_querySearch(amc_searchText.{vmodel}, '{vmodel}'"
        )

        # Add the params for dynamic search
        if self.dynamic:
            html += "," + foreign_params

        html += ')"'
        html += '            md-item-text="item.id"'
        html += f'            placeholder="{placeholder}">'
        html += f'        <span md-highlight-text="amc_searchText.{vmodel}">'
        html += "            {{item.label}}</span>"
        html += "    </md-autocomplete>"
        html += "    <md-chip-template>"
        html += "        <span>"
        html += "        {{$chip.label}}"
        html += "        </span>"
        html += "    </md-chip-template>"
        html += "</md-chips>"
        return mark_safe(html)


class StaticSelect(forms.widgets.Select):
    """
    Howto:
    1) The form class must inherit from GenModelForm
    """

    # Set by the bound field; declared for the type checker (no runtime default).
    field: _ChoiceFieldLike

    def __init__(self, *args, **kwargs):
        targs = None
        if args:
            targs = args[0]
        if kwargs:
            targs = kwargs
        if targs:
            self.is_required = targs.get("is_required", False)
            self.form_name = targs.get("form_name", "")
            self.field_name = targs.get("field_name", "")
            self.choices = targs.get("choices", "")
        super().__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        # Initialization
        if attrs:
            required = self.attrs.get("ng-required", "false")
            controller = self.attrs.get("ng-controller", None)
            disabled = self.attrs.get("ng-disabled", None)
            change = self.attrs.get("ng-change", "undefined").replace('"', "'").replace("'", "\\'")
            if change != "undefined":
                change = f"'{change}'"
            vmodel = self.field_name
            vid = attrs.get("id", f"id_{name}")
            vstyle = attrs.get("style", "")
            ngreadonly = attrs.get("ng-readonly", "")
        else:
            required = "false"
            controller = None
            disabled = None
            change = "undefined"
            vmodel = self.field_name
            vid = f"id_{name}"
            vstyle = ""
            ngreadonly = ""
        vform = smart_str(self.form_name)
        placeholder = escapejs(_("Select an option"))
        is_multiple = getattr(self, "multiple", False)

        # Render
        html = f"<input name='{vmodel}' ng-required='{required}' ng-model='{vmodel}' type='hidden'"
        if controller:
            html += f" ng-controller='{controller}' "
        if disabled:
            html += f" ng-disabled='{disabled}' "
        valuejs = None
        if is_multiple:
            if value:
                if isinstance(value, list):
                    valuejs = json.dumps(
                        [int(x) for x in value],
                        cls=DjangoJSONEncoder,
                    )
                else:
                    valuejs = json.dumps(
                        [
                            int(value),
                        ],
                        cls=DjangoJSONEncoder,
                    )

                html += f' ng-init="{vmodel}={valuejs}"'
            else:
                html += f' ng-init="{vmodel}=[]"'
        elif value:
            html += f" ng-init=\"{vmodel}='{value}'\""

        html += ">"

        html += "<ui-select "
        if disabled:
            html += f" ng-disabled='{disabled}' "
        else:
            html += f' ng-disabled="{ngreadonly}"'
        if controller:
            html += f" ng-controller='{controller}' "
        if is_multiple:
            html += " multiple "
        # Build options
        html += f' ng-init="options.{vmodel}=['
        ini = None
        list_value = []
        index = 0

        if is_multiple and not value:
            value = []
        if hasattr(self, "field"):
            for key, label in self.field.choices:
                if value == key:
                    ini = index
                html += f"{{'id':'{key}','label':'{escapejs(smart_str(label))}'}},"
                index += 1
        elif isinstance(self.choices, (BlankChoiceIterator, list)):
            for key, label in self.choices:
                if value == key:
                    ini = index
                html += f"{{'id':'{key}','label':'{escapejs(smart_str(label))}'}},"
                index += 1
        else:
            if not is_multiple:
                html += f"{{'id':null, 'label':'{placeholder}'}}, "

            for choice in self.choices.queryset:  # pyright: ignore[reportAttributeAccessIssue]
                if value == choice.pk:  # only not multiple
                    ini = index
                html += f"{{'id':'{choice.pk}','label':'{escapejs(smart_str(choice))}'}},"
                if value and isinstance(value, list) and (str(choice.pk) in value):
                    list_value.append(
                        {"id": int(choice.pk), "label": str(choice)},
                    )
                index += 1

            # raise Exception(html)
        html += "];"
        # Select if we have already one
        if ini is not None:
            if is_multiple:
                html += f"$select.selected=options.{vmodel};"
            else:
                html += f"$select.placeholder='options.{vmodel}[{ini}];'"
            # ok html += u"$select.selected=options.{0}".format(vmodel,ini)

        if is_multiple and value is not None:
            html += "{}.{}.$setViewValue({});".format(
                vform,
                vmodel,
                json.dumps(list_value, cls=DjangoJSONEncoder).replace(
                    '"',
                    "'",
                ),
            )
            # html += u"$parent.{1}.$setViewValue({2});".format(vform,
            # vmodel,json.dumps(
            #     list_value,
            #     cls=DjangoJSONEncoder
            # ).replace('"', "'"))

        html += ' "'
        # Build the rest of the tag
        html += f' id="{vid}"'
        html += f' ng-model="$parent.{vmodel}"'
        if is_multiple:
            html += (
                f" on-select=\"selectedOptionSelect({vform}.{vmodel},'{valuejs}',{change}, "
                '$parent, $select.selected)"'
            )
        else:
            if value is None:
                value = "null"
            else:
                value = f"'{value}'"
            html += (
                f' on-select="selectedOptionSelect({vform}.{vmodel},{value},{change}, '
                '$parent, $select.selected)"'
            )
        html += ' theme="bootstrap"'
        html += ' ng-disabled="disabled"'
        html += ' reset-search-input="false"'
        html += ">"
        html += f' <ui-select-match placeholder="{placeholder}">'
        if is_multiple:
            html += "    {{$item.label}}"
        else:
            html += "    {{$select.selected.label}}"
        html += " </ui-select-match>"
        html += " <ui-select-choices"
        html += f'     style="{vstyle}"'
        html += f'     repeat="value.id as value in options.{vmodel}'
        html += '            | filter: {label: $select.search}">'
        html += '     <div ng-bind-html="value.label| highlightSelect: $select.search"></div>'
        html += " </ui-select-choices>"
        html += "</ui-select>"
        # Return result
        return mark_safe(html)


class DynamicSelectInputWidget:
    """
    Howto:

    1) The form class must inherit from GenModelForm

    2) In the form class add inside the Meta class a new attribute named
       autofill:
        autofill = {'ng-model':['select', length, baseurl, field1, field2,
                     field3, ...]}

        Meaning:
        - ng-model: model name in AngularJS
        - 'select': it is constant string 'select'
        - length: how many characters the user has to add in the input so a
          search will happen
        - baseurl: reverse url name to reach to the class that we will ask for
          the options to render
        - field1, field2, .... : other ng-model fields that are linked to this
          one and use to optimize the option's search

    3) You must define an url with a reverse name that we will use to
       configure baseurl

    4) The target (view) for this url (reverse name) must
       implement GenForeignKey.

    5) If you use the templatetag 'addattr' to add a 'ng-change' remember you
       have to operate with $externalScope which referers to the Scope outside
       the widget, this is usefull when the widget is inside some ng-repeat or
       another artificial structure generated by the programmer. To operate
       with form fields you don't need to operate with $externalScope, just
       point to the form_name.field_name as usually.

    6) In the external fields to be included with your search, you can include
       the tag <FORMNAME> and it will be dynamically replaced with the name of
       the form so you can define external fields like '$scope.var1' and/or
       '<FORMNAME>.field2'
    """

    language = None

    def __init__(self, *args, **kwargs):
        targs = None

        if args:
            targs = args[0]

        if kwargs:
            targs = kwargs

        if targs:
            self.is_required = targs.get("is_required", False)
            self.form_name = targs.get("form_name", "")
            self.field_name = targs.get("field_name", "")
            self.autofill_deepness = targs.get("autofill_deepness", 2)
            self.autofill_url = targs.get("autofill_url", "")
            self.autofill = targs.get("autofill_related", [])

        super().__init__(*args, **kwargs)

    def set_language(self, language):
        self.language = language

    def get_foreign(self, vurl, vform, vmodel, search, function):
        html = f"{function}(http,'{vurl}',options,{{"
        comma = False
        for field in self.autofill:
            if ":" in field:
                field_filter = field.split(":")[-1]
                field = field.split(":")[0]
            else:
                field_filter = field
            if comma:
                html += ","
            else:
                comma = True
            html += "'{}':{}".format(
                field,
                field_filter.replace("<FORMNAME>", vform),
            )
        html += f"}}, '{vmodel}', {vmodel}, {search}, {self.autofill_deepness});\""
        return mark_safe(html)


class DynamicSelect(DynamicSelectInputWidget, forms.widgets.Select):
    # Set by concrete subclasses; declared for the type checker (no runtime default).
    multiple: bool

    def render(self, name, value, attrs=None, renderer=None):
        if not self.autofill_url:
            raise OSError("autofill_url not defined")
        if attrs is None:
            attrs = {}
        # Initialization
        controller = self.attrs.get("ng-controller", None)
        disabled = self.attrs.get("ng-disabled", None)
        required = self.attrs.get("ng-required", "false")
        change = self.attrs.get("ng-change", "undefined").replace('"', "'").replace("'", "\\'")
        if change != "undefined":
            change = f"'{change}'"
        vmodel = self.field_name
        vid = attrs.get("id", f"id_{name}")
        vstyle = attrs.get("style", "")
        vform = smart_str(self.form_name)
        vurl = reverse(self.autofill_url, kwargs={"search": "a"})[:-1]
        label = ""
        # Get access to the get_label() method and request for the label of
        # the bound input
        if value:
            func = resolve(vurl + "*").func
            clss = get_class(func)
            if clss:
                if self.language:
                    clss.language = self.language  # pyright: ignore[reportAttributeAccessIssue]
                label = clss().get_label(value)  # pyright: ignore[reportAttributeAccessIssue]

        # Prepare placeholder
        placeholder = self.attrs.get(
            "placeholder",
            _("Press * or start typing"),
        )
        ngplaceholder = self.attrs.get(
            "ng-placeholder",
            "'{}'".format(_("Press * or start typing")),
        )

        # Detect parent node
        vmodelsp = vmodel.split(".")
        if len(vmodelsp) > 1:
            vparent = ".".join(vmodelsp[:-1])
        else:
            vparent = "$parent"

        # Render
        html = (
            f"<input name='{vmodel}' ng-required='{required}' "
            f"ng-model='{vmodel}' id='{vmodel}' type='hidden'"
        )
        if controller:
            html += f" ng-controller='{controller}' "
        if disabled:
            html += f" ng-disabled='{disabled}' "
        # Set initial value
        if value:
            html += f" ng-init=\"{vmodel}='{value}'\""
        html += ">"
        html += "<ui-select"
        if controller:
            html += f" ng-controller='{controller}' "
        if disabled:
            html += f" ng-disabled='{disabled}' "
        if hasattr(self, "multiple") and self.multiple:
            html += " multiple "
        if value:
            html += (
                f" ng-init=\"options.{vmodel}=[{{'id':null,'label':{ngplaceholder}}},"
                f"{{'id':'{value}','label':'{escapejs(label)}'}}]; "
                f"$select.selected=options.{vmodel}[1];"
            )
            voption = self.get_foreign(
                vurl,
                vform,
                vmodel,
                "'*'",
                "getForeignKeys",
            )
            html += f" option_default={voption}; options.{vmodel}=option_default['rows']"
        else:
            # init options for form modal
            html += f" ng-init=\"options.{vmodel}=[{{'id':null,'label':{ngplaceholder}}}]; \""
        html += " ng-click=\"option_default={}; options.{}=option_default['rows']".format(
            self.get_foreign(vurl, vform, vmodel, "'*'", "getForeignKeys"),
            vmodel,
        )

        html += f' id="{vid}"'
        html += f' ng-model="{vparent}.{vmodel}"'
        html += (
            f" on-select=\"selectedOptionSelect({vform}.{vmodel},'{value}',{change}, "
            '$parent, $select.selected)"'
        )
        html += ' theme="bootstrap"'
        html += ' ng-disabled="disabled"'
        html += ' reset-search-input="false"'
        html += ">"
        html += f" <ui-select-match placeholder='{placeholder}'>"
        html += ' <div ng-bind-html="$select.selected.label"></div>'
        html += " </ui-select-match>"
        html += " <ui-select-choices"
        html += f'     style="{vstyle}"'
        html += f'     repeat="value.id as value in options.{vmodel}"'
        html += '     refresh="{}"'.format(
            self.get_foreign(
                vurl,
                vform,
                vmodel,
                "$select.search",
                "getForeignKeys",
            ),
        )
        html += '     refresh-delay="0">'
        html += '     <div ng-bind-html="value.label| highlightSelect: $select.search"></div>'
        html += " </ui-select-choices>"
        html += "</ui-select>"
        return mark_safe(html)


class MultiStaticSelect(StaticSelectMulti):
    static = True
    dynamic = False


class MultiDynamicSelect(StaticSelectMulti):
    static = False
    dynamic = True


class MultiStaticSelect_old(StaticSelect):  # noqa: N801 # pylint: disable=invalid-name
    multiple = True


class MultiDynamicSelect_old(DynamicSelect):  # noqa: N801 # pylint: disable=invalid-name
    multiple = True


class DynamicInput(DynamicSelectInputWidget, forms.widgets.Input):
    def render(self, name, value, attrs=None, renderer=None):
        # Requet the field to render normally
        html = super().render(name, value, attrs=attrs)

        # Initialization
        vmodel = self.field_name
        vform = self.form_name
        vurl = reverse(self.autofill_url, kwargs={"search": "a"})[:-1]

        # Render
        ticket = 'uib-typeahead="item.label for item in {}"'.format(
            self.get_foreign(
                vurl,
                vform,
                vmodel,
                "$viewValue",
                "getAutoComplete",
            ),
        )
        ticket += ' typeahead-on-select="autoFillFields($item, $model, $label, $event)"'
        ticket += ' typeahead-wait-ms="800"'
        ticket += ' ng-change="resetAutoComplete()"'

        # Save ticket inside html
        html = html.replace('type="None"', 'type="text"')
        html = html.replace("/>", f"{ticket}/>")

        # Return updated html
        return mark_safe(html)


class FileAngularInput(forms.widgets.FileInput):
    def render(self, name, value, attrs=None, renderer=None):
        if not attrs:
            attrs = {}
        if value is not None:
            attrs.update({"value": value})
        if self.is_required:
            attrs.update({"required": "required"})
        attrs.update(
            {
                "valid-file": "valid-file",
                "base-sixty-four-input": "base-sixty-four-input",
            },
        )

        # Hacer link hacia el archivo
        if value and not isinstance(value, dict):
            path_image = f"{settings.MEDIA_ROOT}/{value}"
            if not os.path.exists(path_image):
                value = None
                attrs.pop("value")
                button = super().render(
                    name,
                    value,
                    attrs=attrs,
                )
                html = button
            else:
                button = super().render(
                    name,
                    value,
                    attrs=attrs,
                )
                if imghdr.what(path_image) is not None:
                    image = (
                        f'<img src="{settings.MEDIA_URL}{value}" style="max-height:75px; '
                        'max-width:150px;" />'
                    )
                    link = f'<a href="{settings.MEDIA_URL}{value}" target="_blank">{image}</a>'

                    html = '<div class="row">'
                    html += f'   <div class="col-md-6">{button}</div>'
                    html += f'   <div class="col-md-6">{link}</div>'
                    html += "</div>"
                else:
                    link = (
                        f'<br /><a href="{settings.MEDIA_URL}{value}" '
                        f'target="_blank">{value}</a><br />'
                    )
                    html = link + button
        else:
            button = super().render(
                name,
                value,
                attrs=attrs,
            )
            html = button

        return mark_safe(html)

    def value_from_datadict(self, data, files, name):
        # Get field
        field = data[name]

        if isinstance(field, dict):
            # Prepare filename
            temp_hexname = "{}{}".format(
                field["filename"].encode("ascii", "ignore"),
                random.random(),
            )
            hexname = hashlib.sha1(
                temp_hexname.encode(),
                usedforsecurity=False,
            ).hexdigest()

            ext = field["filename"].split(".")[-1]
            if not ext:
                ext = "dat"

            # Prepare temporal file in memory
            f = io.BytesIO()
            f.name = f"{hexname}.{ext}"
            f.original_name = field["filename"]  # pyright: ignore[reportAttributeAccessIssue]
            f.write(base64.b64decode(field["base64"]))
            f.seek(0)

            # Add the files to FILES
            files[name] = File(f)  # pyright: ignore[reportArgumentType]

            # Let Django do its work
            return super().value_from_datadict(
                data,
                files,
                name,
            )
        else:
            return {}


# class Date2TimeInput(forms.widgets.TextInput):
class Date2TimeInput(forms.widgets.DateTimeInput):
    def render(self, name, value, attrs=None, renderer=None):  # pylint: disable=too-many-statements
        if not attrs:
            attrs = {}

        if "label" in attrs.keys():
            label = attrs.pop("label")
        else:
            label = True

        if self.is_required:
            attrs.update({"required": "required"})
        attrs.update({"class": "form-control ng-valid ng-pristine"})

        value_date = ""  # str(datetime.today().date())
        value_time = ""  # '0000'

        if value and value != "":
            if isinstance(value, datetime):
                value_date = value.date()
                value_time = f"{value.time().hour:02d}{value.time().minute:02d}"
            elif isinstance(value, str):
                # 2015-06-03 00:00 or 2015-06-03 00:00:00
                try:
                    # """
                    # ###########################################################################
                    # # WARNING: I suspect this is a bad patch because it doesn't detect the    #
                    # #          format of the data depending on the Django's localization      #
                    # #          system. It should checked how is being used in                 #
                    # #          method value_from_datadict() from this same class              #
                    # ###########################################################################
                    # """
                    if len(value) == 16:
                        aux = datetime.strptime(value, "%Y-%m-%d %H:%M")
                    elif len(value) == 19:
                        aux = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                    else:
                        aux = None
                except ValueError:
                    aux = None

                if aux:
                    value_date = aux.date()
                    value_time = f"{aux.time().hour:02d}{aux.time().minute:02d}"

        startview = 2
        minview = 2
        maxview = 4
        icon = "calendar"

        # """
        # ##############################################################################
        # # WARNING: Language code should be detected on runtime from the user request #
        # ##############################################################################
        # """
        langcode = settings.LANGUAGE_CODE
        format_date = (
            formats.get_format("DATETIME_INPUT_FORMATS", lang=langcode)[0]
            .replace("%", "")
            .replace("d", "dd")
            .replace("m", "mm")
            .replace("Y", "yyyy")
            .replace("H", "hh")
            .replace("M", "ii")
            .split(" ")[0]
        )
        language = settings.LANGUAGE_CODE
        # language = {{LANGUAGE_CODE|default:"en"}}

        if label:
            html = (
                '<label style="margin-right:10px" '
                'class="pull-right" for="id_date">' + _("Hour") + "</label>"
            )
        else:
            html = ""
        html += '<div class="row">'
        html += '<div class="col-sm-8">'
        html += ' <div class="dropdown">'
        html += f'    <div id="date_{name}" class="input-group date">'

        tmp = []
        for x in attrs:
            y = attrs[x]
            tmp.append(x + '="' + y + '"')
        attributes = " ".join(tmp)

        html += (
            f'        <input type="text" name="{name}" id="id_{name}" '
            f'value="{value_date}" {attributes} />'
        )
        html += (
            '        <span class="input-group-addon">'
            f'<i class="glyphicon glyphicon-{icon}"></i></span>'
        )
        html += "    </div>"
        html += " </div>"
        html += "</div>"
        html += '<div class="col-sm-4">'

        ngmodel = attrs["ng-model"].split("']")
        if len(ngmodel) > 1:
            ngmodel[0] = f"{ngmodel[0]}_time"
            ngmodel = "']".join(ngmodel)
        else:
            ngmodel = attrs["ng-model"] + "_time"
        # attrs['ng-model'] = attrs['ng-model']+'_time'
        attrs["ng-model"] = ngmodel
        tmp = []
        for x in attrs:
            y = attrs[x]
            tmp.append(x + '="' + y + '"')
        attributes = " ".join(tmp)
        html += (
            f'        <input type="text" name="{name}_time" id="id_{name}_time" '
            f'value="{value_time}" maxlength="4" {attributes} />'
        )
        llave = "{"
        html += "</div>"
        html += "</div>"
        html += '<script type="text/javascript"> '
        html += f'$("#date_{name}").datetimepicker({llave}'
        html += f' format: "{format_date}",'
        html += " autoclose: true,"
        html += f' language:"{language}",'
        html += " todayBtn: true,"
        html += " weekStart:1,"
        html += " todayHighlight:true,"
        html += ' pickerPosition:"bottom-left",'
        html += " keyboardNavigation:false,"
        html += f" startView:{startview},"
        html += f" minView:{minview},"
        html += f" maxView:{maxview},"
        html += " minuteStep: 15,"
        html += "});"
        html += "</script>"
        return mark_safe(html)

    def value_from_datadict(self, data, files, name):
        # Get field
        if name in data:
            date = data[name]
            ttime = "00:00"
            if name + "_time" in data:
                ttime = data[name + "_time"].strip()

                if ttime.isnumeric():
                    if len(ttime) == 0:
                        ttime = "00:00"
                    elif len(ttime) <= 2:
                        ttime = f"00:{ttime}"
                    elif len(ttime) == 3:
                        ttime = f"0{ttime[:1]}:{ttime[1:]}"
                    else:
                        ttime = f"{ttime[:2]}:{ttime[2:]}"

            try:
                new_date = datetime.strptime(
                    f"{date} {ttime}",
                    formats.get_format(
                        "DATETIME_INPUT_FORMATS",
                        lang=get_language(),
                    )[0],
                )
            except ValueError:
                new_date = None
            # new_date = "{0} {1}".format(date, ttime)
        else:
            new_date = None
            # new_date = ''

        data[name] = new_date  # pyright: ignore[reportIndexIssue]
        return data[name]


class WysiwygAngularRender(forms.widgets.HiddenInput):
    def render_wysiwyg(
        self,
        ngmodel,
        extraif="",
        force_editors=False,
        attrs=None,
        renderer=None,
    ):
        del renderer  # Not used
        # Recompute ngmodel
        if re.fullmatch(r"\w+", ngmodel):
            ngmodel = f"$parent.{ngmodel}"
        # Compute hashkey
        rhash = str(random.randint(0, 1000))
        if attrs:
            hashkey = attrs.get("id", rhash)
        else:
            hashkey = rhash
        # Editors
        editors = {}
        editors["textangular"] = _("Text Angular")
        editors["quill"] = _("NG Quill")
        editors["raw"] = _("Source code")
        editors["preview"] = _("Preview")
        editors_list = []
        for keyarg, valuearg in editors.items():
            editors_list.append(
                f'"{keyarg}":{{"key":"{keyarg}","name":"{smart_str(valuearg)}"}}',
            )
        editors_json = "{" + ",".join(editors_list) + "}"

        # Detect if this field is required
        if self.is_required:
            required = " required"
        else:
            required = ""

        attributes = []
        attributes_ngquill = []
        if attrs:
            for key in attrs.keys():
                if key not in ["id", "class", "ng-model", "ng-init"]:
                    attributes.append(f'{key}="{attrs[key]}"')
                    if key in ["ng-blur", "ng-change"]:
                        attributes_ngquill.append(
                            f'on-content-changed="{attrs[key]}"',
                        )
                    attributes_ngquill.append(
                        f'{key}="{attrs[key]}"',
                    )
        attributes = " ".join(attributes)
        attributes_ngquill = " ".join(attributes_ngquill)
        # Get normal field
        html = ""
        html += f"<div ng-init='editors_{hashkey}={editors_json}'></div>"
        # Render wysiwyg editor's selector
        if force_editors:
            ngshow = ""
        else:
            ngshow = " ng-show='block.type==\"string\"'>"
        html += f"<select ng-model='editor_{hashkey}'{ngshow}>"
        html += (
            f'<option ng-repeat="subeditor in editors_{hashkey}" '
            'value="{{subeditor.key}}">{{subeditor.name}}'
            "</option>"
        )
        html += "</select>"

        # Render wysiwyg editors
        html += (
            f'<div ng-if=\'{extraif}editor_{hashkey}=="preview"\' class="form-control" '
            f'ng-bind-html="{ngmodel}"></div>'
        )
        html += (
            f'<textarea ng-model="{ngmodel}" '
            f'ng-if=\'{extraif}editor_{hashkey}=="raw"\' class="form-control" '
            f'rows="10"{required} {attributes}></textarea>'
        )
        html += (
            f'<ng-quill-editor ng-model="{ngmodel}" '
            f"ng-if='{extraif}editor_{hashkey}==\"quill\"'{required} {attributes_ngquill}>"
            "</ng-quill-editor>"
        )
        html += (
            f'<text-angular ng-model="{ngmodel}" '
            f"ng-if='{extraif}editor_{hashkey}==\"textangular\"'{required} {attributes}>"
            "</text-angular>"
        )
        html += (
            f'<textarea ng-model="{ngmodel}" '
            f"ng-if='{extraif}editor' style='background-color:#fdd'{required} {attributes}>"
            "</textarea>"
        )

        return mark_safe(html)


class WysiwygAngularInput(WysiwygAngularRender):
    def render(self, name, value, attrs=None, renderer=None):
        # Compute hashkey
        rhash = str(random.randint(0, 1000))
        if attrs:
            hashkey = attrs.get("id", rhash)
            # Get model name
            vmodel = attrs.get("ng-model", "")  # .replace("'",'"')
            init = attrs.get("ng-init", "")
        else:
            hashkey = rhash
            vmodel = ""
            init = ""

        if value is None:
            value = ""
        # Render
        html = f"<div ng-init='editor_{hashkey}=\"textangular\"'>"
        html += (
            f'<textarea name="{name}" ng-model="{vmodel}" ng-show=\'false\' '
            f'ng-init="{init}">{value}</textarea>'
        )
        html += self.render_wysiwyg(
            ngmodel=vmodel,
            force_editors=True,
            attrs=attrs,
            renderer=renderer,
        )
        html += "</div>"

        # Return result
        return mark_safe(html)


class MultiBlockWysiwygInput(WysiwygAngularRender):
    def render(self, name, value, attrs=None, renderer=None):
        # Compute hashkey
        rhash = str(random.randint(0, 1000))
        if attrs:
            hashkey = attrs.get("id", rhash)
        else:
            hashkey = rhash

        # Cleaned value
        if value:
            value_clean = value.replace("'", "&#39;")
        else:
            value_clean = value

        # Get model name
        if attrs:
            vmodel = attrs.get("ng-model", "").replace("'", '"')
        else:
            vmodel = ""
        # Get normal field
        html = f"<div ng-init='{vmodel}={{}}; {vmodel}[\"__JSON_DATA__\"]={value_clean}'></div>"
        html += f"<input type='hidden' name='{name}' ng-model='{vmodel}'>"

        # Render blocks with ANGULAR
        html += (
            "<div ng-repeat='(key, block) in "
            f'{vmodel}["__JSON_DATA__"]\' ng-init=\'editor_{hashkey}="quill"\'>'
        )
        html += "<label>{{key}}</label>"

        html += f'<div ng-show="block.deleted"><p class="text-danger">{_("Field deleted in the template")}</p></div>'
        html += self.render_wysiwyg(
            ngmodel="block.value",
            extraif='block.type=="string" && ',
            attrs=attrs,
            renderer=renderer,
        )
        html += "</div>"

        # Return result
        return mark_safe(html)


class VisualHTMLInput(forms.widgets.HiddenInput):
    """
    Example
    service_day_html = forms.CharField(
        label=_("Quota"),  # Optional
        required=False,
        widget=VisualHTMLInput(),
        initial={'selfname': 'service_day_html', 'data': "<div id='<#id#>'
                 ng-init='<#form:service_day_color#>=\"#ff00ff\"'
                 color-contrast='{{<#form:service_day_color#>}}'>
                 {{<#form:service_day_color#>}}</div>"}
    )
    """

    visual = True

    def render(self, name, value, attrs=None, renderer=None):
        # Compute hashkey
        rhash = str(random.randint(0, 1000))
        if attrs:
            hashkey = attrs.get("id", rhash)
            vmodel = attrs.get("ng-model", "").replace("'", '"')
        else:
            hashkey = rhash
            vmodel = ""
        selfname = self.attrs.get("selfname", None)
        value = self.attrs.get("data", None)

        # Process all tags
        if value is not None:
            for keydirty in value.split("<#")[1:]:
                key = keydirty.split("#>")[0]
                keysp = key.split(":")
                actor = keysp[0]
                args = keysp[1:]
                if actor == "form":
                    if selfname:
                        newname = vmodel.replace(selfname, args[0])
                        value = value.replace(f"<#{key}#>", newname)
                    else:
                        raise OSError(
                            "selfname must be included in the attrs from "
                            "the widget with the name of the field in "
                            "the form",
                        )
                elif actor == "id":
                    value = value.replace("<#id#>", hashkey)
                elif actor == "ngmodel":
                    value = value.replace("<#ngmodel#>", vmodel)
        else:
            raise OSError(
                "data must be included in the attrs from the widget "
                "with the name of the field in the form",
            )

        # Return result
        return value


class BootstrapWysiwygInput(forms.widgets.HiddenInput):
    def render(self, name, value, attrs=None, renderer=None):
        # Get model name
        # vmodel = attrs.get('ng-model').replace("'",'"')

        html = _(
            "We are working on this plugin, it will be ready for next version",
        )

        # Return result
        return mark_safe(html)


class GenReCaptchaInput(ReCaptcha):
    # Legacy is added to make the Widget to work as it was designed
    # this field should be True when is being analized to answer an API request
    # and json_details is set to True on the query from the remote client
    # The rest of the time legacy should be kept False
    legacy = False

    def __init__(self, *args, **kwargs):
        # Decide name of the field in the POST
        if "fieldname" in kwargs:
            fieldname = kwargs.pop("fieldname")
        else:
            fieldname = None
        if not fieldname:
            fieldname = "g-recaptcha-response"
        self.recaptcha_response_name = fieldname
        self.recaptcha_challenge_name = fieldname

        # Keep going as usually
        super().__init__(*args, **kwargs)

    #    def __init__(self, public_key=None, use_ssl=None, attrs={}, *args,
    #        **kwargs):
    #        self.public_key = public_key or settings.RECAPTCHA_PUBLIC_KEY
    #        self.use_ssl = use_ssl if use_ssl is not None else
    #        getattr(settings, 'RECAPTCHA_USE_SSL', False)
    #        self.js_attrs = attrs
    #        super(ReCaptcha, self).__init__(*args, **kwargs)

    #    def render(self, name, value, attrs=None, renderer=None):
    #        return mark_safe(u'%s' % client.displayhtml(self.public_key,
    #        self.js_attrs, use_ssl=self.use_ssl))

    def render(self, name, value, attrs=None, renderer=None):
        del renderer  # Not used
        if self.legacy:
            html = super().render(name, value, attrs)
        else:
            html = (
                f'<input ng-model="{name}" name="{name}" id="id_{name}" '
                'type="hidden" ng-required="true">'
            )
            html += f'<div vc-recaptcha key="\'{self.public_key}\'" ng-model="{name}"></div>'
        return mark_safe(html)
