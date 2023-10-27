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

try:
    import pyotp  # type: ignore[import-not-found]
except ImportError:
    pyotp = None
import base64
import datetime
import hashlib
import ssl
import time

import ldap3
from codenerix_lib.debugger import Debugger
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Group, User
from django.utils import timezone
from ldap3.core.exceptions import LDAPException, LDAPSocketOpenError


def hashed(string):
    """
    Hash a string with several algorithms and return all of them
    Allowed algorithms for authentication are:
    - SHA1 <--- DEPRECATED and will be removed in future versions
    - SHA256
    - SHA512
    - SHA3_256 <--- RECOMMENDED
    - SHA3_512
    """
    algorightms = [
        hashlib.sha1,  # DEPRECATED: Backward compatibility with old versions
        hashlib.sha256,
        hashlib.sha512,
        hashlib.sha3_256,
        hashlib.sha3_512,
    ]
    return [
        algorithm(string, usedforsecurity=True).hexdigest()
        for algorithm in algorightms
    ]


def check_auth(user, debugger=None):
    """
    Check if the user should or shouldn't be inside the system:
    - If the user is staff or superuser: LOGIN GRANTED
    - If the user has a Person and it is not "disabled": LOGIN GRANTED
    - Elsewhere: LOGIN DENIED
    """

    # Initialize authentication
    auth = None
    person = None

    # Check if there is an user
    if user:
        # Show debugger
        if debugger:
            debugger(
                "check_auth(): Username: '{}'".format(user),
                color="white",
            )

        # It means that Django accepted the user and it is active
        if user.is_staff or user.is_superuser:
            # This is an administrator, let it in
            auth = user

            # Show debugger
            if debugger:
                debugger(
                    "check_auth(): user '{}' is an Administrator".format(user),
                    color="green",
                )

        else:
            # Show debugger
            if debugger:
                debugger(
                    "check_auth(): user '{}' is a Normal User".format(user),
                    color="cyan",
                )

            # It is a normal user, check if there is a person behind
            person = getattr(user, "person", None)
            if not person:
                # Show debugger
                if debugger:
                    debugger(
                        "check_auth(): no associated person found for "
                        f"user '{user}'",
                        color="yellow",
                    )

                # Check if there is related one
                person_related = getattr(user, "people", None)
                if person_related:
                    # Show debugger
                    if debugger:
                        debugger(
                            "check_auth(): there are People associated for "
                            f"user '{user}'",
                            color="cyan",
                        )

                    # Must be only one
                    if person_related.count() == 1:
                        # Person found
                        person = person_related.get()

                    elif debugger:
                        debugger(
                            "check_auth(): found more than One People "
                            f"associated for user '{user}', "
                            "not valid Person found!",
                            color="yellow",
                        )

                elif debugger:
                    debugger(
                        "check_auth(): no People found for "
                        f"for user '{user}', not valid Person found!",
                        color="red",
                    )

            # Show debugger
            if debugger and person:
                debugger(
                    "check_auth(): user={} - person={} - disabled={}'".format(
                        user,
                        person,
                        person.disabled,
                    ),
                    color="cyan",
                )

            # Check if the person is already disabled
            if person and (
                (person.disabled is None) or (person.disabled > timezone.now())
            ):
                # There is a person, no disabled found or the found one is
                # fine to log in
                auth = user

                if debugger:
                    debugger(
                        f"check_auth(): user '{user}' access granted!",
                        color="green",
                    )

            elif debugger:
                debugger(
                    f"check_auth(): user '{user}' access NOT granted!",
                    color="red",
                )

    elif debugger:
        debugger(
            "check_auth(): No username, access NOT granted!",
            color="red",
        )

    # Return back the final decision
    return auth


class LimitedAuth(ModelBackend, Debugger):
    """
    Authentication system based on default Django's authentication system
    which extends the last one with check_auth() extra system limitations
    """

    def __init__(self, *args, **kwargs):
        # Configure debugger
        self.__debugger = getattr(settings, "AUTHENTICATION_DEBUG", False)
        if self.__debugger:
            self.set_debug()

        # Keep going with super
        super().__init__(*args, **kwargs)

    def authenticate(self, *args, **kwargs):
        # Show debugger
        if self.__debugger:
            self.debug("Started authenticate()", color="blue")

        # Launch default django authentication
        user = super().authenticate(*args, **kwargs)

        # Answer to the system
        answer = check_auth(user, self.debug)
        return answer


class LimitedAuthMiddleware(Debugger):
    """
    Check every request if the user should or shouldn't be inside the system
    SESSION_EXPIRE_WHEN_INACTIVE: number of seconds the user can be innactive
    on the website without being logged out SESSION_SHIFTS: list of hours of
    the day when all users must be logged out

    NOTE: install in your MIDDLEWARE setting after (order matters):
        'django.contrib.auth.middleware.AuthenticationMiddleware'
    """

    def __init__(self, get_response=None):
        # Configure debugger
        self.__debugger = getattr(settings, "AUTHENTICATION_DEBUG", False)
        if self.__debugger:
            self.set_debug()

        # Get response
        self.get_response = get_response

    def process_request(self, request):
        # Show debugger
        if self.__debugger:
            self.debug("Started process_request()", color="blue")

        # If the user is authenticated and shouldn't be
        if request.user.is_authenticated:
            # Show debugger
            if self.__debugger:
                self.debug("User already authenticated", color="cyan")

            # If the user doesn't pass the check_auth test
            if not check_auth(request.user, self.debug):
                # Show debugger
                if self.__debugger:
                    self.debug("User didn'pass check_auth()", color="red")

                # Push it out from the system
                logout(request)

            # Show debugger
            elif self.__debugger:
                self.debug("User pass check_auth()", color="green")

            # Get now
            now = datetime.datetime.now()

            # Create delta for caducity by EXPIRE_WHEN_INACTIVE
            expire_when_innactive = getattr(
                settings,
                "SESSION_EXPIRE_WHEN_INACTIVE",
                None,
            )
            if expire_when_innactive is not None:
                # Get last_seen
                last_seen = request.session.get("user_last_seen", None)
                # Calculate delta
                if last_seen is not None:
                    # Check if we have to logout this user for being
                    # innactive too long
                    try:
                        # python3
                        nowts = now.timestamp()
                    except AttributeError:
                        # python2
                        nowts = float(
                            time.mktime(now.timetuple())
                            + now.microsecond / 1000000.0,
                        )

                    diff = nowts - last_seen - expire_when_innactive

                    # Get caducity
                    if diff > 0:
                        # Push it out from the system
                        logout(request)

                # Refresh last_seen
                last_seen = datetime.datetime.now()
                try:
                    # python3
                    last_seen = last_seen.timestamp()
                except AttributeError:
                    # python2
                    last_seen = float(
                        time.mktime(last_seen.timetuple())
                        + last_seen.microsecond / 1000000.0,
                    )

                # Remember in session
                request.session["user_last_seen"] = last_seen

            # Create delta for caducity by SHIFTS
            shifts = getattr(settings, "SESSION_SHIFTS", None)
            if shifts is not None:
                shifts = shifts + [shifts[0] + 24]
                for turno in shifts:
                    if turno > now.hour:
                        delta = turno % 24
                        break

                # Calculate caducity
                kickout = datetime.datetime(
                    now.year,
                    now.month,
                    now.day,
                    delta,
                )
                try:
                    # python3
                    kickout = kickout.timestamp() - now.timestamp()
                except AttributeError:
                    # python2
                    ts = float(
                        time.mktime(kickout.timetuple())
                        + kickout.microsecond / 1000000.0,
                    )
                    tz = float(
                        time.mktime(now.timetuple())
                        + now.microsecond / 1000000.0,
                    )
                    kickout = ts - tz

                # Get caducity
                caducity = request.session.get("user_session_caducity", None)
                if not caducity or kickout < caducity:
                    # Remember new caducity
                    request.session.set_expiry(kickout)
                    request.session["user_session_caducity"] = kickout
                else:
                    # Push it out from the system
                    request.session.pop("user_session_caducity")
                    logout(request)

        elif self.__debugger:
            self.debug("User not authenticated", color="yellow")

    def __call__(self, request):
        # Code to be executed for each request before the view (and later
        # middleware) are called.
        self.process_request(request)

        # Get response
        response = self.get_response(request)

        # Code to be executed for each request/response after the view
        # is called
        # ... pass ...

        # Return response
        return response


class TokenAuth(ModelBackend, Debugger):
    """
    Authentication system based on a Token key
    """

    def __init__(self, *args, **kwargs):
        # Configure debugger
        self.__debugger = getattr(settings, "AUTHENTICATION_DEBUG", False)
        if self.__debugger:
            self.set_debug()

        # Keep going with super
        super().__init__(*args, **kwargs)

    def authenticate(self, *args, **kwargs):
        # Show debugger
        if self.__debugger:
            self.debug("Started authenticate()", color="blue")

        # Get our arguments
        username = kwargs.get("username", None)
        token = kwargs.get("token", None)
        string = kwargs.get("string", "")

        # Show debug
        if self.__debugger:
            self.debug(
                "Authentication request:",
                color="white",
            )
            self.debug(
                "  > Username [authuser]: '{}'".format(username),
                color="cyan",
            )
            self.debug(
                f"  > Token [authtoken]: '{token}' <- authentication "
                "token (signed or unsigned)",
                color="cyan",
            )
            self.debug(
                "  > String [json]: '{}' <- string to be used as salt".format(
                    string,
                ),
                color="cyan",
            )

        if username is not None and token is not None:
            # Try to find the user
            try:
                # Get the requested username
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                user = None

            # If we got an user
            if user:
                # Show debug
                if self.__debugger:
                    self.debug(
                        "User '{}' found!".format(username),
                        color="green",
                    )

                # Get config
                config = {
                    "key": None,
                    "master_unsigned": False,
                    "user_unsigned": False,
                    "otp_unsigned": False,
                    "master_signed": False,
                    "user_signed": False,
                    "otp_signed": False,
                }
                config_settings = getattr(settings, "AUTHENTICATION_TOKEN", {})
                for key, value in config_settings.items():
                    config[key] = value

                # Show debug
                if self.__debugger:
                    self.debug(
                        "Authentication configuration:",
                        color="white",
                    )
                    for key, value in config_settings.items():
                        if value:
                            color = "blue"
                        else:
                            color = "purple"
                        self.debug(
                            "  > {}: {}".format(key, value),
                            color=color,
                        )

                # Get keys
                if (
                    config["key"]
                    or config["master_unsigned"]
                    or config["master_signed"]
                ):
                    if config["key"] and (
                        config["master_unsigned"] or config["master_signed"]
                    ):
                        # Assign master key
                        master = config["key"]

                    else:
                        if self.__debugger:
                            raise OSError(
                                "To use a master key you have to set "
                                "master_signed or master_unsigned to "
                                "True and set 'master' to some valid "
                                "string as your token",
                            )
                        else:
                            master = None
                else:
                    master = None

                if (
                    config["user_unsigned"]
                    or config["user_signed"]
                    or config["otp_unsigned"]
                    or config["otp_signed"]
                ):
                    # Check if user first_name is filled
                    if user.first_name:
                        # Get user first_name as user_key
                        user_key = user.first_name

                        if config["otp_unsigned"] or config["otp_signed"]:
                            if not pyotp:
                                raise OSError(
                                    "PYOTP library not found, you can not "
                                    "use OTP signed/unsigned configuration",
                                )
                            else:
                                try:
                                    otp = str(
                                        pyotp.TOTP(
                                            base64.b32encode(
                                                user_key.encode(),
                                            ),
                                        ).now(),
                                    )
                                except TypeError:
                                    if self.__debugger:
                                        raise OSError(
                                            f"To use a OTP key you have to set a valid BASE32 string in the user's profile as your token, the string must be 16 characters long (first_name field in the user's model) - BASE32 string can have only this characters 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567='. User {user_key} key length is {len(user_key)} ",  # noqa: E501
                                        )
                                    else:
                                        otp = None
                        else:
                            otp = None

                        # Remove user key if not in use
                        if (not config["user_unsigned"]) or (
                            not config["user_signed"]
                        ):
                            user_key = None

                    else:
                        if self.__debugger:
                            raise OSError(
                                "To use a user/otp key you have to set user_signed, user_unsigned, otp_signed or otp_unsigned to True and set the user key in the user's profile to some valid string as your token (first_name field in the user's model)",  # noqa: E501
                            )
                        else:
                            user_key = None
                            otp = None
                else:
                    user_key = None
                    otp = None

                # Show debug
                if self.__debugger:
                    self.debug(
                        "Clear text keys:",
                        color="white",
                    )
                    if master:
                        info = []
                        if config.get("master_signed", False):
                            info.append("signed")
                        if config.get("master_unsigned", False):
                            info.append("unsigned")
                        self.debug(
                            "  > Master KEY configured: '{}' [{}]".format(
                                master,
                                ", ".join(info),
                            ),
                            color="blue",
                        )
                    else:
                        self.debug(
                            "  > Master KEY NOT configured",
                            color="purple",
                        )
                    if user_key:
                        info = []
                        if config.get("user_signed", False):
                            info.append("signed")
                        if config.get("user_unsigned", False):
                            info.append("unsigned")
                        self.debug(
                            "  > User KEY configured: '{}' [{}]".format(
                                user_key,
                                ", ".join(info),
                            ),
                            color="blue",
                        )
                    else:
                        self.debug(
                            "  > User KEY NOT configured",
                            color="purple",
                        )
                    if otp:
                        info = []
                        if config.get("otp_signed", False):
                            info.append("signed")
                        if config.get("otp_unsigned", False):
                            info.append("unsigned")
                        self.debug(
                            "  > OTP KEY configured: '{}' [{}]".format(
                                otp,
                                ", ".join(info),
                            ),
                            color="blue",
                        )
                    else:
                        self.debug(
                            "  > OTP KEY NOT configured",
                            color="purple",
                        )

                # Unsigned string
                if (
                    config["master_signed"]
                    or config["user_signed"]
                    or config["otp_signed"]
                ):
                    tosign = user.username + string

                # Show debugger
                if self.__debugger:
                    self.debug(
                        "Configured calculated keys:",
                        color="white",
                    )
                    self.debug(
                        "  > tosign = '{}' = '{}' + '{}'".format(
                            tosign,
                            user.username,
                            string,
                        ),
                        color="white",
                    )

                # Build the list of valid keys
                keys = []
                if master:
                    if config["master_unsigned"]:  # MASTER KEY
                        # keys.append("master_unsigned")
                        keys.append(master)

                        # Show debugger
                        if self.__debugger:
                            if keys[-1] == token:
                                color = "cyan"
                            else:
                                color = "blue"
                            self.debug(
                                "  > Master Unsigned Key: {}".format(keys[-1]),
                                color=color,
                            )

                    if config["master_signed"]:  # MASTER KEY SIGNED
                        # keys.append("master_signed")
                        keys += hashed(tosign.encode() + master.encode())

                        # Show debugger
                        if self.__debugger:
                            if keys[-1] == token:
                                color = "green"
                            else:
                                color = "blue"
                            self.debug(
                                f"  > Master Signed Key: {keys[-1]} "
                                f"<- HASHED( {tosign} + {master} )",
                                color=color,
                            )

                if user_key:
                    if config["user_unsigned"]:  # USER KEY
                        # keys.append("user_unsigned")
                        keys.append(user_key)

                        # Show debugger
                        if self.__debugger:
                            if keys[-1] == token:
                                color = "green"
                            else:
                                color = "blue"
                            self.debug(
                                "  > User Unsigned Key: {}".format(keys[-1]),
                                color=color,
                            )

                    if config["user_signed"]:  # USER KEY SIGNED
                        # keys.append("user_signed")
                        keys += hashed(tosign.encode() + user_key.encode())

                        # Show debugger
                        if self.__debugger:
                            if keys[-1] == token:
                                color = "green"
                            else:
                                color = "blue"
                            self.debug(
                                f"  > User Signed Key: {keys[-1]} "
                                f"<- HASHED( {tosign} + {user_key} )",
                                color=color,
                            )

                if otp:
                    if config["otp_unsigned"]:  # OTP KEY
                        # keys.append("otp_unsigned")
                        keys.append(otp)

                        # Show debugger
                        if self.__debugger:
                            if keys[-1] == token:
                                color = "green"
                            else:
                                color = "blue"
                            self.debug(
                                "  > OTP Unsigned Key: {}".format(keys[-1]),
                                color=color,
                            )

                    if config["otp_signed"]:  # OTP KEY SIGNED
                        # keys.append("otp_signed")
                        keys += hashed(tosign.encode() + otp.encode())

                        # Show debugger
                        if self.__debugger:
                            if keys[-1] == token:
                                color = "green"
                            else:
                                color = "blue"
                            self.debug(
                                f"  > OTP Signed Key: {keys[-1]} "
                                f"<- HASHED( {tosign} + {otp} )",
                                color=color,
                            )

                # Key is valid
                if token in keys:
                    answer = user

                    # Show debug
                    if self.__debugger:
                        self.debug(
                            "User '{}' authenticated!".format(username),
                            color="green",
                        )

                else:
                    # Not authenticated
                    answer = None

                    # Show debug
                    if self.__debugger:
                        self.debug(
                            f"User '{username}' NOT authenticated with "
                            f"tokenkey '{token}'!",
                            color="red",
                        )

            else:
                # Username not found, not accepting the authentication request
                answer = None

                # Show debug
                if self.__debugger:
                    self.debug(
                        "User '{}' NOT found!".format(username),
                        color="yellow",
                    )

        else:
            # Missing data, can not authenticate with this information
            answer = None

            # Show debug
            if self.__debugger:
                self.debug(
                    "Missing data, can not authenticte with this information",
                    color="yellow",
                )

        # Return answer
        return answer


class TokenAuthMiddleware(Debugger):
    """
    Check for every request if the user is not loged in, so we can log it
    in with a TOKEN

    NOTE 1: install in your MIDDLEWARE setting after (order matters):
        'django.contrib.auth.middleware.AuthenticationMiddleware'

    NOTE 2: if you are using POST with HTTPS, Django will require to
        send Referer, to avoid this problem you must add to the view
        of your url definition csrf_exempt(), as follows:

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
    """  # noqa: E501

    def __init__(self, get_response=None):
        # Configure debugger
        self.__debugger = getattr(settings, "AUTHENTICATION_DEBUG", False)
        if self.__debugger:
            self.set_debug()

        # Get response
        self.get_response = get_response

    def process_request(self, request):
        # Show debugger
        if self.__debugger:
            self.debug("Started process_request()", color="blue")

        # By default we are not in authtoken
        request.authtoken = False

        # Get body
        body = request.body

        # Get token
        token = request.GET.get("authtoken", request.POST.get("authtoken", ""))

        # If the user is authenticated and shouldn't be
        if token:
            if self.__debugger:
                self.debug("AUTHTOKEN='{}'".format(token), color="cyan")

            # Get username and json
            username = request.GET.get(
                "authuser",
                request.POST.get("authuser", None),
            )
            json = request.GET.get(
                "json",
                request.POST.get("json", body.decode()),
            )
            if self.__debugger:
                self.debug(
                    "USERNAME={} - JSON={}".format(username, json),
                    color="cyan",
                )

            # Authenticate user
            user = authenticate(
                request=None,
                username=username,
                token=token,
                string=json,
            )
            if user:
                # Show debug
                if self.__debugger:
                    self.debug("User authenticated", color="green")

                # Set we are in authtoken
                request.authtoken = True
                # Log user in
                login(request, user)
                # Disable CSRF checks
                setattr(request, "_dont_enforce_csrf_checks", True)
                json_details = request.GET.get(
                    "authjson_details",
                    request.POST.get("authjson_details", False),
                )
                if json_details in ["true", "1", "t", True]:
                    json_details = True
                else:
                    json_details = False
                request.json_details = json_details

            elif self.__debugger:
                self.debug("User not authenticated", color="red")

        elif self.__debugger:
            self.debug("No authtoken found in your request", color="yellow")

    def __call__(self, request):
        # Code to be executed for each request before the view (and later
        # middleware) are called.
        self.process_request(request)

        # Get response
        response = self.get_response(request)

        # Code to be executed for each request/response after the view
        # is called
        # ... pass ...

        # Return response
        return response


class ActiveDirectoryGroupMembershipSSLBackend:
    """
    Authorization backend for Active Directory in Django

    # Possible configuration parameters
    # AD_SSL = True                             # Use SSL
    # AD_CERT_FILE='/path/to/your/cert.txt'     # Path to SSL certificate
    # AD_DEBUG_FILE='/tmp/ldap.debug'           # Path to DEBUG file (if none, Debugging will be disabled)
    # AD_LDAP_PORT=9834                         # Port to use
    # AD_DNS_NAME='NTDOMAIN.CODENERIX.COM'      # DNS nameserver if different thatn NT4 DOMAIN
    AD_LOCK_UNAUTHORIZED=True                   # Unauthorized users in Active Directory should be locked in Django
    AD_NT4_DOMAIN='NTDOMAIN.CODENERIX.COM'      # NT4 Domain name
    AD_MAP_FIELDS= {                            # Fields to map:   left=Django   right=Active Directory
            'email':        'mail',
            'first_name':   'givenName',
            'last_name':    'sn',
        }
    """  # noqa: E501

    __debug = None

    def debug(self, msg):
        """
        Handle the debugging to a file
        """
        # If debug is not disabled
        if self.__debug is not False:
            # If never was set, try to set it up
            if self.__debug is None:
                # Check what do we have inside settings
                debug_filename = getattr(settings, "AD_DEBUG_FILE", None)
                if debug_filename:
                    # Open the debug file pointer
                    self.__debug = open(settings.AD_DEBUG_FILE, "a")
                else:
                    # Disable debuging forever
                    self.__debug = False

            if self.__debug:
                # Debug the given message
                self.__debug.write("{}\n".format(msg))
                self.__debug.flush()

    def ldap_link(self, username, password, mode="LOGIN"):
        # If no password provided, we will not try to authenticate
        if password:
            # Prepare LDAP connection details
            nt4_domain = settings.AD_NT4_DOMAIN.upper()
            dns_name = getattr(settings, "AD_DNS_NAME", nt4_domain).upper()
            use_ssl = getattr(settings, "AD_SSL", False)
            if use_ssl:
                default_port = 636
                proto = "ldaps"
            else:
                default_port = 389
                proto = "ldap"
            port = getattr(settings, "AD_LDAP_PORT", default_port)
            ldap_url = "{}://{}:{}".format(proto, dns_name, port)
            self.debug("ldap.initialize :: url: {}".format(ldap_url))

            # Prepare library
            ser = {}
            ser["allowed_referral_hosts"] = [("*", True)]
            con = {}
            con["user"] = r"{}\{}".format(nt4_domain, username)
            con["password"] = password
            con["raise_exceptions"] = True
            con["authentication"] = ldap3.NTLM
            if use_ssl:
                certfile = settings.AD_CERT_FILE
                self.debug(
                    "ldap.ssl :: Activated - Cert file: {}".format(certfile),
                )
                con["auto_bind"] = ldap3.AUTO_BIND_TLS_BEFORE_BIND
                ser["use_ssl"] = True
                ser["tls"] = ldap3.Tls(
                    validate=ssl.CERT_REQUIRED,
                    version=ssl.PROTOCOL_TLSv1,
                )
            else:
                con["auto_bind"] = ldap3.AUTO_BIND_NO_TLS
            try:
                # self.debug('ldap.server params :: {}'.format(ser))
                server = ldap3.Server(ldap_url, **ser)
                self.debug("ldap.server :: {}".format(server))
                # self.debug('ldap.connection params :: {}'.format(con))
                answer = ldap3.Connection(server, **con)
                self.debug("ldap.connection :: {}".format(answer))
                # answer.open()
                # answer.bind()
                self.debug("ldap.connected :: Authorized")
            except LDAPSocketOpenError as e:
                # The access for this user has been denied, Debug it
                # if required
                self.debug(
                    "LDAP connect failed 'SocketOpenError' "
                    f"for url '{ldap_url}' with error '{e}'",
                )
                answer = None
            except LDAPException as e:
                # The access for this user has been denied, Debug it
                # if required
                self.debug(
                    "LDAP connect failed 'LDAPException' "
                    f"for user '{username}' with error '{e}'",
                )
                answer = False

        else:
            # The access for this user has been denied, Debug it if required
            self.debug("No password provided for user '{}'".format(username))
            answer = False

        # Return the final result
        return answer

    def authenticate(self, *args, **kwargs):
        """
        Authenticate the user agains LDAP
        """

        # Get config
        username = kwargs.get("username", None)
        password = kwargs.get("password", None)

        # Check user in Active Directory (authorization == None if can not
        # connect to Active Directory Server)
        authorization = self.ldap_link(username, password, mode="LOGIN")

        if authorization:
            # The user was validated in Active Directory
            user = self.get_or_create_user(username, password)
            # Get or get_create_user will revalidate the new user
            if user:
                # If the user has been properly validated
                user.is_active = True
                user.save()
        else:
            # Locate user in our system
            user = User.objects.filter(username=username).first()
            if user and not user.is_staff:
                # If access was denied
                if authorization is False or getattr(
                    settings,
                    "AD_LOCK_UNAUTHORIZED",
                    False,
                ):
                    # Deactivate the user
                    user.is_active = False
                    user.save()

            # No access and no user here
            user = None

        # Return the final decision
        return user

    def get_ad_info(self, username, password):
        self.debug("get_ad_info for user '{}'".format(username))

        # Initialize the answer
        info = {}

        # Get an already authenticated link connection to LDAP
        link = self.ldap_link(username, password, mode="SEARCH")

        if link:
            # Prepare SEARCH fields
            mapping = getattr(settings, "AD_MAP_FIELDS", {})
            # Build the search fields
            search_fields = ["sAMAccountName", "memberOf"] + list(
                mapping.values(),
            )
            search_dns = (
                getattr(settings, "AD_NT4_DOMAIN", "").lower().split(".")
            )
            # Build the dn list
            search_dnlist = []
            for token in search_dns:
                search_dnlist.append("dc={}".format(token))
            search_dn = ",".join(search_dnlist)

            # Search for the user
            self.debug('Search "{}"'.format(search_dn))
            # Search in LDAP
            link.search(
                search_base=search_dn,
                # search_filter='(&(objectclass=person)(uid=admin))',
                search_filter="(sAMAccountName={})".format(username),
                search_scope=ldap3.SUBTREE,
                # attributes=ldap3.ALL_ATTRIBUTES,
                attributes=search_fields,
                get_operational_attributes=True,
                size_limit=1,
            )

            # Get all results
            results = link.entries

            # Make sure we found only one result
            if len(results) == 1:
                # Get answer
                result = results[0].__dict__

            elif len(results) > 1:
                # Found serveral results
                self.debug("I found several results for your LDAP query")
                memberships = []
            else:
                # Not found
                self.debug(
                    "I didn't find any matching result for your LDAP query",
                )
                memberships = []

            # Validate that they are a member of review board group
            memberships = result.get("memberOf", [])

            # Process all memberships found
            groups_ad = {}
            for membership in memberships:
                tokens = membership.split(",")
                dcs = []
                cn = None

                for token in tokens:
                    (key, value) = token.split("=")
                    if key == "CN":
                        if not cn:
                            cn = value
                    elif key == "DC":
                        dcs.append(value)

                # Prepare the full domain name addess of the AD
                dc = ".".join(dcs)

                # Make sure the key exists
                if dc not in groups_ad:
                    groups_ad[dc] = []

                # Add the new CN to the list
                if cn not in groups_ad[dc]:
                    groups_ad[dc].append(cn)

            # Prepare the answer
            info = {}
            info["groups"] = groups_ad

            # Look for other tokens to get mapped
            for djfield in mapping.keys():
                adfield = mapping[djfield]
                if adfield in result:
                    info[djfield] = result[adfield]
                    self.debug("{}={}".format(adfield, info[djfield]))
                else:
                    self.debug("{}=-NONE-".format(adfield))

        else:
            # No link gotten
            self.debug("I didn't get a valid link to the LDAP server")

        # Return the final result
        return info

    def get_or_create_user(self, username, password):
        """
        Get or create the given user
        """

        # Get the groups for this user
        info = self.get_ad_info(username, password)
        self.debug("INFO found: {}".format(info))

        # Find the user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User(username=username)

        # Update user
        user.first_name = info.get("first_name", "")
        user.last_name = info.get("last_name", "")
        user.email = info.get("email", "")

        # Check if the user is in the Administrators groups
        is_admin = False
        for domain in info["groups"]:
            if "Domain Admins" in info["groups"][domain]:
                is_admin = True
                break

        # Set the user permissions
        user.is_staff = is_admin
        user.is_superuser = is_admin

        # Refresh the password
        user.set_password(password)

        # Validate the selected user and gotten information
        user = self.validate(user, info)
        if user:
            self.debug("User got validated!")

            # Autosave the user until this point
            user.save()

            # Synchronize user
            self.synchronize(user, info)
        else:
            self.debug("User didn't pass validation!")

        # Finally return user
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def validate(self, user, info):
        """
        Placeholder validate system, to be redeclared
        User object here is not saved in the database, but it is ready to
        be saved
        If the answer from this method is None, user will be denied to login
        in to the system!
        """
        self.debug("Validation process!")
        return user

    def synchronize(self, user, info):
        """
        It tries to do a group synchronization if possible
        This methods should be redeclared by the developer
        """

        self.debug("Synchronize!")

        # Remove all groups from this user
        user.groups.clear()

        # For all domains found for this user
        for domain in info["groups"]:
            # For all groups he is
            for groupname in info["groups"][domain]:
                # Lookup for that group
                group = Group.objects.filter(name=groupname).first()
                if group:
                    # If found, add the user to that group
                    user.groups.add(group)
