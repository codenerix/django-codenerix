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

from django.utils.translation import ugettext as _
from django.conf import settings

def debugme(obj):
        raise IOError(obj)

def debugmedict(obj):
        raise IOError(obj.__dict__)

def addedit(value):
    return (value=='add') or (value=='edit')

def invert(listt):
    newlist=[]
    for element in listt:
        newlist.insert(0,element)
    return newlist

def differ(value1,value2):
    return abs(value1-value2)


def ghtml(value):
    if value:
        splitted=value.replace("\r","").split("\n")
        result=''
        for row in splitted:
            oldlen=0
            while oldlen!=len(row):
                oldlen=len(row)
                row=row.replace('  ','&nbsp;&nbsp;')
            if len(row)>0 and row[0]=='#':
                result+="<b>%s</b>" % (row[1:])
            else:
                result+="%s" % (row)
            result+='<br>'
    else:
        result=value
    return result

def smallerthan(value1,value2):
    return value1<value2

def br(value):
    splitted=value.split("\n")
    header=splitted[0]
    body='<br>'.join(splitted[1:])
    return "<div style='color:#5588BB'>%s</div><div style='color:#22BB00; margin-top:5px;'>%s</div>" % (header,body)

def nicenull(value):
    if value:
        return value
    else:
        return "-"

def nicekilometers(value):
    if value:
        return "{0}km".format(value)
    else:
        return "-"

def niceeuronull(value):
    if value:
        return u"{0}\u20AC".format(value)
    else:
        return "-"

def nicepercentnull(value):
    if value:
        return "%s%%" % (value)
    else:
        return "-"

def nicebool(value):
    if value:
        return _("Yes")
    else:
        return _("No")

def ynbool(value):
    if value:
        return "yes"
    else:
        return "no"

def toint(value):
    try:
        newvalue=int(value)
    except:
        newvalue=None
    return newvalue

def notval(value):
    return not value

def count(values):
    return values.count()

def countpages(values):
    return (values.count()-1)

def freedombool(value1,value2):
    if value1>=value2:
        return "yes"
    else:
        return "no"

def pair(value):
    if value % 2:
        return False
    else:
        return True

def lenlist(list):
    return len(list)

def nbsp(value):
    return value.replace(' ','&nbsp;')


def mod(value, arg):
    if (value%arg==0):
        return 1
    else:
        return 

def keyvalue(dic, key):
        return dic[key]

def acumulate(element,l):
    if l:
        number=l[-1]['id']+1
    else:
        number=1
    l.append({'id':number,'value':element})
    return number

def getforms(forms,form):
    if forms:
        return forms
    else:
        return [form]

def langforms(forms, language):
    for form in forms:
        form.set_language(language)
    return forms

def objectatrib(instance, atrib):
    '''
    this filter is going to be useful to execute an object method or get an 
    object attribute dynamically. this method is going to take into account
    the atrib param can contains underscores
    '''
    atrib = atrib.replace("__", ".")
    atribs = []
    atribs = atrib.split(".")
    
    obj = instance
    for atrib in atribs:
        if type(obj)==dict:
            result = obj[atrib]
        else:
            try:
                result = getattr(obj, atrib)()
            except:
                result = getattr(obj, atrib)
        
        obj = result
    return result

def TrueFalse(value):
    if type(value)==bool:
        if value:
            return _('True')
        else:
            return _('False')
    return value

def codenerix(value, kind=None):
    if kind:
        if kind == 'skype':
            return u"<a ng-click='$event.stopPropagation();' href='tel:{0}'>{0}</a>".format(value);
        elif kind == 'image':
            return u"<img ng-click='$event.stopPropagation();' src='{0}{1}'>".format(settings.MEDIA_URL, value);
        else:
            raise Exception("Django filter 'codenerix' got a wrong kind named '"+kind+"'")
    
    return value


def multiplication(value, arg):
    return float(value) * float(arg)


def division(value, arg):
    if arg != 0:
        return float(value) / float(arg)
    else:
        return None


def addition(value, arg):
    return float(value) + float(arg)


def subtraction(value, arg):
    return float(value) - float(arg)
