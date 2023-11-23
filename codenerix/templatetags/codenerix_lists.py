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

from django.conf import settings
from django.core.exceptions import ValidationError
from django.template import Library
from django.urls import reverse
from django.utils import formats
from django.utils.encoding import smart_str
from django.utils.safestring import mark_safe

from codenerix.djng.angular_base import TupleErrorList
from codenerix.helpers import model_inspect

register = Library()


@register.filter
def widgetize(i):
    # Initialize structure
    attrs = (
        i.__dict__.get("field", {})
        .__dict__.get("widget", {})
        .__dict__.get("attrs", {})
    )

    # Select
    # if 'choices' in i.field.widget.__dict__:
    #
    #    # Set classes for select2 inputs to look properly with and
    #    # without foreignkeys link button
    #    if foreignkey(i,""):
    #        addattr(attrs,"class=select_fk")
    #    else:
    #        addattr(attrs,"class=select_nofk")
    #    # Add a new attribute for ui-select to work
    #    addattr(attrs,"ui-select2")

    # Return result
    return attrs


@register.filter
def istype(i, kind):
    # Get widget
    widget = i.field.widget

    # Get format type
    if "format_key" in type(widget).__dict__:
        ftype = type(widget).format_key
    else:
        ftype = None

    # Choose kind
    if kind == "datetime":
        if ftype == "DATETIME_INPUT_FORMATS":
            answer = "DATETIME_INPUT_FORMATS"
        elif ftype == "DATE_INPUT_FORMATS":
            answer = "DATE_INPUT_FORMATS"
        elif ftype == "TIME_INPUT_FORMATS":
            answer = "TIME_INPUT_FORMAT"
        else:
            answer = False
    elif kind == "date2time":
        answer = "DATE_INPUT_FORMATS"
    elif kind == "color":
        answer = ngmodel(i) == "color"
    else:
        raise OSError(f"Unknown type '{kind}' in 'istype' filter")

    # Return answer
    return answer


@register.filter
def addextra(attrs, attr):
    if attr:
        for at in attr:
            addattr(attrs, at)
    # Return result
    return attrs


@register.filter
def addattr(attrs, attr):
    # Split the new attr into key/value pair
    attrsp = attr.split("=")
    key = attrsp[0]
    if len(attrsp) >= 2:
        value = "=".join(attrsp[1:])
    else:
        value = ""

    if key in attrs:
        # Key already exists in the attrs struct
        if attrs[key]:
            # Key has a value already inside the structure
            if value:
                # We got a new value to add to the struct, append it
                attrs[key] += f" {value}"
        else:
            # Key doesn't have a value inside the structure
            if value:
                # We got a new value to add eo the struct, add it
                attrs[key] += value
    else:
        # Add the new key
        attrs[key] = value

    # Return result
    return attrs


@register.filter
def lockattr(attrs, cannot_update):
    if cannot_update:
        if "ui-select2" in attrs:
            attrs.pop("ui-select2")
        newattrs = addattr(attrs, "readonly='readonly'")
        return addattr(newattrs, "disabled='disabled'")
    else:
        return attrs


@register.filter
def setattrs(field, attrs):
    if attrs:
        return field.as_widget(attrs=attrs)
    else:
        return field


@register.filter
def ngmodel(i):
    return getattr(
        i.field.widget,
        "field_name",
        i.field.widget.attrs["ng-model"],
    )


@register.filter
def inireadonly(attrs, i):
    field = ngmodel(i)
    return addattr(attrs, f"ng-readonly=readonly_{field}")


@register.filter
def date2timewidget(i, langcode):
    return datewidget(i, langcode, "date2time")


@register.filter
def datewidget(i, langcode, kindtype="datetime", kind=None):
    # Initialization
    final = {}
    form = (
        formats.get_format("DATETIME_INPUT_FORMATS", lang=langcode)[0]
        .replace("%", "")
        .replace("d", "dd")
        .replace("m", "mm")
        .replace("Y", "yyyy")
        .replace("H", "hh")
        .replace("M", "ii")
        .replace("S", "ss")
    )

    if kind is None:
        kind = istype(i, kindtype)

    if kind == "DATETIME_INPUT_FORMATS":
        final["format"] = form
        final["startview"] = 2
        final["minview"] = 0
        final["maxview"] = 4
        final["icon"] = "calendar"

    elif (kind == "DATE_INPUT_FORMATS") or (kind == "date"):
        final["format"] = form.split(" ")[0]
        final["startview"] = 2
        final["minview"] = 2
        final["maxview"] = 4
        final["icon"] = "calendar"

    elif kind == "TIME_INPUT_FORMAT":
        final["format"] = form.split(" ")[1]
        final["startview"] = 1
        final["minview"] = 0
        final["maxview"] = 1
        final["icon"] = "time"

    else:
        raise OSError(f"Unknown kind '{kind}' in filter 'datewidget'")

    # Return result
    return final


@register.filter
def unlist(elements):
    # Remake the tuple
    newtuple = TupleErrorList()
    # Process each errror
    for error in elements:
        # Split errors
        (f1, f2, f3, f4, f5, msg) = error
        if isinstance(msg, ValidationError):
            newmsg = ""
            for error in msg:
                if newmsg:
                    newmsg += f" {error}"
                else:
                    newmsg = error
            # Save new msg
            msg = newmsg
        # Save error with converted text
        newtuple.append((f1, f2, f3, f4, f5, msg))
    # Return the newtuple
    return newtuple


@register.filter
def foreignkey(element, exceptions):
    """
    function to determine if each select field needs a create button or not
    """
    label = element.field.__dict__["label"]
    try:
        label = unicode(label)
    except NameError:
        pass
    if (not label) or (label in exceptions):
        return False
    else:
        return "_queryset" in element.field.__dict__


@register.filter
def headstyle(group):
    # Initialize
    style = ""

    # Decide about colors
    if "color" in group and group["color"]:
        style += f"color:{group['color']};"
    if "bgcolor" in group and group["bgcolor"]:
        style += f"background-color:{group['bgcolor']};"
    if "textalign" in group and group["textalign"]:
        style += f"text-align:{group['textalign']};"

    # Check if we have some style
    if style:
        return f"style={style}"
    else:
        return ""


class ColumnCounter:
    def __init__(self):
        self.__columns = 0

    def add(self, columns):
        # Control columns
        if self.__columns == 12:
            self.__columns = 0
            answer = True
        elif self.__columns > 12:
            raise OSError(
                "Columns max number of 12 reached, you requested to use a "
                f"total of '{self.__columns}'",
            )
        else:
            answer = False
        # Add new columns
        self.__columns += columns
        # Return answer
        return answer


@register.filter
def column_counter(nothing):
    return ColumnCounter()


@register.filter
def add_columns(obj, columns):
    return obj.add(columns)


@register.filter
def linkedinfo(element, info_input={}):
    info = model_inspect(element.field._get_queryset().model())
    info.update(info_input)

    ngmodel = element.html_name  # field.widget.attrs['ng-model']
    baseurl = getattr(settings, "BASE_URL", "")
    return mark_safe(
        f"'{baseurl}','{ngmodel}','{info['appname']}', "
        f"'{info['modelname'].lower()}s'",
    )


# DEPRECATED: 2017-02-14
@register.filter
def get_depa(queryset, kind):
    return queryset.get(kind=kind, alternative=False)


@register.filter
def getws(form, input_name):
    if "autofill" in form.Meta.__dict__ and input_name in form.Meta.autofill:
        ref = reverse(
            form.Meta.autofill[input_name][2],
            kwargs={"search": "__pk__"},
        )

        return f"'{ref}'"
    else:
        return "undefined"


@register.filter
def get_field_list(forms):
    inputs = []
    for form in forms:
        for field in form.fields:
            inputs.append(f"'{field}'")
    if inputs:
        inps = ",".join(inputs)
        inputs = f"[{inps}]"
    return inputs


@register.filter
def invalidator(formname, inp):
    return mark_safe(
        "{'codenerix_invalid':"
        f"{smart_str(formname)}.{ngmodel(inp)}.$invalid}}",
    )


@register.filter
def join_list(lst, string):
    if lst:
        return string.join(lst)
    else:
        return ""
