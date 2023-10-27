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
import imghdr
import io
import json
import os
import random
import re
from datetime import datetime

from captcha.widgets import ReCaptcha  # type: ignore[import-not-found]
from django import forms
from django.conf import settings
from django.core.files.base import File
from django.urls import resolve, reverse
from django.utils import formats
from django.utils.encoding import smart_str
from django.utils.html import escapejs
from django.utils.translation import get_language
from django.utils.translation import gettext as _

from codenerix.helpers import get_class


class StaticSelectMulti(forms.widgets.Select):
    __language = None

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
            self.autofill_deepness = targs.get("autofill_deepness", 3)
            self.autofill_url = targs.get("autofill_url", "")
            self.autofill = targs.get("autofill_related", [])
        return super().__init__(*args, **kwargs)

    def set_language(self, language):
        self.__language = language

    def render(self, name, value, attrs=None, choices=(), renderer=None):
        # Initialization
        # required=self.attrs.get('ng-required','false')
        vmodel = self.field_name
        # vid=attrs.get('id','id_{0}'.format(name))
        # vstyle=attrs.get('style','')
        vform = self.form_name
        if self.static:
            placeholder = escapejs(_("Press * and select an option"))
        else:
            placeholder = _("Press * or start typing")

            if not self.autofill_url:
                raise OSError("autofill_url not defined")

            vurl = reverse(self.autofill_url, kwargs={"search": "a"})[:-1]
            # Get access to the get_label() method and request for the
            # label of the bound input
            if value:
                func = resolve(vurl + "*").func
                clss = get_class(func)
                if self.__language:
                    clss.language = self.__language
                label = clss().get_label(value)

        if value is None:
            value = []

        valuejs = []

        if self.static:
            init = ""
            if not value:
                value = []
            if hasattr(self, "field"):
                for key, label in self.field.choices:
                    if value == key:
                        valuejs.append(
                            '{{"id":"{0}","label":"{1}"}},'.format(
                                key,
                                escapejs(smart_str(label)),
                            ),
                        )
                    init += '{{"id":"{0}","label":"{1}"}},'.format(
                        key,
                        escapejs(smart_str(label)),
                    )
            elif isinstance(self.choices, list):
                for key, label in self.choices:
                    if value == key:
                        valuejs.append(
                            '{{"id":"{0}","label":"{1}"}},'.format(
                                key,
                                escapejs(smart_str(label)),
                            ),
                        )
                    init += '{{"id":"{0}","label":"{1}"}},'.format(
                        key,
                        escapejs(smart_str(label)),
                    )
            else:
                # FORCE RELOAD DATAS
                elements = self.choices.queryset
                elements._result_cache = None
                for choice in elements:
                    init += '{{"id":"{0}","label":"{1}"}},'.format(
                        choice.pk,
                        escapejs(smart_str(choice)),
                    )
                    if (
                        value
                        and isinstance(value, list)
                        and (choice.pk in value)
                    ):
                        valuejs.append(
                            '{{"id":"{0}","label":"{1}"}},'.format(
                                int(choice.pk),
                                escapejs(smart_str(choice)),
                            ),
                        )
        else:
            init = "getForeignKeys(http,'{0}',amc_items,{{".format(vurl)
            comma = False
            for field in self.autofill:
                if ":" in field:
                    field_filter = field.split(":")[-1]
                    field = field.split(":")[0]
                else:
                    field_filter = field
                if comma:
                    init += ","
                else:
                    comma = True
                init += "'{}':{}.{}".format(field, vform, field_filter)
            init += "}},'{0}',{0},$select.search,{1})\"".format(
                vmodel,
                self.autofill_deepness,
            )

        html = (
            '<md-chips ng-model="amc_select.{0}" '
            'md-autocomplete-snap id="{0}" name="{0}" '.format(vmodel)
        )
        html += '    md-transform-chip="amc_transformChip($chip)"'
        # html += u'    initial = "loadVegetables()"'
        html += "    ng-init = 'amc_items.{} = [".format(vmodel)
        #        {"name":"Broccoli","type":"Brassica","_lowername":"broccoli","_lowertype":"brassica"}
        html += init
        if valuejs:
            # html += u" ng-init = 'amc_select.{0} = [".format(vmodel)
            html += "]; amc_select.{} = [".format(vmodel)
            html += "".join(valuejs)
            html += "]'"
        html += "]'"
        html += '    md-require-match="amc_autocompleteDemoRequireMatch">'
        html += "    <md-autocomplete"
        html += '            md-selected-item="amc_selectedItem.{}"'.format(
            vmodel,
        )
        html += '            md-search-text="amc_searchText.{}"'.format(vmodel)
        html += (
            '            md-items="item in amc_querySearch('
            "amc_searchText.{0}, '{0}', '{0}')\"".format(vmodel)
        )
        html += '            md-item-text="item.id"'
        html += '            placeholder="{}">'.format(placeholder)
        html += '        <span md-highlight-text="amc_searchText.{}">'.format(
            vmodel,
        )
        html += "            {{item.label}}</span>"
        html += "    </md-autocomplete>"
        html += "    <md-chip-template>"
        html += "        <span>"
        html += "        {{$chip.label}}"
        html += "        </span>"
        html += "    </md-chip-template>"
        html += "</md-chips>"
        return html


class StaticSelect(forms.widgets.Select):
    """
    Howto:
    1) The form class must inherit from GenModelForm
    """

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
        return super().__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, choices=(), renderer=None):
        # Initialization
        required = self.attrs.get("ng-required", "false")
        controller = self.attrs.get("ng-controller", None)
        disabled = self.attrs.get("ng-disabled", None)
        change = (
            self.attrs.get("ng-change", "undefined")
            .replace('"', "'")
            .replace("'", "\\'")
        )
        if change != "undefined":
            change = "'{}'".format(change)
        vmodel = self.field_name
        vid = attrs.get("id", "id_{}".format(name))
        vstyle = attrs.get("style", "")
        ngreadonly = attrs.get("ng-readonly", "")
        vform = smart_str(self.form_name)
        placeholder = escapejs(_("Select an option"))
        is_multiple = hasattr(self, "multiple") and self.multiple

        # Render
        html = (
            "<input name='{0}' ng-required='{1}' ng-model='{0}' "
            "type='hidden'".format(vmodel, required)
        )
        if controller:
            html += " ng-controller='{}' ".format(controller)
        if disabled:
            html += " ng-disabled='{}' ".format(disabled)
        valuejs = None
        if is_multiple:
            if value:
                if isinstance(value, list):
                    valuejs = json.dumps([int(x) for x in value])
                else:
                    valuejs = json.dumps(
                        [
                            int(value),
                        ],
                    )

                html += ' ng-init="{}={}"'.format(vmodel, valuejs)
            else:
                html += ' ng-init="{}=[]"'.format(vmodel)
        elif value:
            html += " ng-init=\"{}='{}'\"".format(vmodel, value)

        html += ">"

        html += "<ui-select "
        if disabled:
            html += " ng-disabled='{}' ".format(disabled)
        else:
            html += ' ng-disabled="{}"'.format(ngreadonly)
        if controller:
            html += " ng-controller='{}' ".format(controller)
        if is_multiple:
            html += " multiple "
        # Build options
        html += ' ng-init="options.{}=['.format(vmodel)
        ini = None
        list_value = []
        index = 0

        if is_multiple and not value:
            value = []
        if hasattr(self, "field"):
            for key, label in self.field.choices:
                if value == key:
                    ini = index
                html += "{{'id':'{0}','label':'{1}'}},".format(
                    key,
                    escapejs(smart_str(label)),
                )
                index += 1
        elif isinstance(self.choices, list):
            for key, label in self.choices:
                if value == key:
                    ini = index
                html += "{{'id':'{0}','label':'{1}'}},".format(
                    key,
                    escapejs(smart_str(label)),
                )
                index += 1
        else:
            if not is_multiple:
                html += "{{'id':null, 'label':'{0}'}}, ".format(placeholder)

            for choice in self.choices.queryset:
                if value == choice.pk:  # only not multiple
                    ini = index
                html += "{{'id':'{0}','label':'{1}'}},".format(
                    choice.pk,
                    escapejs(smart_str(choice)),
                )
                if (
                    value
                    and isinstance(value, list)
                    and (str(choice.pk) in value)
                ):
                    list_value.append(
                        {"id": int(choice.pk), "label": str(choice)},
                    )
                index += 1

            # raise Exception(html)
        html += "];"
        # Select if we have already one
        if ini is not None:
            if is_multiple:
                html += "$select.selected=options.{};".format(vmodel)
            else:
                html += "$select.placeholder='options.{}[{}];'".format(
                    vmodel,
                    ini,
                )
            # ok html += u"$select.selected=options.{0}".format(vmodel,ini)

        if is_multiple and value is not None:
            html += "{}.{}.$setViewValue({});".format(
                vform,
                vmodel,
                json.dumps(list_value).replace('"', "'"),
            )
            # html += u"$parent.{1}.$setViewValue({2});".format(vform,
            # vmodel,json.dumps(list_value).replace('"', "'"))

        html += ' "'
        # Build the rest of the tag
        html += ' id="{}"'.format(vid)
        html += ' ng-model="$parent.{}"'.format(vmodel)
        if is_multiple:
            html += (
                " on-select=\"selectedOptionSelect({}.{},'{}',{}, "
                '$parent, $select.selected)"'.format(
                    vform,
                    vmodel,
                    valuejs,
                    change,
                )
            )
        else:
            if value is None:
                value = "null"
            else:
                value = "'{}'".format(value)
            html += (
                ' on-select="selectedOptionSelect({}.{},{},{}, '
                '$parent, $select.selected)"'.format(
                    vform,
                    vmodel,
                    value,
                    change,
                )
            )
        html += ' theme="bootstrap"'
        html += ' ng-disabled="disabled"'
        html += ' reset-search-input="false"'
        html += ">"
        html += ' <ui-select-match placeholder="{}">'.format(placeholder)
        if is_multiple:
            html += "    {{$item.label}}"
        else:
            html += "    {{$select.selected.label}}"
        html += " </ui-select-match>"
        html += " <ui-select-choices"
        html += '     style="{}"'.format(vstyle)
        html += '     repeat="value.id as value in options.{}'.format(vmodel)
        html += '            | filter: {label: $select.search}">'
        html += (
            '     <div ng-bind-html="value.label| highlightSelect: '
            '$select.search"></div>'
        )
        html += " </ui-select-choices>"
        html += "</ui-select>"
        # Return result
        return html


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
            self.autofill_deepness = targs.get("autofill_deepness", 3)
            self.autofill_url = targs.get("autofill_url", "")
            self.autofill = targs.get("autofill_related", [])

        return super().__init__(*args, **kwargs)

    def set_language(self, language):
        self.language = language

    def get_foreign(self, vurl, vform, vmodel, search, function):
        html = "{0}(http,'{1}',options,{{".format(function, vurl)
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
        html += "}}, '{0}', {1}, {2}, {3});\"".format(
            vmodel,
            vmodel,
            search,
            self.autofill_deepness,
        )
        return html


class DynamicSelect(DynamicSelectInputWidget, forms.widgets.Select):
    def render(self, name, value, attrs=None, choices=(), renderer=None):
        if not self.autofill_url:
            raise OSError("autofill_url not defined")
        # Initialization
        controller = self.attrs.get("ng-controller", None)
        disabled = self.attrs.get("ng-disabled", None)
        required = self.attrs.get("ng-required", "false")
        change = (
            self.attrs.get("ng-change", "undefined")
            .replace('"', "'")
            .replace("'", "\\'")
        )
        if change != "undefined":
            change = "'{}'".format(change)
        vmodel = self.field_name
        vid = attrs.get("id", "id_{}".format(name))
        vstyle = attrs.get("style", "")
        vform = smart_str(self.form_name)
        vurl = reverse(self.autofill_url, kwargs={"search": "a"})[:-1]
        # Get access to the get_label() method and request for the label of
        # the bound input
        if value:
            func = resolve(vurl + "*").func
            clss = get_class(func)
            if self.language:
                clss.language = self.language
            label = clss().get_label(value)

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
            "<input name='{0}' ng-required='{1}' "
            "ng-model='{0}' id='{0}' type='hidden'".format(vmodel, required)
        )
        if controller:
            html += " ng-controller='{}' ".format(controller)
        if disabled:
            html += " ng-disabled='{}' ".format(disabled)
        # Set initial value
        if value:
            html += " ng-init=\"{}='{}'\"".format(vmodel, value)
        html += ">"
        html += "<ui-select"
        if controller:
            html += " ng-controller='{}' ".format(controller)
        if disabled:
            html += " ng-disabled='{}' ".format(disabled)
        if hasattr(self, "multiple") and self.multiple:
            html += " multiple "
        if value:
            html += (
                " ng-init=\"options.{0}=[{{'id':null,'label':{3}}},"
                "{{'id':'{1}','label':'{2}'}}]; "
                "$select.selected=options.{0}[1];".format(
                    vmodel,
                    value,
                    escapejs(label),
                    ngplaceholder,
                )
            )
            html += (
                " option_default={}; options.{}=option_default['rows']".format(
                    self.get_foreign(
                        vurl,
                        vform,
                        vmodel,
                        "'*'",
                        "getForeignKeys",
                    ),
                    vmodel,
                )
            )
        else:
            # init options for form modal
            html += (
                " ng-init=\"options.{0}=[{{'id':null,"
                "'label':{1}}}]; \"".format(vmodel, ngplaceholder)
            )
        html += (
            ' ng-click="option_default={}; '
            "options.{}=option_default['rows']".format(
                self.get_foreign(vurl, vform, vmodel, "'*'", "getForeignKeys"),
                vmodel,
            )
        )

        html += ' id="{}"'.format(vid)
        html += ' ng-model="{}.{}"'.format(vparent, vmodel)
        html += (
            " on-select=\"selectedOptionSelect({}.{},'{}',{}, "
            '$parent, $select.selected)"'.format(vform, vmodel, value, change)
        )
        html += ' theme="bootstrap"'
        html += ' ng-disabled="disabled"'
        html += ' reset-search-input="false"'
        html += ">"
        html += " <ui-select-match placeholder='{}'>".format(placeholder)
        html += ' <div ng-bind-html="$select.selected.label"></div>'
        html += " </ui-select-match>"
        html += " <ui-select-choices"
        html += '     style="{}"'.format(vstyle)
        html += '     repeat="value.id as value in options.{}"'.format(vmodel)
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
        html += (
            '     <div ng-bind-html="value.label| highlightSelect: '
            '$select.search"></div>'
        )
        html += " </ui-select-choices>"
        html += "</ui-select>"
        return html


class MultiStaticSelect(StaticSelectMulti):
    static = True


class MultiDynamicSelect(StaticSelectMulti):
    static = False


class MultiStaticSelect_old(StaticSelect):  # noqa: N801
    multiple = True


class MultiDynamicSelect_old(DynamicSelect):  # noqa: N801
    multiple = True


class DynamicInput(DynamicSelectInputWidget, forms.widgets.Input):
    def render(self, name, value, attrs=None, choices=(), renderer=None):
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
        ticket += (
            ' typeahead-on-select="autoFillFields($item, $model, '
            '$label, $event)"'
        )
        ticket += ' typeahead-wait-ms="800"'
        ticket += ' ng-change="resetAutoComplete()"'

        # Save ticket inside html
        html = html.replace('type="None"', 'type="text"')
        html = html.replace("/>", "{}/>".format(ticket))

        # Return updated html
        return html


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
            path_image = "{}/{}".format(settings.MEDIA_ROOT, value)
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
                        '<img src="{}{}" style="max-height:75px; '
                        'max-width:150px;" />'.format(
                            settings.MEDIA_URL,
                            value,
                        )
                    )
                    link = '<a href="{}{}" target="_blank">{}</a>'.format(
                        settings.MEDIA_URL,
                        value,
                        image,
                    )

                    html = '<div class="row">'
                    html += '   <div class="col-md-6">{}</div>'.format(button)
                    html += '   <div class="col-md-6">{}</div>'.format(link)
                    html += "</div>"
                else:
                    link = (
                        '<br /><a href="{}{}" '
                        'target="_blank">{}</a><br />'.format(
                            settings.MEDIA_URL,
                            value,
                            value,
                        )
                    )
                    html = link + button
        else:
            button = super().render(
                name,
                value,
                attrs=attrs,
            )
            html = button

        return html

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
            f.name = "{}.{}".format(hexname, ext)
            f.original_name = field["filename"]
            f.write(base64.b64decode(field["base64"]))
            f.seek(0)

            # Add the files to FILES
            files[name] = File(f)

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
    def render(self, name, value, attrs=None, renderer=None):
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

        try:
            list_type = [
                str,
                unicode,
            ]
        except NameError:
            list_type = [
                str,
            ]

        if value and value != "":
            if isinstance(value, datetime):
                value_date = value.date()
                value_time = "{:02d}{:02d}".format(
                    value.time().hour,
                    value.time().minute,
                )
            elif type(value) in list_type:
                # 2015-06-03 00:00 or 2015-06-03 00:00:00
                try:
                    """
                    ###########################################################################
                    # WARNING: I suspect this is a bad patch because it doesn't detect the    #
                    #          format of the data depending on the Django's localization      #
                    #          system. It should checked how is being used in                 #
                    #          method value_from_datadict() from this same class              #
                    ###########################################################################
                    """  # noqa: E501
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
                    value_time = "{:02d}{:02d}".format(
                        aux.time().hour,
                        aux.time().minute,
                    )

        startview = 2
        minview = 2
        maxview = 4
        icon = "calendar"

        """
        ##############################################################################
        # WARNING: Language code should be detected on runtime from the user request #
        ##############################################################################
        """  # noqa: E501
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
        html += '    <div id="date_{}" class="input-group date">'.format(name)

        tmp = []
        for x in attrs:
            y = attrs[x]
            tmp.append(x + '="' + y + '"')
        attributes = " ".join(tmp)

        html += (
            '        <input type="text" name="{0}" id="id_{0}" '
            'value="{1}" {2} />'.format(name, value_date, attributes)
        )
        html += (
            '        <span class="input-group-addon">'
            '<i class="glyphicon glyphicon-{}"></i></span>'.format(icon)
        )
        html += "    </div>"
        html += " </div>"
        html += "</div>"
        html += '<div class="col-sm-4">'

        ngmodel = attrs["ng-model"].split("']")
        if len(ngmodel) > 1:
            ngmodel[0] = "{}_time".format(ngmodel[0])
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
            '        <input type="text" name="{0}_time" id="id_{0}_time" '
            'value="{1}" maxlength="4" {2} />'.format(
                name,
                value_time,
                attributes,
            )
        )
        html += "</div>"
        html += "</div>"
        html += '<script type="text/javascript"> '
        html += '$("#date_{}").datetimepicker({}'.format(name, "{")
        html += ' format: "{}",'.format(format_date)
        html += " autoclose: true,"
        html += ' language:"{}",'.format(language)
        html += " todayBtn: true,"
        html += " weekStart:1,"
        html += " todayHighlight:true,"
        html += ' pickerPosition:"bottom-left",'
        html += " keyboardNavigation:false,"
        html += " startView:{},".format(startview)
        html += " minView:{},".format(minview)
        html += " maxView:{},".format(maxview)
        html += " minuteStep: 15,"
        html += "});"
        html += "</script>"
        return html

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
                        ttime = "00:{}".format(ttime)
                    elif len(ttime) == 3:
                        ttime = "0{}:{}".format(ttime[:1], ttime[1:])
                    else:
                        ttime = "{}:{}".format(ttime[:2], ttime[2:])

            try:
                new_date = datetime.strptime(
                    "{} {}".format(date, ttime),
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

        data[name] = new_date
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
        # Recompute ngmodel
        if re.fullmatch(r"\w+", ngmodel):
            ngmodel = "$parent.{}".format(ngmodel)
        # Compute hashkey
        hashkey = attrs.get("id", str(random.randint(0, 1000)))
        # Editors
        editors = {}
        editors["textangular"] = _("Text Angular")
        editors["quill"] = _("NG Quill")
        editors["raw"] = _("Source code")
        editors["preview"] = _("Preview")
        editors_list = []
        for keyarg in editors.keys():
            editors_list.append(
                '"{0}":{{"key":"{0}","name":"{1}"}}'.format(
                    keyarg,
                    smart_str(editors[keyarg]),
                ),
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
                    attributes.append('{}="{}"'.format(key, attrs[key]))
                    if key in ["ng-blur", "ng-change"]:
                        attributes_ngquill.append(
                            'on-content-changed="{}"'.format(attrs[key]),
                        )
                    attributes_ngquill.append(
                        '{}="{}"'.format(key, attrs[key]),
                    )
        attributes = " ".join(attributes)
        attributes_ngquill = " ".join(attributes_ngquill)
        # Get normal field
        html = ""
        html += "<div ng-init='editors_{1}={0}'></div>".format(
            editors_json,
            hashkey,
        )
        # Render wysiwyg editor's selector
        if force_editors:
            ngshow = ""
        else:
            ngshow = " ng-show='block.type==\"string\"'>"
        html += "<select ng-model='editor_{1}'{0}>".format(ngshow, hashkey)
        html += (
            '<option ng-repeat="subeditor in editors_{0}" '
            'value="{{{{subeditor.key}}}}">{{{{subeditor.name}}}}'
            "</option>".format(hashkey)
        )
        html += "</select>"

        # Render wysiwyg editors
        html += (
            '<div ng-if=\'{1}editor_{2}=="preview"\' class="form-control" '
            'ng-bind-html="{0}"></div>'.format(ngmodel, extraif, hashkey)
        )
        html += (
            '<textarea ng-model="{0}" '
            'ng-if=\'{1}editor_{4}=="raw"\' class="form-control" '
            'rows="10"{2} {3}></textarea>'.format(
                ngmodel,
                extraif,
                required,
                attributes,
                hashkey,
            )
        )
        html += (
            '<ng-quill-editor ng-model="{0}" '
            "ng-if='{1}editor_{4}==\"quill\"'{2} {3}>"
            "</ng-quill-editor>".format(
                ngmodel,
                extraif,
                required,
                attributes_ngquill,
                hashkey,
            )
        )
        html += (
            '<text-angular ng-model="{0}" '
            "ng-if='{1}editor_{4}==\"textangular\"'{2} {3}>"
            "</text-angular>".format(
                ngmodel,
                extraif,
                required,
                attributes,
                hashkey,
            )
        )
        html += (
            '<textarea ng-model="{}" '
            "ng-if='{}editor' style='background-color:#fdd'{} {}>"
            "</textarea>".format(ngmodel, extraif, required, attributes)
        )

        return html


class WysiwygAngularInput(WysiwygAngularRender):
    def render(self, name, value, attrs=None, renderer=None):
        # Compute hashkey
        hashkey = attrs.get("id", str(random.randint(0, 1000)))
        # Get model name
        vmodel = attrs.get("ng-model")  # .replace("'",'"')
        init = attrs.get("ng-init", "")

        if value is None:
            value = ""
        # Render
        html = "<div ng-init='editor_{}=\"textangular\"'>".format(hashkey)
        html += (
            '<textarea name="{0}" ng-model="{1}" ng-show=\'false\' '
            'ng-init="{3}">{2}</textarea>'.format(name, vmodel, value, init)
        )
        html += self.render_wysiwyg(
            ngmodel=vmodel,
            force_editors=True,
            attrs=attrs,
            renderer=renderer,
        )
        html += "</div>"

        # Return result
        return html


class MultiBlockWysiwygInput(WysiwygAngularRender):
    def render(self, name, value, attrs=None, renderer=None):
        # Compute hashkey
        hashkey = attrs.get("id", str(random.randint(0, 1000)))

        # Cleaned value
        if value:
            value_clean = value.replace("'", "&#39;")
        else:
            value_clean = value

        # Get model name
        vmodel = attrs.get("ng-model").replace("'", '"')
        # Get normal field
        html = (
            "<div ng-init='{0}={{}}; {0}[\"__JSON_DATA__\"]={1}'>"
            "</div>".format(vmodel, value_clean)
        )
        html += "<input type='hidden' name='{}' ng-model='{}'>".format(
            name,
            vmodel,
        )

        # Render blocks with ANGULAR
        html += (
            "<div ng-repeat='(key, block) in "
            '{}["__JSON_DATA__"]\' ng-init=\'editor_{}="quill"\'>'.format(
                vmodel,
                hashkey,
            )
        )
        html += "<label>{{key}}</label>"

        html += (
            '<div ng-show="block.deleted"><p class="text-danger">{}</p>'
            "</div>".format(_("Field deleted in the template"))
        )
        html += self.render_wysiwyg(
            ngmodel="block.value",
            extraif='block.type=="string" && ',
            attrs=attrs,
            renderer=renderer,
        )
        html += "</div>"

        # Return result
        return html


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
        hashkey = attrs.get("id", str(random.randint(0, 1000)))
        vmodel = attrs.get("ng-model").replace("'", '"')
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
                        value = value.replace("<#{}#>".format(key), newname)
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
        return html


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
        if not fieldname:
            fieldname = "g-recaptcha-response"
        self.recaptcha_response_name = fieldname
        self.recaptcha_challenge_name = fieldname

        # Keep going as usually
        return super().__init__(*args, **kwargs)

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
        if self.legacy:
            html = super().render(name, value, attrs)
        else:
            html = (
                '<input ng-model="{0}" name="{0}" id="id_{0}" '
                'type="hidden" ng-required="true">'.format(name)
            )
            html += (
                '<div vc-recaptcha key="\'{}\'" ng-model="{}"></div>'.format(
                    self.public_key,
                    name,
                )
            )
        return html
