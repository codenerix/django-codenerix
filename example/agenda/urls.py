from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views

from base import urls as base_urls
from base.views import home, alarms, status
from agenda.settings import autourl


urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),

    url('^$', home, name='home'),
    url('^alarmspopups$', alarms, name='alarms'),
    url(r'^status/(?P<status>\w+)/(?P<answer>[a-zA-Z0-9+/]+)$', status, name='status'),
    url(r'^login/$', auth_views.login, name='login'),
    url(r'^logout/$', auth_views.logout, name='logout'),

    url(r'^base/', include(base_urls)),
]

urlpatterns = autourl(urlpatterns)
