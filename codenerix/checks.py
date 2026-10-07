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

from codenerix.debug import debug_toolbar_access_errors


def check_debug_toolbar_access(
    app_configs: Sequence[AppConfig] | None,
    **kwargs: Any,
) -> list[CheckMessage]:
    """Report unsafe or malformed DEBUG_TOOLBAR_ALLOWED_IPS settings.

    show_toolbar() already fails closed on these; this makes the cause visible
    on runserver and on any management command (e.g. `manage.py check --deploy`).
    """
    return [Error(message, id="codenerix.E001") for message in debug_toolbar_access_errors()]
