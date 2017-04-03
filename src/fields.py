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

import os
import sys
import socket
from datetime import datetime

from django import forms
from django.db import models
from django.conf import settings
from django.forms.utils import ValidationError
from django.utils.translation import ugettext as _
from django.forms.widgets import Textarea
from django.utils.encoding import smart_text

from multi_email_field.forms import MultiEmailField as MultiEmailFormField
from captcha import client

from codenerix.widgets import FileAngularInput, Date2TimeInput, WysiwygAngularInput, GenReCaptchaInput, MultiBlockWysiwygInput, BootstrapWysiwygInput

class FileAngularField(models.FileField):
    description = "File manage throught the Angular service system"
    
    def formfield(self, **kwargs):
        defaults = {'widget': FileAngularInput}
        defaults.update(kwargs)
        return super(FileAngularField, self).formfield(**defaults)

class ImageAngularField(models.ImageField):
    description = "Image field for Angular JS"
    
    def formfield(self, **kwargs):
        defaults = {'widget': FileAngularInput}
        defaults.update(kwargs)
        return super(ImageAngularField, self).formfield(**defaults)


class Date2TimeField(models.DateTimeField):
    def formfield(self, **kwargs):
        defaults = {'widget': Date2TimeInput}
        defaults.update(kwargs)
        return super(Date2TimeField, self).formfield(**defaults)
    
    def clean(self, *args, **kwargs):
        date_min = datetime(2000, 1, 1, 0, 0, 0)
        
        if args[0]:
            if type(args[0]) is not datetime:
                raise ValidationError(_("Invalid date"))
            elif args[0] and date_min.date()>args[0].date(): 
                raise ValidationError(_("Date too old"))
            #return args[0]
        return super(Date2TimeField, self).clean(*args, **kwargs)


email_er = "[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*"
class MultiEmailField(MultiEmailFormField):
    message = _("Enter valid email addresses.")
    widget = Textarea(attrs={'ng-pattern': "/^({0})(\\n{0})*$/".format(email_er)})
    
    def to_python(self, value):
        if value:
            for char in [',',' ','\r']:
                value=value.replace(char,"\n").replace("\n\n","\n")
        return super(MultiEmailField, self).to_python(value)

class WysiwygAngularField(models.TextField):
    description = "A hand of cards (bridge style)"
    
    def formfield(self, **kwargs):
        defaults = {'widget': WysiwygAngularInput}
        defaults.update(kwargs)
        return super(WysiwygAngularField, self).formfield(**defaults)

class MultiBlockWysiwygField(models.TextField):
    description = "Multi block WYSIWYG"
    
    def formfield(self, **kwargs):
        defaults = {'widget': MultiBlockWysiwygInput}
        defaults.update(kwargs)
        return super(MultiBlockWysiwygField, self).formfield(**defaults)

class BootstrapWysiwygField(models.TextField):
    description = "Bootstrap WYSIWYG"
    
    def formfield(self, **kwargs):
        defaults = {'widget': BootstrapWysiwygInput}
        defaults.update(kwargs)
        return super(BootstrapWysiwygField, self).formfield(**defaults)

class GenReCaptchaField(forms.CharField):
    description = "ReCaptcha field throught the Angular service system"
    default_error_messages = {
        'captcha_invalid': _('Incorrect, please try again.'),
        'captcha_error': _('Error verifying input, please try again.'),
    }

    def __init__(self, public_key=None, private_key=None, use_ssl=None, attrs={}, *args, **kwargs):
        """
        ReCaptchaField can accepts attributes which is a dictionary of
        attributes to be passed to the ReCaptcha widget class. The widget will
        loop over any options added and create the RecaptchaOptions
        JavaScript variables as specified in
        https://code.google.com/apis/recaptcha/docs/customization.html
        
        On compiled verstion of the library, don't forget to add before the codenerix.js scripts to add:
        <script type="text/javascript" src="https://www.google.com/recaptcha/api.js?onload=vcRecaptchaApiLoaded&render=explicit" async defer></script>$
        """
        public_key = public_key if public_key else \
            settings.RECAPTCHA_PUBLIC_KEY
        self.private_key = private_key if private_key else \
            settings.RECAPTCHA_PRIVATE_KEY
        self.use_ssl = use_ssl if use_ssl is not None else getattr(
            settings, 'RECAPTCHA_USE_SSL', False)
        
        self.widget = GenReCaptchaInput(public_key=public_key, use_ssl=self.use_ssl, attrs=attrs)
        self.required = True
        return super(GenReCaptchaField, self).__init__(*args, **kwargs)
    
    def get_remote_ip(self):
        f = sys._getframe()
        while f:
            if 'request' in f.f_locals:
                request = f.f_locals['request']
                if request:
                    remote_ip = request.META.get('REMOTE_ADDR', '')
                    forwarded_ip = request.META.get('HTTP_X_FORWARDED_FOR', '')
                    ip = remote_ip if not forwarded_ip else forwarded_ip
                    return ip
            f = f.f_back
    
    def clean(self, values):
        super(GenReCaptchaField, self).clean(values[0])
        recaptcha_challenge_value = smart_text(values[0])
        recaptcha_response_value = smart_text(values[1])
        
        if os.environ.get('RECAPTCHA_TESTING', None) == 'True' and recaptcha_response_value == 'PASSED':
            return values[0]
        
        try:
            check_captcha = client.submit(
                recaptcha_challenge_value,
                recaptcha_response_value, private_key=self.private_key,
                remoteip=self.get_remote_ip(), use_ssl=self.use_ssl)
            
        except socket.error: # Catch timeouts, etc
            # raise IOError,"ERROR: {}".format(self.error_messages['captcha_error'])
            raise ValidationError(
                self.error_messages['captcha_error']
            )
        
        if not check_captcha.is_valid:
            # raise IOError,"INVALID: {}".format(self.error_messages['captcha_invalid'])
            raise ValidationError(
                self.error_messages['captcha_invalid']
            )
        
        return values[0]

