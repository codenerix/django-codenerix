#
# django-codenerix
#
# Codenerix GNU
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
import ssl

from django.conf import settings
from django.core import mail
from django.core.mail.backends.smtp import EmailBackend
from django.core.mail.utils import DNS_NAME


class EmailMessage(mail.EmailMessage):
    def __init__(self, *args, **kwargs):
        new_args = list(args)
        if len(args) >= 4 and args[3] is None:
            print("WARNING: 'to' is None, using ADMINS as email target")
            new_args[3] = [x[1] for x in settings.ADMINS]
        elif "to" in kwargs and kwargs["to"] is None:
            print("WARNING: 'to' is None, using ADMINS as email target")
            kwargs["to"] = [x[1] for x in settings.ADMINS]
        else:
            if settings.DEBUG and hasattr(settings, "CLIENTS"):
                # Warn this is deprecated in favor of FIXED_EMAIL_TARGETS
                raise DeprecationWarning(
                    "CLIENTS setting is deprecated "
                    "use FIXED_EMAIL_TARGETS instead",
                )
            fixed_clients = getattr(settings, "FIXED_EMAIL_TARGETS", None)
            if fixed_clients:
                print(f"WARNING: Using FIXED_EMAIL_TARGETS={fixed_clients}")
                to = [x[1] for x in fixed_clients]
                if len(args) >= 4:
                    new_args[3] = to
                else:
                    kwargs["to"] = to

        super().__init__(*new_args, **kwargs)


class SSLEmailBackend(EmailBackend):
    def __init__(self, *args, **kwargs):
        timeout = getattr(settings, "CLIENT_EMAIL_TIMEOUT", 10)
        kwargs.setdefault("timeout", timeout)
        super().__init__(*args, **kwargs)

    def open(self):
        if self.connection:
            return False
        try:
            self.connection = smtplib.SMTP_SSL(
                self.host,
                self.port,
                local_hostname=DNS_NAME.get_fqdn(),
            )

            if self.username and self.password:
                self.connection.ehlo()
                # Remove CRAM-MD5 authentication method
                self.connection.esmtp_features["auth"] = "PLAIN LOGIN"
                self.connection.login(self.username, self.password)
            return True
        except smtplib.SMTPException:
            if not self.fail_silently:
                raise
        except ssl.SSLError:
            try:
                self.connection = smtplib.SMTP(self.host, self.port)
                self.connection.ehlo()
                self.connection.starttls()
                if self.username and self.password:
                    self.connection.ehlo()
                    # Remove CRAM-MD5 authentication method
                    self.connection.esmtp_features["auth"] = "PLAIN LOGIN"
                    self.connection.login(self.username, self.password)
                return True
            except smtplib.SMTPException:
                if not self.fail_silently:
                    raise


def get_connection(
    host=settings.CLIENT_EMAIL_HOST,
    port=settings.CLIENT_EMAIL_PORT,
    username=settings.CLIENT_EMAIL_USERNAME,
    password=settings.CLIENT_EMAIL_PASSWORD,
    use_tls=settings.CLIENT_EMAIL_USE_TLS,
    use_ssl=settings.CLIENT_EMAIL_USE_SSL,
):
    if use_ssl:
        backend = "codenerix.lib.genmail.SSLEmailBackend"
    else:
        backend = "django.core.mail.backends.smtp.EmailBackend"

    return mail.get_connection(
        backend=backend,
        host=host,
        port=port,
        username=username,
        password=password,
        use_tls=use_tls,
    )
