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

WEIGHT_UNITS = {
        # SI
        'kg': (_('Kilogram'),1.0),              # BASE
        'g': (_('Gram'), 1000.0),
        # US/UK
        'lb': (_('Pound'), 2.2046228),
        'oz': (_('Ounce'), 35.273962),
        'st': (_('Stone'), 0.15747304),
    }

LENGTH_UNITS = {
        # SI
        'm': (_('Metre'), 1.0),                 # BASE
        'cm': (_('Centimetre'), 100.0),
        'km': (_('Kilometre'), 0.001),
        # US/UK
        'mi': (_('Mile'), 0.00062137119),
        'yd': (_('Yard'), 1.0936133), 
        'ft': (_('Feet'), 3.2808399),
        'in': (_('Inch'), 39.3701),
    }

VOLUME_UNITS = {
        # SI
        'm3': (_('Cubic metre'), 1.0),          # BASE
        'dm3': (_('Cubic decimetre'), 1000.0),
        'l': (_('Litre'), 1000.0),
        'ml': (_('Mililitre'), 1000000.0),
        # UK
        'ig': (_('UK Gallon'), 219.969),
        'ip': (_('UK Pint'), 1759.75),
        # US
        'g': (_('US Gallon'), 264.172),
        'p': (_('US Pint'), 2113.38),
        # US/UK
        'ft3': (_('Cubic feet'), 35.314666882523476),
        'yd3': (_('Cubic yard'), 1.3079506252786468),
        }
