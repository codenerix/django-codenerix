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

from collections.abc import Sequence
from typing import Any

from django.apps import AppConfig
from django.core.checks import CheckMessage, Error

from codenerix.debug import debug_access_checks


def check_debug_access(
    app_configs: Sequence[AppConfig] | None,
    **kwargs: Any,
) -> list[CheckMessage]:
    """Report unsafe, malformed or removed debug access settings (E001), debug
    tools placed behind the page cache middlewares (E002), a page cache that
    debug requests would not bypass (E003), a toolbar callback that ignores
    DEBUG_ALLOWED_IPS (E004) and more than one middleware of a debug tool (E005).

    The debug gates already fail closed on these; this makes the cause visible
    on runserver and on any management command (e.g. `manage.py check --deploy`).
    """
    return [Error(message, id=check_id) for check_id, message in debug_access_checks()]
