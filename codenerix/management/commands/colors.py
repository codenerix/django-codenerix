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
import subprocess

from codenerix_lib.colors import colors
from codenerix_lib.debugger import Debugger
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand, Debugger):
    # Show this when the user types help
    help = "Show colors for Debugger"

    def handle(self, *args, **options):
        # Autoconfigure Debugger
        self.set_name("CODENERIX")
        self.set_debug()

        # Reorder colors
        keys = []
        for key, color in colors.items():
            keys.append((color[0], color[1], key))
        keys.sort()

        # Show up all colors
        for color in keys:
            # Get the color information
            simplebit, subcolor = colors[color[2]]
            # Show it
            print(
                f"{simplebit:1d}:{subcolor:02d} - "
                f"\033[{simplebit:1d};{subcolor:02d}m{color[2]:<14s}"
                f"\033[1;00m{color[2]:<s}",
            )

            # Get environment
            appname = settings.ROOT_URLCONF.split(".")[0]
            basedir = settings.BASE_DIR
            appdir = os.path.abspath(f"{basedir}/{appname}")
            result = subprocess.run(
                ["find", f"{appdir}/", "-type", "f", "-name", "*.pyc", "-delete"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            status, output = result.returncode, result.stdout.rstrip("\n")
            if status:
                raise CommandError(output)
