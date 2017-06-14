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

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe

from codenerix import __version__


def codenerix(request):
    '''
    Codenerix CONTEXT
    '''
    # Get values
    DEBUG = getattr(settings, 'DEBUG', False)
    VERSION = getattr(settings, 'VERSION', _('WARNING: No version set to this code, add VERSION contant to your configuration'))
    
    # Set environment
    return {
        'DEBUG': DEBUG,
        'VERSION': VERSION,
        'CODENERIX_VERSION': __version__,
    }


def codenerix_js( request ):
    cnf = {}
    
    # Get values
    CONNECTION_ERROR = getattr(settings,'CONNECTION_ERROR', None)
    ALARMS_LOOPTIME  = getattr(settings,'ALARMS_LOOPTIME',  None)
    ALARMS_QUICKLOOP = getattr(settings,'ALARMS_QUICKLOOP', None)
    ALARMS_ERRORLOOP = getattr(settings,'ALARMS_ERRORLOOP', None)
    DEBUG = getattr(settings,'DEBUG', False)
    DATERANGEPICKER_OPTIONS = getattr(settings, 'DATERANGEPICKER_OPTIONS', None)
    DATETIME_RANGE_FORMAT = getattr(settings, 'DATETIME_RANGE_FORMAT', None)
    
    # Set values
    if CONNECTION_ERROR is not None: cnf['connection_error'] = CONNECTION_ERROR
    if ALARMS_LOOPTIME  is not None: cnf['alarms_looptime']  = ALARMS_LOOPTIME
    if ALARMS_QUICKLOOP is not None: cnf['alarms_quickloop'] = ALARMS_QUICKLOOP
    if ALARMS_ERRORLOOP is not None: cnf['alarms_errorloop'] = ALARMS_ERRORLOOP
    cnf['debug'] = str(DEBUG).lower()
    cnf['codenerix_css'] = getattr(settings,'CODENERIX_CSS', _('WARNING: CODENERIX_CSS is not set in your configuration!!!'))
    cnf['codenerix_js']  = getattr(settings,'CODENERIX_JS', _('WARNING: CODENERIX_JS is not set in your configuration!!!'))
    
    # Set daterange
    if (DATERANGEPICKER_OPTIONS is None) or (DATETIME_RANGE_FORMAT is None):
        daterangepicker = '"'
        if DATERANGEPICKER_OPTIONS is None:
            daterangepicker+= "{}".format(_(' WARNING: DATERANGEPICKER_OPTIONS is not set in your configuration!!! '))
        if DATETIME_RANGE_FORMAT is None:
            daterangepicker+= "{}".format(_(' WARNING: DATETIME_RANGE_FORMAT is not set in your configuration!!! '))
        daterangepicker+= '"'
        cnf['daterangepicker'] = mark_safe(daterangepicker)
    else:
        cnf['daterangepicker'] = mark_safe(settings.DATERANGEPICKER_OPTIONS.format(
                    Format=settings.DATETIME_RANGE_FORMAT[1],
                    From= _("From"),
                    To= _("To"),
                    Apply= _("Apply"),
                    Cancel= _("Cancel"),
                    Su= _("Su"),
                    Mo= _("Mo"),
                    Tu= _("Tu"),
                    We= _("We"),
                    Th= _("Th"),
                    Fr= _("Fr"),
                    Sa= _("Sa"),
                    January= _("January"),
                    February= _("February"),
                    March= _('March'),
                    April= _('April'),
                    May= _('May'),
                    June= _('June'),
                    July= _('July'), 
                    August= _('August'), 
                    September= _('September'), 
                    October= _('October'),
                    November= _('November'), 
                    December= _('December')
                    ))
    
    # Return environment
    return {'cnf': cnf }

