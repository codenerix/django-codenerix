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


from django.apps import apps
from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import User
from django.contrib.contenttypes.management import create_contenttypes
from django.core.management.base import BaseCommand

from codenerix.lib.debugger import Debugger


class Command(BaseCommand, Debugger):
    # Show this when the user types help
    help = "Refresh all permissions from a project"

    def handle(self, *args, **options):
        # Autoconfigure Debugger
        self.set_name("CODENERIX")
        self.set_debug()
        self.debug("Settings permissions for:", color="blue")

        # Get list of apps
        self.debug("Getting list of APPs", color="blue")
        apps_config = apps.get_app_configs()
        apps_total = len(apps_config)

        # Create missins permissions
        self.debug("Creating missing permissions", color="blue")
        idx = 1
        for app_config in apps_config:
            self.debug(
                "    -> {}/{} {}".format(idx, apps_total, app_config.label),
                color="cyan",
            )
            create_permissions(app_config, apps=apps, verbosity=0)
            idx += 1

        # Update contenttypes
        self.debug("Updating Content Types", color="blue")
        idx = 1
        for app_config in apps_config:
            self.debug(
                "    -> {}/{} {}".format(idx, apps_total, app_config.label),
                color="cyan",
            )
            create_contenttypes(app_config)
            idx += 1

        # Get all users from the system
        person = None
        for user in User.objects.all():
            self.debug(
                f"    > {user.username} ",
                color="cyan",
                tail=None,
            )
            if hasattr(user, "person") and user.person:
                self.debug(
                    "OK",
                    color="green",
                    header=None,
                )
                user.person.refresh_permissions()
                person = user.person
            else:
                self.debug(
                    "NO PERSON",
                    color="red",
                    header=None,
                )

        # Remake groups permissions if we have at least one valid user
        if person:
            self.debug(
                "Refreshing group permissions "
                "(it may takes over a minute)... ",
                color="blue",
                tail=None,
            )
            person.__class__.group_permissions(person.__class__)
            self.debug("DONE", color="green", header=None)
        else:
            self.debug(
                "Can not refresh group permissions because I didn't "
                "find a user with a Person",
                color="red",
            )
