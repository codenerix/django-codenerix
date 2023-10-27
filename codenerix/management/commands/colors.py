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

try:
    from subprocess import getstatusoutput

    pythoncmd = "python3"
except Exception:
    from commands import (  # type: ignore[import-not-found,no-redef]
        getstatusoutput,
    )

    pythoncmd = "python2"

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from codenerix.lib.colors import colors
from codenerix.lib.debugger import Debugger


class Command(BaseCommand, Debugger):
    # Show this when the user types help
    help = "Show colors for Debugger"

    def handle(self, *args, **options):
        # Autoconfigure Debugger
        self.set_name("CODENERIX")
        self.set_debug()

        # Reorder colors
        keys = []
        for key in colors.keys():
            keys.append((colors[key][0], colors[key][1], key))
        keys.sort()

        # Show up all colors
        for color in keys:
            # Get the color information
            (simplebit, subcolor) = colors[color[2]]
            # Show it
            print(
                "{:1d}:{:02d} - \033[{:1d};{:02d}m{:<14s}\033[1;00m{:<s}".format(  # noqa: E501
                    simplebit,
                    subcolor,
                    simplebit,
                    subcolor,
                    color[2],
                    color[2],
                ),
            )

            # Get environment
            appname = settings.ROOT_URLCONF.split(".")[0]
            basedir = settings.BASE_DIR
            appdir = os.path.abspath("{}/{}".format(basedir, appname))
            status, output = getstatusoutput(
                "find {}/ -type f -name '*.pyc' -delete".format(appdir),
            )
            if status:
                raise CommandError(output)
