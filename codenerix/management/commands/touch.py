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
from pathlib import Path

from codenerix_lib.debugger import Debugger
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand, Debugger):
    # Show this when the user types help
    help = "Do a touch to the project"

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            "-f",
            action="store_true",
            dest="f",
            default=False,
            help="Keep the command working forever",
        )

        # Named (optional) arguments
        parser.add_argument(
            "--follow",
            action="store_true",
            dest="follow",
            default=False,
            help="Keep the command working forever",
        )

    def handle(self, *args, **options):
        # Autoconfigure Debugger
        self.set_name("CODENERIX")
        self.set_debug()

        # Get environment
        appname = settings.ROOT_URLCONF.split(".")[0]
        basedir = settings.BASE_DIR
        appdir = os.path.abspath(f"{basedir}/{appname}")

        # While keep working
        keepworking = True
        while keepworking:
            # Collect
            self.debug("Collecting...", color="blue")
            cmd = [f"{appdir}/manage", "collectstatic", "--noinput"]
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            status, output = result.returncode, result.stdout.rstrip("\n")
            if status:
                raise CommandError(f"{output}\nCommand was: {' '.join(cmd)}")
            for line in output.split("\n"):
                if line[0:7] == "Copying":
                    path = line.split("'")[1].replace(appdir, ".")
                    self.debug(f"    > {path}")
                elif ("static file copied to" in line) or ("static files copied to" in line):
                    done = line.split(" ")[0]
                    linesp = line.split(",")
                    if len(linesp) == 1:
                        total = linesp[0].split(" ")[0]
                    else:
                        total = linesp[1].split(" ")[1]
                    self.debug(
                        f"{done}/{total} files copied",
                        color="cyan",
                    )
                elif (
                    "was already registered. Reloading models is not advised "
                    "as it can lead to inconsistencies, most notably with "
                    "related models." in line
                ):
                    pass
                elif (
                    "new_class._meta.apps.register_model(new_class._meta.app_label, new_class)"  # noqa: E501
                    in line
                ):
                    pass
                elif line == "":
                    pass
                else:
                    self.warning(f"Unknown string: #{line}#")

            # Clean
            self.debug("Cleaning...", color="blue")
            cmd = [f"{appdir}/manage", "clean"]
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            status, output = result.returncode, result.stdout.rstrip("\n")
            if status:
                raise CommandError(f"{output}\nCommand was: {' '.join(cmd)}")

            # Touch
            self.debug("Touch...", color="blue", tail=False)
            filenames = os.listdir(appdir)
            filenames.sort()
            for name in filenames:
                if name[0:4] == "wsgi" or name[-4:] == "wsgi":
                    try:
                        Path(appdir, name).touch()
                    except OSError as e:
                        raise CommandError(f"{e}\nTouching: {appdir}/{name}") from e

            self.debug(" Done", color="green", header=False)

            if options["follow"] or options["f"]:
                # Ask the user if would really like to remove all
                # locale folders
                self.debug(
                    "Hit a ENTER when ready to go or Q to exit (ENTER|q) ",
                    tail=False,
                    color="purple",
                )
                try:
                    key = input().lower()
                except KeyboardInterrupt:
                    self.debug(" ", header=False)
                    key = "q"
                self.debug("", header=False)
                self.debug(" ")
                if key == "q":
                    self.debug("Quitting!", color="yellow")
                    keepworking = False
            else:
                self.debug("Quitting!", color="yellow")
                keepworking = False
