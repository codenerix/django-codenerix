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

import datetime

from django import template
from django.conf import settings
from django.utils import formats
from django.utils.translation import get_language
from django.utils.translation import gettext as _

from codenerix.helpers import monthname, nameunify, zeropad

register = template.Library()
register.filter("digitos", zeropad)
register.filter("monthname", monthname)
register.filter("nameunify", nameunify)


@register.filter
def debugme(obj, kind=None):
    if kind == "dict":
        obj = obj.__dict__
    elif kind == "keys":
        obj = obj.__dict__.keys()

    raise OSError(obj)


@register.filter
def debugmedict(obj):
    raise OSError(obj.__dict__)


@register.filter
def addedit(value):
    return (value == "add") or (value == "edit")


@register.filter
def invert(listt):
    newlist = []
    for element in listt:
        newlist.insert(0, element)
    return newlist


@register.filter
def differ(value1, value2):
    return abs(value1 - value2)


@register.filter
def ghtml(value):
    if value:
        splitted = value.replace("\r", "").split("\n")
        result = ""
        for row in splitted:
            oldlen = 0
            while oldlen != len(row):
                oldlen = len(row)
                row = row.replace("  ", "&nbsp;&nbsp;")
            if len(row) > 0 and row[0] == "#":
                result += "<b>%s</b>" % (row[1:])
            else:
                result += "%s" % (row)
            result += "<br>"
    else:
        result = value
    return result


@register.filter
def smallerthan(value1, value2):
    return value1 < value2


@register.filter
def br(value):
    splitted = value.split("\n")
    header = splitted[0]
    body = "<br>".join(splitted[1:])
    return (
        f"<div style='color:#5588BB'>{header}/div>"
        f"<div style='color:#22BB00; margin-top:5px;'>{body}</div>"
    )


@register.filter
def nicenull(value):
    if value:
        return value
    else:
        return "-"


@register.filter
def nicekilometers(value):
    if value:
        return f"{value}km"
    else:
        return "-"


@register.filter
def niceeuronull(value):
    if value:
        return f"{value}\u20AC"
    else:
        return "-"


@register.filter
def nicepercentnull(value):
    if value:
        return "%s%%" % (value)
    else:
        return "-"


@register.filter
def nicebool(value):
    if value:
        return _("Yes")
    else:
        return _("No")


@register.filter
def ynbool(value):
    if value:
        return "yes"
    else:
        return "no"


@register.filter
def toint(value):
    try:
        newvalue = int(value)
    except Exception:
        newvalue = None
    return newvalue


@register.filter
def notval(value):
    return not value


@register.filter
def count(values):
    return values.count()


@register.filter
def countpages(values):
    return values.count() - 1


@register.filter
def freedombool(value1, value2):
    if value1 >= value2:
        return "yes"
    else:
        return "no"


@register.filter
def pair(value):
    if value % 2:
        return False
    else:
        return True


@register.filter(name="len")
def lenlist(list):
    return len(list)


@register.filter
def nbsp(value):
    return value.replace(" ", "&nbsp;")


@register.filter
def mod(value, arg):
    if value % arg == 0:
        return 1
    else:
        return


@register.filter
def keyvalue(dic, key):
    return dic[key]


@register.filter
def acumulate(element, li):
    if li:
        number = li[-1]["id"] + 1
    else:
        number = 1
    li.append({"id": number, "value": element})
    return number


@register.filter
def getforms(forms, form):
    if forms:
        return forms
    else:
        return [form]


@register.filter
def langforms(forms, language):
    for form in forms:
        form.set_language(language)
    return forms


@register.filter
def objectatrib(instance, atrib):
    """
    this filter is going to be useful to execute an object method or get an
    object attribute dynamically. this method is going to take into account
    the atrib param can contains underscores
    """

    if instance != "":
        atrib = atrib.replace("__", ".")
        atribs = []
        atribs = atrib.split(".")

        obj = instance
        for atrib in atribs:
            if isinstance(obj, dict):
                result = obj[atrib]
            else:
                try:
                    result = getattr(obj, atrib)()
                except Exception:
                    result = getattr(obj, atrib)

            obj = result
    else:
        result = None
    return result


@register.filter
def TrueFalse(value):  # noqa: N802
    if isinstance(value, bool):
        if value:
            return _("True")
        else:
            return _("False")
    return value


@register.filter
def cdnx_beauty(value, kind=None):
    if kind:
        if kind == "skype":
            return (
                "<a ng-click='$event.stopPropagation();' "
                f"href='tel:{value}'>{value}</a>"
            )
        elif kind == "image":
            return (
                "<img ng-click='$event.stopPropagation();' "
                f"src='{settings.MEDIA_URL}{value}'>"
            )
        elif kind == "nofilter":
            return value
        else:
            raise Exception(
                "Django filter 'codenerix' got a wrong kind named '"
                + kind
                + "'",
            )
    else:
        if value is None:
            return nicenull(value)
        elif isinstance(value, bool):
            return TrueFalse(value)
        elif isinstance(value, datetime.datetime):
            fmt = formats.get_format(
                "DATETIME_INPUT_FORMATS",
                lang=get_language(),
            )[0]
            value = datetime.datetime.strftime(value, fmt)
        elif isinstance(value, datetime.time):
            fmt = formats.get_format(
                "TIME_INPUT_FORMATS",
                lang=get_language(),
            )[0]
            value = datetime.time.strftime(value, fmt)
        elif isinstance(value, float):
            if float(int(value)) == value:
                value = int(value)

    return value


@register.filter
def cdnx_angular(value):
    """
    Convert each value to its analog version in Angular
    """
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return str(value).lower()
    elif isinstance(value, str):
        return '"' + value + '"'
    else:
        return value


@register.filter
def multiplication(value, arg):
    return float(value) * float(arg)


@register.filter
def division(value, arg):
    if arg != 0:
        return float(value) / float(arg)
    else:
        return None


@register.filter
def addition(value, arg):
    return float(value) + float(arg)


@register.filter
def subtraction(value, arg):
    return float(value) - float(arg)


@register.filter
def autofocus(f):
    if f.get("focus", False):
        return "autofocus"
    else:
        return ""


@register.filter
def replace(value, fromto):
    (f, t) = fromto.split("·")
    return str(value).replace(f, t)


@register.filter
def set_ngmodel(inp, name):
    inp.field.widget.field_name = name
    return inp
