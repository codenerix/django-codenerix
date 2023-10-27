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

    pythoncmd = "python3"
except Exception:
    from commands import (  # type: ignore[import-not-found,no-redef]
        getstatusoutput,
    )

    pythoncmd = "python2"

from django.conf import settings
from django.core.management.base import BaseCommand

from codenerix.lib.debugger import Debugger


class Command(BaseCommand, Debugger):
    # Show this when the user types help
    help = "Clean memcache"

    def handle(self, *args, **options):
        # Autoconfigure Debugger
        self.set_name("CODENERIX")
        self.set_debug()

        for name, cache in settings.CACHES.items():
            if "memcache" in cache.get("BACKEND", ""):
                location = cache["LOCATION"]
                locationsp = location.split(":")
                if len(locationsp) == 1:
                    host = locationsp[0]
                    port = 11211
                else:
                    host = locationsp[0]
                    port = locationsp[1]
                self.debug(
                    "Flushing all keys for "
                    f"{name}@Memcache located at {host}:{port}",
                    color="blue",
                )
                # Get environment
                status, output = getstatusoutput(
                    f"echo 'flush_all' | nc -v -w 1 {host} {port}",
                )
                if status:
                    self.debug(
                        f"ERROR at {name}@Memcache -> {output}",
                        color="red",
                    )
                else:
                    self.debug(
                        f"OK at {name}@Memcache located "
                        f"at {host}:{port} -> {output}",
                        color="green",
                    )
