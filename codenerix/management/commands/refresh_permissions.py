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


from codenerix_lib.debugger import Debugger
from django.apps import apps
from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import User
from django.contrib.contenttypes.management import create_contenttypes
from django.core.management.base import BaseCommand
from providers.people.models import Person


class Command(BaseCommand, Debugger):
    # Show this when the user types help
    help = "Refresh all permissions from a project"

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            type=str,
            default="default",
            help="Nominates a database to synchronize. "
            "Defaults to the 'default' database.",
        )

    def handle(self, *args, **options):
        # Get database
        db = options["database"]

        # Autoconfigure Debugger
        self.set_name("CODENERIX")
        self.set_debug()
        self.debug(f"Settings permissions for '{db}':", color="blue")

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
            create_permissions(app_config, apps=apps, verbosity=0, using=db)
            idx += 1

        # Update contenttypes
        self.debug("Updating Content Types", color="blue")
        idx = 1
        for app_config in apps_config:
            self.debug(
                "    -> {}/{} {}".format(idx, apps_total, app_config.label),
                color="cyan",
            )
            create_contenttypes(app_config, using=db)
            idx += 1

        # Get all users from the system
        self.debug("Refreshing users permissions", color="blue")
        person = None
        for user in User.objects.using(db).all():
            self.debug(
                f"    > {user.username} ",
                color="cyan",
                tail=False,
            )
            if hasattr(user, "person") and user.person:
                self.debug(
                    "OK",
                    color="green",
                    head=False,
                )
                user.person.refresh_permissions(using=db)
                person = user.person
            else:
                self.debug(
                    "NO PERSON",
                    color="red",
                    head=False,
                )

        # Remake groups permissions if we have at least one valid user
        if person:
            self.debug(
                "Refreshing group permissions "
                "(it may takes over a minute)... ",
                color="blue",
                tail=False,
            )
            Person.group_permissions(Person, using=db)
            self.debug("DONE", color="green", head=False)
        else:
            self.debug(
                "Can not refresh group permissions because I didn't "
                "find a user with a Person",
                color="red",
            )
