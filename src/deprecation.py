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

#import os
#import warnings
from django.conf import settings

#class RemovedInCodenerix2017Warning(RuntimeWarning):
#    pass
#RemovedInNextYearVersionWarning = RemovedInCodenerix2017Warning

if "TEMPLATES_CONTEXT_PROCESSORS" in dir(settings):
    if "codenerix.context.version" in settings.TEMPLATE_CONTEXT_PROCESSORS:
        # warnings.warn("TEMPLATE_CONTEXT_PROCESSORS 'codenerix.context.version' will be Deprecated in Codenerix2017 in favor of 'codenerix.context.codenerix'", RemovedInCodenerix2017Warning, stacklevel=2)
        raise IOError,"TEMPLATE_CONTEXT_PROCESSORS 'codenerix.context.version' will be Deprecated in Codenerix2017 in favor of 'codenerix.context.codenerix'"
    if "codenerix.context.settings_js" in settings.TEMPLATE_CONTEXT_PROCESSORS:
        # warnings.warn("TEMPLATE_CONTEXT_PROCESSORS 'codenerix.context.settings_js' will be Deprecated in Codenerix2017 in favor of 'codenerix.context.codenerix_js'", RemovedInCodenerix2017Warning, stacklevel=2)
        raise IOError,"TEMPLATE_CONTEXT_PROCESSORS 'codenerix.context.settings_js' will be Deprecated in Codenerix2017 in favor of 'codenerix.context.codenerix_js'"

