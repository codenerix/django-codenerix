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

try:
    import pyotp
except ImportError:
    pyotp=None
import hashlib
import base64

from django.utils import timezone
from django.contrib.auth import logout
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.conf import settings

def check_auth(user):
    '''
    Check if the user should or shouldn't be inside the system:
    - If the user is staff or superuser: LOGIN GRANTED
    - If the user has a Person and it is not "disabled": LOGIN GRANTED
    - Elsewhere: LOGIN DENIED
    '''
    
    # Initialize authentication
    auth = None
    person = None
    
    # Check if there is an user
    if user:
        
        # It means that Django accepted the user and it is active
        if user.is_staff or user.is_superuser:
            # This is an administrator, let it in
            auth = user
        else:
            # It is a normal user, check if there is a person behind
            person_related=getattr(user,"people",None)
            
            # Check if this person has limited access or not
            if person_related:
                # Must be only one
                if person_related.count()==1:
                    person=person_related.get()
            elif getattr(user,'disabled',False) is not False:
                person = user
            
            if person and ( (person.disabled is None) or (person.disabled>timezone.now()) ):
                # There is a person, no disabled found or the found one is fine to log in 
                auth = user
    
    # Return back the final decision
    return auth


#class LimitedAuth(ModelBackend):
#    '''
#    Authentication system based on default Django's authentication system
#    which extends the last one with check_auth() extra system limitations
#    '''
#    
#    def authenticate(self, username=None, password=None):
#        # Launch default django authentication
#        user = super(LimitedAuth, self).authenticate(username, password)
#        
#        # Answer to the system
#        answer = check_auth(user)
#        return answer


class LimitedAuthMiddleware(object):
    '''
    Check every request if the user should or shouldn't be inside the system
    
    NOTE: install in your MIDDLEWARE_CLASSES setting after (order matters):
        'django.contrib.auth.middleware.AuthenticationMiddleware'
    '''
    
    def process_request(self, request):
        # If the user is authenticated and shouldn't be
        if request.user.is_authenticated() and not check_auth(request.user):
            # Push it out from the system
            logout(request)


class TokenAuth(ModelBackend):
    '''
    Authentication system based on a Token key
    '''
    
    def authenticate(self, username=None, token=None, string=None):
        try:
            # Get the requested username
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
        
        if user:
            # Get config
            config = {
                       'key': None,
           'master_unsigned': False,
             'user_unsigned': False,
              'otp_unsigned': False,
             'master_signed': False,
               'user_signed': False,
                'otp_signed': False,
                }
            config_settings = getattr(settings,'AUTHENTICATION_TOKEN',{})
            for (key,value) in config_settings.items():
                config[key]=value
            
            # Get keys
            if config['key'] or config['master_unsigned'] or config['master_signed']:
                if config['key'] and ( config['master_unsigned'] or config['master_signed'] ):
                    master = config['key']
                else:
                    if settings.DEBUG:
                        raise IOError,"To use a master key you have to set master_signed or master_unsigned to True and set 'master' to some valid string as your token"
                    else:
                        master = None
            else:
                master = None
            
            if config['user_unsigned'] or config['user_signed'] or config['otp_unsigned'] or config['otp_signed']:
                if user.first_name:
                    user_key = user.first_name
                    
                    if config['otp_unsigned'] or config['otp_signed']:
                        if not pyotp:
                            raise IOError,"PYOTP library not found, you can not use OTP signed/unsigned configuration"
                        else:
                            try:
                                otp = str(pyotp.TOTP(base64.b32encode(user_key)).now())
                            except TypeError:
                                if settings.DEBUG:
                                    raise IOError,"To use a OTP key you have to set a valid BASE32 string in the user's profile as your token, the string must be 16 characters long (first_name field in the user's model) - BASE32 string can have only this characters 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567='"
                                else:
                                    otp = None
                    else:
                        otp = None
                else:
                    if settings.DEBUG:
                        raise IOError,"To use a user/otp key you have to set user_signed, user_unsigned, otp_signed or otp_unsigned to True and set the user key in the user's profile to some valid string as your token (first_name field in the user's model)"
                    else:
                        user_key = None
                        otp = None
            else:
                user_key = None
                otp = None
            
            # Unsigned string
            if config['master_signed'] or config['user_signed'] or config['otp_signed']:
                tosign=username+string
            
            # Build the list of valid keys
            keys=[]
            if master:
                if config['master_unsigned']:                   # MASTER KEY
                    # keys.append("master_unsigned")
                    keys.append(master)
                if config['master_signed']:                     # MASTER KEY SIGNED
                    # keys.append("master_signed")
                    keys.append(hashlib.sha1(tosign+master).hexdigest())
            if user_key:
                if config['user_unsigned']:                     # USER KEY
                    # keys.append("user_unsigned")
                    keys.append(user_key)
                if config['user_signed']:                       # USER KEY SIGNED
                    # keys.append("user_signed")
                    keys.append(hashlib.sha1(tosign+user_key).hexdigest())
            if otp:
                if config['otp_unsigned']:                      # OTP KEY
                    # keys.append("otp_unsigned")
                    keys.append(otp)
                if config['otp_signed']:                        # OTP KEY SIGNED
                    # keys.append("otp_signed")
                    keys.append(hashlib.sha1(tosign+otp).hexdigest())
            
            # Key is valid
            if token in keys:
                answer = user
            else:
                # Not authenticated
                answer = None
            
        else:
            
            # Username not found, not accepting the authentication request
            answer = None
        
        # Return answer
        return answer


class TokenAuthMiddleware(object):
    '''
    Check for every request if the user is not loged in, so we can log it in with a TOKEN
    
    NOTE 1: install in your MIDDLEWARE_CLASSES setting after (order matters):
        'django.contrib.auth.middleware.AuthenticationMiddleware'
    
    NOTE 2: if you are using POST with HTTPS, Django will require to send Referer, to avoid
        this problem you must add to the view of your url definition csrf_exempt(), as follows:
        
        from django.views.decorators.csrf import csrf_exempt
        urlpatterns = patterns(
            # ...
            # Will exclude `/api/v1/test` from CSRF 
            url(r'^api/v1/test', csrf_exempt(TestApiHandler.as_view()))
            # ...
        )
        
        Check: http://stackoverflow.com/questions/11374382/how-can-i-disable-djangos-csrf-protection-only-in-certain-cases
        They recommend in this post to use the decorator, but we didn't manage to make it work
        in the post() method inside our class-view. Probably this will work in the dispatch().
    '''
    
    def process_request(self, request):
        # By default we are not in authtoken
        request.authtoken=False
        # Get body
        body = request.body
        # Get token
        token = request.GET.get("authtoken",request.POST.get("authtoken",""))
        # If the user is authenticated and shouldn't be
        if token:
            username = request.GET.get("authuser",request.POST.get("authuser",None))
            json = request.GET.get("json",request.POST.get("json", body))
            # Authenticate user
            user = authenticate(username=username,token=token,string=json)
            if user:
                # Set we are in authtoken
                request.authtoken=True
                # Log user in
                login(request,user)
                # Disable CSRF checks
                setattr(request, '_dont_enforce_csrf_checks', True)
                json_details = request.GET.get("authjson_details",request.POST.get("authjson_details",False))
                if json_details in ['true', '1', 't', True]:
                    json_details = True
                else:
                    json_details = False
                request.json_details = json_details

