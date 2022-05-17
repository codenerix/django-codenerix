# -*- coding: utf-8 -*-
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
    from subprocess import getstatusoutput
    pythoncmd="python3"
except:
    from commands import getstatusoutput
    pythoncmd="python2"

from django.core.management.base import BaseCommand, CommandError

from codenerix.lib.debugger import Debugger

class Command(BaseCommand, Debugger):

    # Show this when the user types help
    help = "Clean memcache"
    
    def handle(self, *args, **options):
        
        # Autoconfigure Debugger
        self.set_name("CODENERIX")
        self.set_debug()
        
        # Get environment
        status, output = getstatusoutput("echo 'flush_all' | nc localhost 11211")
        if status: raise CommandError(output)

