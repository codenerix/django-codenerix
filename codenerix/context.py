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

from uuid import uuid4

from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from codenerix import __version__


def codenerix(request):
    """
    Codenerix CONTEXT
    """
    # Get values
    DEBUG = getattr(settings, "DEBUG", False)  # noqa: N806
    VERSION = getattr(  # noqa: N806
        settings,
        "VERSION",
        _(
            "WARNING: No version set to this code, "
            "add VERSION contant to your configuration",
        ),
    )

    # Set environment
    return {
        "DEBUG": DEBUG,
        "VERSION": VERSION,
        "CODENERIX_VERSION": __version__,
        "CODENERIX_UUID": str(uuid4()),
    }


def codenerix_js(request):
    cnf = {}

    # Get values
    CONNECTION_ERROR = getattr(  # noqa: N806
        settings,
        "CONNECTION_ERROR",
        None,
    )
    USER_BEHAVIOUR = getattr(settings, "USER_BEHAVIOUR", None)  # noqa: N806
    ALARMS_LOOPTIME = getattr(settings, "ALARMS_LOOPTIME", None)  # noqa: N806
    ALARMS_QUICKLOOP = getattr(  # noqa: N806
        settings,
        "ALARMS_QUICKLOOP",
        None,
    )
    ALARMS_ERRORLOOP = getattr(  # noqa: N806
        settings,
        "ALARMS_ERRORLOOP",
        None,
    )
    DEBUG = getattr(settings, "DEBUG", False)  # noqa: N806
    DATERANGEPICKER_OPTIONS = getattr(  # noqa: N806
        settings,
        "DATERANGEPICKER_OPTIONS",
        None,
    )
    DATETIME_RANGE_FORMAT = getattr(  # noqa: N806
        settings,
        "DATETIME_RANGE_FORMAT",
        None,
    )

    # Set values
    if USER_BEHAVIOUR is not None:
        cnf["user_behaviour"] = USER_BEHAVIOUR is True
    if CONNECTION_ERROR is not None:
        cnf["connection_error"] = CONNECTION_ERROR
    if ALARMS_LOOPTIME is not None:
        cnf["alarms_looptime"] = ALARMS_LOOPTIME
    if ALARMS_QUICKLOOP is not None:
        cnf["alarms_quickloop"] = ALARMS_QUICKLOOP
    if ALARMS_ERRORLOOP is not None:
        cnf["alarms_errorloop"] = ALARMS_ERRORLOOP
    cnf["debug"] = str(DEBUG).lower()
    cnf["session_cookie_age"] = getattr(settings, "SESSION_COOKIE_AGE", None)
    cnf["codenerix_css"] = getattr(
        settings,
        "CODENERIX_CSS",
        _("WARNING: CODENERIX_CSS is not set in your configuration!!!"),
    )
    cnf["codenerix_js"] = getattr(
        settings,
        "CODENERIX_JS",
        _("WARNING: CODENERIX_JS is not set in your configuration!!!"),
    )

    # Set daterange
    if (DATERANGEPICKER_OPTIONS is None) or (DATETIME_RANGE_FORMAT is None):
        daterangepicker = '"'
        if DATERANGEPICKER_OPTIONS is None:
            daterangepicker += "{}".format(
                _(
                    " WARNING: DATERANGEPICKER_OPTIONS is not "
                    "set in your configuration!!! ",
                ),
            )
        if DATETIME_RANGE_FORMAT is None:
            daterangepicker += "{}".format(
                _(
                    " WARNING: DATETIME_RANGE_FORMAT is not "
                    "set in your configuration!!! ",
                ),
            )
        daterangepicker += '"'
        cnf["daterangepicker"] = mark_safe(daterangepicker)
    else:
        cnf["daterangepicker"] = mark_safe(
            settings.DATERANGEPICKER_OPTIONS.format(
                Format=settings.DATETIME_RANGE_FORMAT[1],
                From=_("From"),
                To=_("To"),
                Apply=_("Apply"),
                Cancel=_("Cancel"),
                Su=_("Su"),
                Mo=_("Mo"),
                Tu=_("Tu"),
                We=_("We"),
                Th=_("Th"),
                Fr=_("Fr"),
                Sa=_("Sa"),
                January=_("January"),
                February=_("February"),
                March=_("March"),
                April=_("April"),
                May=_("May"),
                June=_("June"),
                July=_("July"),
                August=_("August"),
                September=_("September"),
                October=_("October"),
                November=_("November"),
                December=_("December"),
            ),
        )
    # Return environment
    return {"cnf": cnf}
