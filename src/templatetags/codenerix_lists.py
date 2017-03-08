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

from django.template import Library
from codenerix.templatetags_lists import join_list, widgetize, istype, addextra, addattr, lockattr, setattrs, ngmodel, inireadonly, date2timewidget, datewidget, unlist, foreignkey, headstyle, column_counter, add_columns, linkedinfo, get_depa, getws, get_field_list, invalidator

def fbuilder1(f): return lambda arg: f(arg)
def fbuilder2(f): return lambda arg1,arg2: f(arg1,arg2)

register = Library()

register.filter('join_list',fbuilder2(join_list))
register.filter('widgetize',fbuilder1(widgetize))
register.filter('istype',fbuilder2(istype))
register.filter('addextra',fbuilder2(addextra))
register.filter('addattr',fbuilder2(addattr))
register.filter('lockattr',fbuilder2(lockattr))
register.filter('setattrs',fbuilder2(setattrs))
register.filter('ngmodel',fbuilder1(ngmodel))
register.filter('inireadonly',fbuilder2(inireadonly))
register.filter('date2timewidget',fbuilder2(date2timewidget))
register.filter('datewidget',fbuilder2(datewidget))
register.filter('unlist',fbuilder1(unlist))
register.filter('foreignkey',fbuilder2(foreignkey))
register.filter('headstyle',fbuilder1(headstyle))
register.filter('column_counter',fbuilder1(column_counter))
register.filter('add_columns',fbuilder2(add_columns))
register.filter('linkedinfo',fbuilder1(linkedinfo))
register.filter('get_depa',fbuilder2(get_depa))
register.filter('getws', fbuilder2(getws))
register.filter('get_field_list', fbuilder1(get_field_list))
register.filter('invalidator', fbuilder2(invalidator))
