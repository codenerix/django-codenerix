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

from django.core.management.base import BaseCommand

from codenerix.lib.debugger import Debugger

try:
    from subprocess import getstatusoutput
    pythoncmd="python3"
except:
    from commands import getstatusoutput
    pythoncmd="python2"

class Command(BaseCommand, Debugger):
    
    # IDENTS
    packages = {
            'KERNEL':       'django-codenerix',
            'PAYMENTS':     'django-codenerix-payments',
            'TRANSPORTS':   'django-codenerix-transports',
            'PQPROCLIENT':  'django-codenerix-pqpro-client',
            'PQPROSERVER':  'django-codenerix-pqpro-server',
            'EXTENSIONS':   'django-codenerix-extensions',
            'INVOICING':    'django-codenerix-invoicing',
            'PRODUCTS':     'django-codenerix-products',
            'SLIDER':       'django-codenerix-slider',
            'STORAGES':     'django-codenerix-storages',
        }
    
    # Dependencies
    imports = [
            #("bcrypt",                          "import bcrypt"),
            ("bson",                            "from bson import json_util"),
            ("django-angular==0.8.4",           "from djng.forms.angular_base import TupleErrorList"),
            #("Crypto.Cipher",                   "from Crypto.Cipher import AES"),
            #("cryptography",                    "import cryptography"),
            ("dateutil",                        "from dateutil.tz import tzutc"),
            ("django-multi-email-field==0.5",   "from multi_email_field.forms import MultiEmailField", "pip install git+https://github.com/fle/django-multi-email-field.git"),
            ("django-recaptcha",                "from captcha import client"),
            ("django-rosetta",                  "import rosetta"),
            ("jsonfield",                       "import jsonfield"),
            ("ldap3",                           "import ldap3"),
            ("openpyxl==2.2.5",                 "import openpyxl"),
            #("paypalrestsdk",                   "import paypalrestsdk"),
            ("Pillow",                          "import PIL"),
            #("pycrypto==2.6.1",                 "from Crypto.Cipher import AES"),
            ("python-dateutil",                 "import dateutil.parser"),
            #("scipy",                           "import scipy"),
            ("Unidecode",                       "from unidecode import unidecode"),
            ("xhtml2pdf",                       "import xhtml2pdf", "git clone https://github.com/xhtml2pdf/xhtml2pdf - and, python2 setup.py install or python3 setup.py install - sudo apt-get remove python-setuptools - wget https://bootstrap.pypa.io/get-pip.py - sudo -H python get-pip.py - sudo -H pip install -U pip setuptools"),
            ]
    
    # Show this when the user types help
    help = "Do a touch to the project"
    
    def handle(self, *args, **options):
        
        # Autoconfigure Debugger
        self.set_name("CODENERIX")
        self.set_debug()
        self.check_dependencies()
    
    def check_dependencies(self):
        self.debug("Checking all libraries required for CODENERIX to work:",color='cyan')
        
        # Django Angular
        for entry in self.imports:
            if len(entry)==2:
                (name,command)=entry
                helptext=None
            else:
                (name,command,helptext)=entry
            self.debug("    > {:32s} :: ".format(name),color='blue', tail=None),
            error, output = getstatusoutput("{} -c '{}' 2>&1".format(pythoncmd,command))
            if not error:
                # Library test passed, check version
                package = name.split("=")[0]
                error, output = getstatusoutput("pip freeze | grep -e '^{}=' || echo 'EMPTY'".format(package))
                if not error:
                    if output=='EMPTY':
                        self.debug("OK",color='green', header=None, tail=None)
                        self.debug(" (BUILT-IN)",color='purple', header=None)
                    elif "error" in output.lower():
                        self.debug("ERROR - OUTPUT WAS:\n".format(name),color='red', header=None, tail=None)
                        if output.split("\n")[-1]=='EMPTY':
                            output = "\n".join(output.split("\n")[0:-1])
                        self.debug(output,color='white', header=None)
                    else:
                        if output<name:
                            self.debug("OLDER".format(name),color='yellow', header=None, tail=None)
                            if helptext:
                                self.debug(" - HELP FOR YOU: {}".format(helptext),color='white', header=None, tail=None)
                            self.debug(" ",header=None)
                        else:
                            self.debug("OK".format(name),color='green', header=None)
                else:
                    self.debug("ERROR while looking for the package in PIP for '{}'".format(name),color='red')
                    self.debug(" -> Test: pip freeze | grep -e '^{}=' || echo 'EMPTY'".format(package),color='yellow')
                    self.debug("pip freeze | grep '{}' || echo 'EMPTY'".format(name))
                    self.error(error)
                    self.debug("OUTPUT: {}".format(output))
                    if helptext:
                        self.debug("HELP FOR YOU: {}".format(helptext))
                    print
            else:
                self.debug("MISSING or wrong version for '{}'".format(name),color='red')
                self.debug(" -> Test: {}".format(command),color='yellow')
                self.debug("{} -c '{}'".format(pythoncmd,command))
                self.error(error)
                self.debug("OUTPUT: {}".format(output))
                self.debug("")

