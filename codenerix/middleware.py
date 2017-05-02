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

from django.shortcuts import redirect
from django.conf import settings


class SecureRequiredMiddleware(object):
    def __init__(self, get_response=None):
        self.get_response = get_response
        self.paths = getattr(settings, 'HTTPS_PATHS', getattr(settings, 'SECURE_REQUIRED_PATHS', ('/', )))
        self.enabled = self.paths and getattr(settings, 'HTTPS_SUPPORT', True)
    
    def process_request(self, request):
        
        if self.enabled and not request.is_secure():

            # Check for negative matching, URLs we don't want to be secure
            for path in self.paths:
                full_path = request.get_full_path()
                if path[0] == '-' and (full_path.startswith(path[1:]) or re.compile(path[1:]).match(full_path)):
                    return None
                
            # Check for positive matching, URLs we want to be secure
            for path in self.paths:
                full_path = request.get_full_path()
                if full_path.startswith(path) or re.compile(path).match(full_path):
                    request_url = request.build_absolute_uri(request.get_full_path())
                    secure_url = request_url.replace('http://', 'https://')
                    return redirect(secure_url, permanent=True)

        # Any other lateral case
        return None
    
    def __call__(self, request):
        # Code to be executed for each request before the view (and later middleware) are called.
        response = self.process_request(request)
        
        # Get response
        if response is None:
            response = self.get_response(request)
        
        # Code to be executed for each request/response after the view is called
        # ... pass ...
        
        # Return response
        return response


class CurrentUserMiddleware(object):
    '''
    Let the system to have the username everywhere
    '''
    def __init__(self, get_response=None):
        self.get_response = get_response
    
    def process_request(self, request):
        _user.value = request.user
    
    def __call__(self, request):
        # Code to be executed for each request before the view (and later middleware) are called.
        self.process_request(request)
        
        # Get response
        response = self.get_response(request)
        
        # Code to be executed for each request/response after the view is called
        # ... pass ...
        
        # Return response
        return response
    
def get_current_user():
    '''
    Thought this function you can get the user loged in everywhere
    '''
    if 'value' in dir(_user):
        return _user.value
    else:
        return None
_user = local()

