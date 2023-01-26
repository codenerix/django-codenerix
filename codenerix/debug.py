#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

from django import VERSION

import debug_toolbar

DEBUG_TOOLBAR_DEFAULT_PANELS = (
    "debug_toolbar.panels.versions.VersionsPanel",
    "debug_toolbar.panels.timer.TimerPanel",
    "debug_toolbar.panels.settings.SettingsPanel",
    "debug_toolbar.panels.headers.HeadersPanel",
    "debug_toolbar.panels.request.RequestPanel",
    "debug_toolbar.panels.sql.SQLPanel",
    "debug_toolbar.panels.staticfiles.StaticFilesPanel",
    "debug_toolbar.panels.templates.TemplatesPanel",
    "debug_toolbar.panels.cache.CachePanel",
    "debug_toolbar.panels.signals.SignalsPanel",
    "debug_toolbar.panels.logging.LoggingPanel",
    "debug_toolbar.panels.redirects.RedirectsPanel",
    "debug_toolbar.panels.profiling.ProfilingPanel",
)
DEBUG_TOOLBAR_DEFAULT_CONFIG = {
    "INTERCEPT_REDIRECTS": False,
    # Toolbar options
    "RESULTS_CACHE_SIZE": 3,
    "SHOW_COLLAPSED": True,
    # Panel options
    "SQL_WARNING_THRESHOLD": 100,  # milliseconds
}


# Autoload
def autoload(
    INSTALLED_APPS,
    MIDDLEWARE,
    DEBUG=False,
    SPAGHETTI=False,
    ROSETTA=False,
    ADMINSITE=False,
    DEBUG_TOOLBAR=False,
    DEBUG_PANEL=False,
    SNIPPET_SCREAM=False,
    GRAPH_MODELS=False,
    CODENERIX_DISABLE_LOG=False,
    DEBUG_PYINSTRUMENT=False,
):
    EXTRA_MIDDLEWARES = []
    if DEBUG and SPAGHETTI:
        INSTALLED_APPS += ("django_spaghetti",)
    if DEBUG and ROSETTA:
        INSTALLED_APPS += ("rosetta",)
    if (
        "django.contrib.admin" not in INSTALLED_APPS
        and not CODENERIX_DISABLE_LOG
    ):
        INSTALLED_APPS += ("django.contrib.admin",)
    if DEBUG and ADMINSITE and not CODENERIX_DISABLE_LOG:
        EXTRA_MIDDLEWARES.append(
            "django.contrib.messages.middleware.MessageMiddleware"
        )
    if DEBUG and DEBUG_TOOLBAR:
        INSTALLED_APPS += ("debug_toolbar",)
        if DEBUG_PANEL:
            INSTALLED_APPS += ("debug_panel",)
            EXTRA_MIDDLEWARES.append(
                "debug_panel.middleware.DebugPanelMiddleware"
            )
        else:
            EXTRA_MIDDLEWARES.append(
                "debug_toolbar.middleware.DebugToolbarMiddleware"
            )
    if DEBUG and SNIPPET_SCREAM:
        EXTRA_MIDDLEWARES.append("snippetscream.ProfileMiddleware")
    if DEBUG and GRAPH_MODELS:
        INSTALLED_APPS += ("django_extensions",)
    if DEBUG and DEBUG_PYINSTRUMENT:
        EXTRA_MIDDLEWARES.append("pyinstrument.middleware.ProfilerMiddleware")

    # Attach new middlewares
    if type(MIDDLEWARE) == tuple:
        MIDDLEWARE += tuple(EXTRA_MIDDLEWARES)
    else:
        MIDDLEWARE += list(EXTRA_MIDDLEWARES)

    # Return final results
    return (INSTALLED_APPS, MIDDLEWARE)


# Autourl
def autourl(
    URLPATTERNS,
    DEBUG,
    ROSETTA,
    ADMINSITE,
    SPAGHETTI,
    DEBUG_TOOLBAR=False,
    DEBUG_PANEL=False,
):
    from django.conf.urls import include
    from django.urls import re_path

    if ROSETTA:
        URLPATTERNS += [re_path(r"^rosetta/", include("rosetta.urls"))]

    if ADMINSITE:
        from django.contrib import admin

        if VERSION[0] < 2 and ADMINSITE:
            URLPATTERNS += [re_path(r"^admin/", include(admin.site.urls))]
        else:
            from django.urls import path

            URLPATTERNS += [
                path(
                    "admin/",
                    admin.site.urls,
                )
            ]
    if DEBUG and SPAGHETTI:
        URLPATTERNS += [re_path(r"^plate/", include("django_spaghetti.urls"))]
    if DEBUG and DEBUG_TOOLBAR:
        URLPATTERNS += [re_path(r"^__debug__/", include(debug_toolbar.urls))]
    return URLPATTERNS


# Codenerix STATIC
def codenerix_statics(DEBUG, STATIC_URL="/static/"):

    # Backward compatibility for older configurations (CODENERIXSOURCE is deprecated from now!)
    if type(STATIC_URL) is bool:
        DEBUG = STATIC_URL
        STATIC_URL = "/static/"

    locales = '\
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.ar.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.bg.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.ca.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.cs.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.da.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.de.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.ee.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.el.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.es.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.fi.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.fr.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.he.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.hr.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.hu.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.id.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.is.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.it.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.ja.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.ko.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.lt.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.lv.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.ms.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.nb.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.nl.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.no.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.pl.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.pt-BR.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.pt.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.ro.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.rs.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.rs-latin.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.ru.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.sk.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.sl.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.sv.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.sw.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.th.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.tr.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.ua.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.uk.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.zh-CN.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.zh-TW.js"></script> '

    CODENERIX_CSS_DEBUG = ' \
    <link href="{STATIC_URL}codenerix/lib/bootstrap/css/bootstrap.css" rel="stylesheet"> \
    <link href="{STATIC_URL}djangular/css/styles.css" rel="stylesheet"> \
    <link href="{STATIC_URL}djangular/css/bootstrap3.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-bootstrap-colorpicker/css/colorpicker.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-daterangepicker/daterangepicker-bs3.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-ui/select.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-material/angular-material.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-loading-bar/loading-bar.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/css/bootstrap-datetimepicker.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/nspopover/nspopover.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/css/base.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/css/lists.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/bootstrap-vertical-grid.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/fontawesome/css/font-awesome.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/fontawesome-animation/font-awesome-animation.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/textAngular/textAngular.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-quill/quill.snow.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-hotkeys/hotkeys.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/bootstrap-switch/bootstrap-switch.css" rel="stylesheet"> \
    '
    CODENERIX_CSS_MIN = ' \
    <link href="{STATIC_URL}codenerix/lib/bootstrap/css/bootstrap.min.css" rel="stylesheet"> \
    <link href="{STATIC_URL}djangular/css/styles.css" rel="stylesheet"> \
    <link href="{STATIC_URL}djangular/css/bootstrap3.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-bootstrap-colorpicker/css/colorpicker.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-daterangepicker/daterangepicker-bs3.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-ui/select.min.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-material/angular-material.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-loading-bar/loading-bar.min.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/css/bootstrap-datetimepicker.min.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/nspopover/nspopover.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/css/base.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/css/lists.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/bootstrap-vertical-grid.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/fontawesome/css/font-awesome.min.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/fontawesome-animation/font-awesome-animation.min.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/textAngular/textAngular.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-quill/quill.snow.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-hotkeys/hotkeys.min.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/bootstrap-switch/bootstrap-switch.min.css" rel="stylesheet"> \
    '
    CODENERIX_JS_DEBUG = (
        ' \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/jquery/jquery.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/moment/moment.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap/js/bootstrap.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-dropdowns-functions.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-animate.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-aria.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-messages.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-ui/ui-bootstrap-tpls.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-ui/angular-ui-router.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-ui/select.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-ui/datetimepicker.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-resource.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-cookies.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-sanitize.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-touch.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-material/angular-material.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}djangular/js/django-angular.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-loading-bar/loading-bar.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/bootstrap-datetimepicker.js"></script> \
\
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-bootstrap-colorpicker/js/bootstrap-colorpicker-module.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-daterangepicker/daterangepicker.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-daterangepicker/angular-daterangepicker.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-checklist-model.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/color-contrast.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/nspopover/nspopover.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/notifyjs/notify.js"></script> \
    <script type="text/javascript" src="https://www.google.com/recaptcha/api.js?onload=vcRecaptchaApiLoaded&render=explicit" async defer></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-recaptcha/angular-recaptcha.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-base64-upload.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/file_validation.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/js/codenerix.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/js/notify.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/js/filters.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/js/inotify.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/textAngular/textAngular-rangy.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/textAngular/textAngular-sanitize.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/textAngular/textAngular.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-quill/quill.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-quill/ng-quill.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-hotkeys/hotkeys.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-switch/bootstrap-switch.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-bootstrap-switch/angular-bootstrap-switch.js"></script> \
    '
        + locales
    )
    CODENERIX_JS_MIN = (
        ' \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/jquery/jquery.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/moment/moment.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap/js/bootstrap.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-dropdowns-functions.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-animate.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-aria.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-messages.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-ui/ui-bootstrap-tpls.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-ui/angular-ui-router.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-ui/select.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-ui/datetimepicker.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-resource.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-cookies.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-sanitize.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-touch.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-material/angular-material.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}djangular/js/django-angular.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-loading-bar/loading-bar.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/bootstrap-datetimepicker.js"></script> <!-- .min.js FAILS! --> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-bootstrap-colorpicker/js/bootstrap-colorpicker-module.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-daterangepicker/daterangepicker.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-daterangepicker/angular-daterangepicker.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-checklist-model.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/color-contrast.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/nspopover/nspopover.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/notifyjs/notify.min.js"></script> \
    <script type="text/javascript" src="https://www.google.com/recaptcha/api.js?onload=vcRecaptchaApiLoaded&render=explicit" async defer></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-recaptcha/angular-recaptcha.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-base64-upload.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/file_validation.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/js/codenerix.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/js/notify.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/js/filters.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/js/inotify.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/textAngular/textAngular-rangy.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/textAngular/textAngular-sanitize.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/textAngular/textAngular.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-quill/quill.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-quill/ng-quill.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-hotkeys/hotkeys.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-switch/bootstrap-switch.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-bootstrap-switch/angular-bootstrap-switch.min.js"></script> \
    '
        + locales
    )

    # Load CODENERIX CSS
    if DEBUG:
        CODENERIX_CSS = CODENERIX_CSS_DEBUG
    else:
        CODENERIX_CSS = CODENERIX_CSS_MIN
    # Load CODENERIX JS
    if DEBUG:
        CODENERIX_JS = CODENERIX_JS_DEBUG
    else:
        CODENERIX_JS = CODENERIX_JS_MIN
    return (
        CODENERIX_CSS.format(STATIC_URL=STATIC_URL),
        CODENERIX_JS.format(STATIC_URL=STATIC_URL),
    )
