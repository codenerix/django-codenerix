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

import re
from threading import local

from django.http import HttpResponsePermanentRedirect
from django.conf import settings

class SecureRequiredMiddleware(object):
    def __init__(self):
        self.paths = getattr(settings, 'HTTPS_PATHS', getattr(settings, 'SECURE_REQUIRED_PATHS',('/',)))
        self.enabled = self.paths and getattr(settings, 'HTTPS_SUPPORT', True)
    
    def process_request(self, request):
        if self.enabled and not request.is_secure():
            for path in self.paths:
                full_path = request.get_full_path()
                if path[0]=='-' and (full_path.startswith(path[1:]) or re.compile(path[1:]).match(full_path)):
                    return None
            for path in self.paths:
                full_path = request.get_full_path()
                if full_path.startswith(path) or re.compile(path).match(full_path):
                    request_url = request.build_absolute_uri(request.get_full_path())
                    secure_url = request_url.replace('http://', 'https://')
                    return HttpResponsePermanentRedirect(secure_url)
        return None

class CurrentUserMiddleware(object):
    '''
    Let the system to have the username everywhere
    '''
    def process_request(self, request):
        _user.value = request.user
    
def get_current_user():
    '''
    Thought this function you can get the user loged in everywhere
    '''
    if 'value' in dir(_user):
        return _user.value
    else:
        return None
_user = local()

