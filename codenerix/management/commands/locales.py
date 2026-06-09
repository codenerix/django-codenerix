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

import glob
import os
import subprocess

from codenerix_lib.debugger import Debugger
from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand, Debugger):
    # Show this when the user types help
    help = "Used to build all locales details"

    def add_arguments(self, parser):
        # Set witch mode to use
        parser.add_argument(
            "--mode",
            dest="mode",
            default="suexec",
            help="Mode used in the environment 'suexec', 'apache' or 'wwwdata'",
        )

        # Named (optional) arguments
        parser.add_argument(
            "--noauto",
            action="store_true",
            dest="noauto",
            default=False,
            help="Tells the command not to find automatic solution for problems",
        )

        # Named (optional) arguments
        parser.add_argument(
            "--noguess",
            action="store_true",
            dest="noguess",
            default=False,
            help="Disable guessing user environment",
        )

        # Named (optional) arguments
        parser.add_argument(
            "--clean",
            action="store_true",
            dest="clean",
            default=False,
            help="Do a full clean by deleting everything before building translations",
        )

        # Named (optional) arguments
        parser.add_argument(
            "--compile",
            action="store_true",
            dest="compile",
            default=False,
            help="Compile .po files",
        )

    def handle(self, *args, **options):
        # Check arguments
        mode = options["mode"]
        if mode not in ["wwwdata", "apache", "suexec"]:
            self.print_help("", "")
            raise CommandError(
                "Allowed modes are suexec, apache or wwwdata ('apache' and "
                "'wwwdata' option will force permissions to apache or "
                "www-data user, suexec won't touch permissions)",
            )

        # Autoconfigure Debugger
        self.set_name("CODENERIX")
        self.set_debug()

        # Get environment
        appname = settings.ROOT_URLCONF.split(".")[0]
        basedir = settings.BASE_DIR
        appdir = os.path.abspath(f"{basedir}/{appname}")
        noauto = options["noauto"]

        # Check user selection
        if not options["noguess"]:
            result = subprocess.run(
                ["find", appdir, "-name", "locale", "-exec", "ls", "-lR", "{}", ";"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            guess = "wwwdata" if "www-data" in result.stdout else "suexec"
            if guess != mode:
                self.print_help("", "")
                raise CommandError(
                    f"You have selected mode '{mode}' but I believe you are "
                    "using '{guess}', if sure use --noguess",
                )

        # Show header
        self.debug(f"Creating locales for {appname}", color="blue")
        if noauto:
            self.debug("Autoconfig mode is OFF", color="yellow")

        # Get a list of all apps belonging to this project
        installed_apps = []
        for app_config in apps.get_app_configs():
            # print(f"App Name: {app_config.name}")
            # print(f"  - Verbose Name: {app_config.verbose_name}")
            # print(f"  - Path: {app_config.path}")
            # print("-" * 10)
            if app_config.name.split(".")[0] == appname:
                installed_apps.append(".".join(app_config.name.split(".")[1:]))

        # Check for locale folders
        error = False
        for app in [""] + installed_apps:
            testpath = os.path.abspath(
                f"{appdir}/{app}/locale".replace("//", "/"),
            )
            if not os.path.exists(testpath):
                if noauto:
                    error = True
                    self.debug(
                        f"'locale' folder missing at {testpath}/",
                        color="yellow",
                    )
                else:
                    self.debug(
                        f"'locale' folder missing, creating {testpath}/",
                        color="purple",
                    )
                    os.mkdir(testpath)

        if error:
            raise CommandError(
                "Some error has happened, can not keep going! (avoid "
                "using --noauto to let CODENERIX find a solution)",
            )

        # Check execution mode
        sudo = ""
        if mode in ("apache", "wwwdata"):
            result = subprocess.run(
                ["whoami"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            status, output = result.returncode, result.stdout.rstrip("\n")
            if status:
                # Error in command
                self.error("Error while executing 'whoami' command")
                raise CommandError(output)
            if output == "www-data":
                # Detected we are already www-data user, so keep going
                self.debug("Detected we are 'www-data' user", color="purple")
            else:
                # No permissions try to become root using sudo
                result = subprocess.run(
                    ["sudo", "whoami"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )
                status, output = result.returncode, result.stdout.rstrip("\n")
                if status:
                    # Error in command
                    self.error("Error while executing 'sudo whoami' command")
                    raise CommandError(output)
                if output == "root":
                    # Detected sudo is working and we can become root
                    self.debug(
                        "Detected we can become 'root' user",
                        color="purple",
                    )
                    sudo = "sudo "
                else:
                    # No permissions
                    raise CommandError(
                        "You requested 'apache' or 'wwwdata' execution mode "
                        "but you are not www-data and we can not become root",
                    )

        # Delete locale folders if requested
        if options["clean"]:
            # Ask the user if would really like to remove all locale folders
            key = ""
            while key not in ["n", "y"]:
                self.debug(
                    "All 'locale' folders are going to be removed, are you sure? (y|n) ",
                    tail=False,
                    color="red",
                )
                key = input().lower()
                self.debug("", header=False)

            # Remove all locale folders
            if key == "y":
                self.debug("Removing locale folders...", color="red")
                for app in [""] + installed_apps:
                    testpath = os.path.abspath(
                        f"{appdir}/{app}/locale".replace("//", "/"),
                    )
                    if os.path.exists(testpath):
                        self.debug(
                            f"    > Removing {testpath}",
                            color="red",
                        )
                        entries = glob.glob(f"{testpath}/*")
                        if entries:
                            result = subprocess.run(
                                (["sudo"] if sudo else []) + ["rm", "-R", *entries],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True,
                                check=False,
                            )
                            status, output = (
                                result.returncode,
                                result.stdout.rstrip("\n"),
                            )
                            if status:
                                raise CommandError(output)
            else:
                raise CommandError(
                    "You requested to clean all 'locale' folders but "
                    "you answered NO to the previous question, can not "
                    "keep going!",
                )

        # Ready to go
        if not options["compile"]:
            for code, name in settings.LANGUAGES:
                self.debug(
                    f"Processing translations for {name}...",
                    color="cyan",
                )
                result = subprocess.run(
                    (["sudo"] if sudo else [])
                    + [
                        f"{basedir}/manage.py",
                        "makemessages",
                        "-v0",
                        "--symlinks",
                        "--ignore",
                        "env",
                        "-l",
                        code,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )
                status, output = result.returncode, result.stdout.rstrip("\n")
                if status:
                    raise CommandError(output)

                result = subprocess.run(
                    (["sudo"] if sudo else [])
                    + [
                        f"{basedir}/manage.py",
                        "makemessages",
                        "-v0",
                        "--symlinks",
                        "--ignore",
                        "env",
                        "-d",
                        "djangojs",
                        "-l",
                        code,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )
                status, output = result.returncode, result.stdout.rstrip("\n")
                if status:
                    raise CommandError(output)

        # Set permissions for locale folders
        if sudo:
            self.debug("Setting permissions...", color="cyan")
            if mode == "apache":
                user = "apache"
            elif mode == "wwwdata":
                user = "www-data"
            else:
                raise CommandError(f"Wrong mode for sudo '{mode}'")
            for app in [""] + installed_apps:
                testpath = os.path.abspath(
                    f"{appdir}/{app}/locale".replace("//", "/"),
                )
                result = subprocess.run(
                    ["sudo", "chown", f"{user}.{user}", "-R", f"{testpath}/"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )
                status, output = result.returncode, result.stdout.rstrip("\n")
                if status:
                    raise CommandError(output)
