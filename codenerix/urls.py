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

from django.urls import re_path

from codenerix.views import (
    LogDetails,
    LogList,
    RemoteLogCreate,
    RemoteLogDetails,
    RemoteLogList,
    status,
)

urlpatterns = [
    # Backward compatibility
    re_path(
        r"^status/(?P<status>\w+)/(?P<answer>[a-zA-Z0-9+-_/]+)$",
        status,
        name="status",
    ),
    re_path(r"^logs$", LogList.as_view(), name="codenerix_log_list"),
    re_path(
        r"^logs/(?P<pk>\w+)$",
        LogDetails.as_view(),
        name="codenerix_log_details",
    ),
    re_path(
        r"^status/(?P<status>\w+)/(?P<answer>[a-zA-Z0-9+-_/]+)$",
        status,
        name="CDNX_status",
    ),
    re_path(r"^logs$", LogList.as_view(), name="CDNX_codenerix_log_list"),
    re_path(
        r"^logs/(?P<pk>\w+)$",
        LogDetails.as_view(),
        name="CDNX_codenerix_log_details",
    ),
    re_path(
        r"^remotelogs$",
        RemoteLogList.as_view(),
        name="CDNX_remotelog_list",
    ),
    re_path(
        r"^remotelogs/add$",
        RemoteLogCreate.as_view(),
        name="CDNX_remotelog_create",
    ),
    re_path(
        r"^remotelogs/(?P<pk>\w+)$",
        RemoteLogDetails.as_view(),
        name="CDNX_remotelog_details",
    ),
]
