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

import smtplib
from django.core import mail
from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend
from django.core.mail.utils import DNS_NAME


class EmailMessage(mail.EmailMessage):
    
    def __init__(self, *args, **kwargs):
        new_args = list(args)
        if len(args) >= 3 and args[3] is None:
            new_args[3] = [x[1] for x in settings.ADMINS]
        elif 'to' in kwargs and kwargs['to'] is None:
            kwargs['to'] = [x[1] for x in settings.ADMINS]
        else:
            if settings.DEBUG and settings.CLIENTS:
                if len(args) >= 3:
                    new_args[3] = [x[1] for x in settings.CLIENTS]
                else:
                    kwargs['to'] = [x[1] for x in settings.CLIENTS]
        
        super(EmailMessage, self).__init__(*new_args, **kwargs)


class SSLEmailBackend(EmailBackend):

    def __init__(self, *args, **kwargs):
        timeout = getattr(settings, "CLIENT_EMAIL_TIMEOUT", 10)
        kwargs.setdefault('timeout', timeout)
        super(SSLEmailBackend, self).__init__(*args, **kwargs)

    def open(self):
        if self.connection:
            return False
        try:
            self.connection = smtplib.SMTP_SSL(
                self.host, self.port, local_hostname=DNS_NAME.get_fqdn())

            if self.username and self.password:
                self.connection.ehlo()
                # Remove CRAM-MD5 authentication method
                self.connection.esmtp_features['auth'] = 'PLAIN LOGIN'
                self.connection.login(self.username, self.password)
            return True
        except smtplib.SMTPException:
            if not self.fail_silently:
                raise


def get_connection(host=settings.CLIENT_EMAIL_HOST, port=settings.CLIENT_EMAIL_PORT, username=settings.CLIENT_EMAIL_USERNAME, password=settings.CLIENT_EMAIL_PASSWORD, use_tls=settings.CLIENT_EMAIL_USE_TLS):
    return mail.get_connection(
        backend="codenerix.lib.genmail.SSLEmailBackend",
        host=host,
        port=port,
        username=username,
        password=password,
        use_tls=use_tls
    )
