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

import os
import shlex
import subprocess

from codenerix_lib.debugger import Debugger
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand, Debugger):
    # Show this when the user types help
    help = "Remove *.pyc files"

    def handle(self, *args, **options):
        # Autoconfigure Debugger
        self.set_name("CODENERIX")
        self.set_debug()

        # Get environment
        appname = settings.ROOT_URLCONF.split(".")[0]
        basedir = settings.BASE_DIR
        appdir = os.path.abspath(f"{basedir}/{appname}")
        cmd = [
            "find",
            f"{appdir}/",
            "-name",
            "*.py[c|o]",
            "-o",
            "-name",
            "__pycache__",
            "-exec",
            "rm",
            "-rf",
            "{}",
            "+",
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        status, output = result.returncode, result.stdout.rstrip("\n")
        if status:
            raise CommandError(f"{output}\nCommand was: {shlex.join(cmd)}")
