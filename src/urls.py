# -*- coding: utf-8 -*-
#
# django-codenerix
#
# Copyright 2017 Centrologic Computational Logistic Center S.L.
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

from django.conf.urls import url

from codenerix.views import LogList, LogDetails, status

urlpatterns = [
    url(r'^status/(?P<status>\w+)/(?P<answer>[a-zA-Z0-9+-/]+)$', status, name='status'),
    url(r'^logs$', LogList.as_view(), name='codenerix_log_list'),
    url(r'^logs/(?P<pk>\w+)$', LogDetails.as_view(), name='codenerix_log_details'),
]
