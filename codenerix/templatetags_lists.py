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

from django.core.urlresolvers import reverse
from django.utils.encoding import smart_text
from django.utils.safestring import mark_safe
from django.core.exceptions import ValidationError
from django.utils import formats
from djng.forms.angular_base import TupleErrorList

from codenerix.helpers import model_inspect


def widgetize(i):
    # Initialize structure
    attrs = i.__dict__.get("field", {}).__dict__.get("widget", {}).__dict__.get('attrs', {})
    
    # Select
    # if 'choices' in i.field.widget.__dict__:
    #
    #    # Set classes for select2 inputs to look properly with and without foreignkeys link button
    #    if foreignkey(i,""):
    #        addattr(attrs,"class=select_fk")
    #    else:
    #        addattr(attrs,"class=select_nofk")
    #    # Add a new attribute for ui-select to work
    #    addattr(attrs,"ui-select2")

    # Return result
    return attrs


def istype(i, kind):
    # Get widget
    widget = i.field.widget

    # Get format type
    if ('format_key' in type(widget).__dict__):
        ftype = type(widget).format_key
    else:
        ftype = None

    # Choose kind
    if kind == 'datetime':
        if   ftype == 'DATETIME_INPUT_FORMATS':   answer = 'DATETIME_INPUT_FORMATS'
        elif ftype == 'DATE_INPUT_FORMATS':       answer = 'DATE_INPUT_FORMATS'
        elif ftype == 'TIME_INPUT_FORMATS':       answer = 'TIME_INPUT_FORMAT'
        else:                                     answer = False
    elif kind == 'date2time':
        answer = 'DATE_INPUT_FORMATS'
    elif kind == 'color':
        answer = (ngmodel(i) == 'color')
    else:
        IOError("Unknown type '{0}' in 'istype' filter".format(kind))

    # Return answer
    return answer


def addextra(attrs, attr):
    if attr:
        for at in attr:
            addattr(attrs, at)
    # Return result
    return attrs


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
                attrs[key] += " {0}".format(value)
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


def lockattr(attrs, cannot_update):
    if cannot_update:
        if "ui-select2" in attrs:
            attrs.pop("ui-select2")
        newattrs = addattr(attrs, "readonly='readonly'")
        return addattr(newattrs, "disabled='disabled'")
    else:
        return attrs


def setattrs(field, attrs):
    if attrs:
        return field.as_widget(attrs=attrs)
    else:
        return field


def ngmodel(i):
    return getattr(i.field.widget, 'field_name', i.field.widget.attrs['ng-model'])


def inireadonly(attrs, i):
    field = ngmodel(i)
    return addattr(attrs, 'ng-readonly=readonly_{0}'.format(field))


def date2timewidget(i, langcode):
    return datewidget(i, langcode, 'date2time')


def datewidget(i, langcode, kindtype='datetime'):
    # Initialization
    final = {}
    form = formats.get_format('DATETIME_INPUT_FORMATS', lang=langcode)[0].replace("%", "").replace('d', 'dd').replace('m', 'mm').replace('Y', 'yyyy').replace('H', 'hh').replace('M', 'ii').replace('S', 'ss')

    kind = istype(i, kindtype)
    if kind == 'DATETIME_INPUT_FORMATS':
        final['format'] = form
        final['startview'] = 2
        final['minview'] = 0
        final['maxview'] = 4
        final['icon'] = 'calendar'

    elif (kind == 'DATE_INPUT_FORMATS') or (kind == 'date'):
        final['format'] = form.split(" ")[0]
        final['startview'] = 2
        final['minview'] = 2
        final['maxview'] = 4
        final['icon'] = 'calendar'

    elif kind == 'TIME_INPUT_FORMAT':
        final['format'] = form.split(" ")[1]
        final['startview'] = 1
        final['minview'] = 0
        final['maxview'] = 1
        final['icon'] = 'time'

    else:
        raise IOError("Unknown kind '{0}' in filter 'datewidget'".format(kind))

    # Return result
    return final


def unlist(elements):
    # Remake the tuple
    newtuple = TupleErrorList()
    # Process each errror
    for error in elements:
        # Split errors
        (f1, f2, f3, f4, f5, msg) = error
        if type(msg) == ValidationError:
            newmsg = ""
            for error in msg:
                if newmsg:
                    newmsg += " {0}".format(error)
                else:
                    newmsg = error
            # Save new msg
            msg = newmsg
        # Save error with converted text
        newtuple.append((f1, f2, f3, f4, f5, msg))
    # Return the newtuple
    return newtuple


def foreignkey(element, exceptions):
    '''
    function to determine if each select field needs a create button or not
    '''
    label = element.field.__dict__['label']
    try:
        label = unicode(label)
    except NameError:
        pass
    if (not label) or (label in exceptions):
        return False
    else:
        return "_queryset" in element.field.__dict__


def headstyle(group):
    # Initialize
    style = ""
    
    # Decide about colors
    if 'color' in group and group['color']:
        style += "color:{0};".format(group['color'])
    if 'bgcolor' in group and group['bgcolor']:
        style += "background-color:{0};".format(group['bgcolor'])
    if 'textalign' in group and group['textalign']:
        style += "text-align:{0};".format(group['textalign'])
    
    # Check if we have some style
    if style:
        return "style={0}".format(style)
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
            raise IOError("Columns max number of 12 reached, you requested to use a total of '{}'".format(self.__columns))
        else:
            answer = False
        # Add new columns
        self.__columns += columns
        # Return answer
        return answer


def column_counter(nothing):
    return ColumnCounter()


def add_columns(obj, columns):
    return obj.add(columns)


def linkedinfo(element):
    info = model_inspect(element.field._get_queryset().model())
    ngmodel = element.html_name  # field.widget.attrs['ng-model']
    return mark_safe("'{0}','{1}','{2}s'".format(ngmodel, info['appname'], info['modelname'].lower()))


# DEPRECATED: 2017-02-14
def get_depa(queryset, kind):
    return queryset.get(kind=kind, alternative=False)


def getws(form, input_name):
    if 'autofill' in form.Meta.__dict__ and input_name in form.Meta.autofill:
        return "'{}'".format(reverse(form.Meta.autofill[input_name][2], kwargs={'search': '__pk__'}))
    else:
        return 'undefined'


def get_field_list(forms):
    inputs = []
    for form in forms:
        for field in form.fields:
            inputs.append("'{}'".format(field))
    if inputs:
        inputs = "[{}]".format(','.join(inputs))
    return inputs


def invalidator(formname, inp):
    return mark_safe("{{'codenerix_invalid':{0}.{1}.$invalid}}".format(smart_text(formname), ngmodel(inp)))


def join_list(l, string):
    if l:
        return string.join(l)
    else:
        return ''
