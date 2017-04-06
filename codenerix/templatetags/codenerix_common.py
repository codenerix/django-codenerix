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

from django import template

from codenerix.helpers import zeropad,monthname,nameunify
from codenerix.templatetags_common import codenerix, nicenull, debugme, debugmedict, addedit, invert, differ, ghtml, smallerthan, br, nicekilometers, niceeuronull, nicepercentnull, nicebool, ynbool, toint, notval, count, countpages, freedombool, pair, lenlist, nbsp, mod, keyvalue, acumulate, getforms, langforms, objectatrib, TrueFalse, multiplication, division, addition, subtraction

def fbuilder1(f): return lambda arg: f(arg)
def fbuilder2(f): return lambda arg1,arg2: f(arg1,arg2)
def fcodenerix(arg1, arg2=None):
    return codenerix(arg1, arg2)

register = template.Library()
register.filter('digitos',zeropad)
register.filter('monthname',monthname)
register.filter('nameunify',nameunify)
register.filter('nicenull',fbuilder1(nicenull))
register.filter('debugme',fbuilder1(debugme))
register.filter('debugmedict',fbuilder1(debugmedict))
register.filter('addedit',fbuilder1(addedit))
register.filter('invert',fbuilder1(invert))
register.filter('differ',fbuilder2(differ))
register.filter('ghtml',fbuilder1(ghtml))
register.filter('smallerthan',fbuilder2(smallerthan))
register.filter('br',fbuilder1(br))
register.filter('nicekilometers',fbuilder1(nicekilometers))
register.filter('niceeuronull',fbuilder1(niceeuronull))
register.filter('nicepercentnull',fbuilder1(nicepercentnull))
register.filter('nicebool',fbuilder1(nicebool))
register.filter('ynbool',fbuilder1(ynbool))
register.filter('toint',fbuilder1(toint))
register.filter('notval',fbuilder1(notval))
register.filter('count',fbuilder1(count))
register.filter('countpages',fbuilder1(countpages))
register.filter('freedombool',fbuilder2(freedombool))
register.filter('pair',fbuilder1(pair))
register.filter('len',fbuilder1(lenlist))
register.filter('nbsp',fbuilder1(nbsp))
register.filter('mod',fbuilder1(mod))
register.filter('keyvalue',fbuilder2(keyvalue))
register.filter('acumulate',fbuilder2(acumulate))
register.filter('getforms',fbuilder2(getforms))
register.filter('langforms',fbuilder2(langforms))
register.filter('objectatrib',fbuilder2(objectatrib))
register.filter('TrueFalse',fbuilder1(TrueFalse))
register.filter('codenerix',fcodenerix)
register.filter('multiplication',fbuilder2(multiplication))
register.filter('division',fbuilder2(division))
register.filter('addition',fbuilder2(addition))
register.filter('subtraction',fbuilder2(subtraction))
