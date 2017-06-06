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

'''
Base library to handle CODENERIX system
'''

# System
import os
import base64
import re
import time
import json
import datetime
import calendar
import hashlib
import string
import random

# Django
from django.db import models
from django.views.generic import View
from django.views.generic import ListView
from django.forms.models import model_to_dict
from django.utils.translation import ugettext as _  # Before it was , ugettext_lazy as __
from django.utils.encoding import smart_text
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import redirect, get_object_or_404
from django.utils.translation import string_concat, gettext
from django.core.exceptions import ImproperlyConfigured
from django.core import serializers
from django.http import HttpResponse, HttpResponseForbidden, Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.core.urlresolvers import reverse_lazy, resolve, reverse
from django.utils.http import urlsafe_base64_encode
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.utils import formats
from django.http import QueryDict
from django.utils.translation import get_language

from django.conf import settings

from django.db.models import Q, F, FieldDoesNotExist
from django.utils.http import urlsafe_base64_decode

# Export to Excel
from openpyxl import Workbook

from codenerix.helpers import epochdate, monthname, get_static, get_template, get_profile, model_inspect, get_class, remove_getdisplay, daterange_filter
from codenerix.templatetags_lists import unlist


def status(request, status, answer):
    answerjson = urlsafe_base64_decode(answer)
    status = status.lower()
    if status == 'accept':
        out=202     # Accepted
    else:
        out=501     # Not Implemented
    return HttpResponse(answerjson, status=out)


# Get rightnow value
def grv(struct, position):
    '''
    This function helps to convert date information for showing proper filtering
    '''
    if position == 'year':
        size = 4
    else:
        size = 2

    if (struct[position][2]):
        rightnow = str(struct[position][0]).zfill(size)
    else:
        if position == 'year':
            rightnow = '____'
        else:
            rightnow = '__'
    return rightnow


def pages(paginator, current):
    # Get the range of pages
    p = paginator.page_range
    # Get first and last
    first = p[0]
    last = p[-1]
    total = (last - first) - 2
    if total == 0:
        total = 1
    holes = 10
    radio = 3

    # Build center
    ini = current - radio
    end = current + radio + 1
    if ini < first:
        ini = first
    if end > last:
        end = last
    try:
        center = xrange(ini, end)
    except NameError:
        center = range(ini, end)

    # Build the list of pages
    pages = []
    # Add the firstpage
    pages.append(first)

    # Decide block size
    ini_block = int( holes * current / total )
    end_block = holes - ini_block
    # Calculate grains
    if ini_block > 0:
        ini_grain = float(ini - first) / ini_block
    else:
        ini_grain = 0.0
    if end_block > 0:
        end_grain = float(last - end) / end_block
    else:
        end_grain = 0.0
    # Fill blocks
    page = first
    ref = page
    try:
        range_border = xrange(0, ini_block)
    except NameError:
        range_border = range(0, int(ini_block))
    for i in range_border:
        # Calculate if new grain will cross the border
        if ref + ini_grain < ini:
            ref += ini_grain
            newpage = int(round(ref))
            if (newpage > page) and (newpage < ini):
                page = newpage
                pages.append(page)
        else:
            break
    for page in center:
        if (page > first) and (page < last):
            pages.append(page)

    ref = page
    try:
        cross_border = xrange(0, end_block)
    except NameError:
        cross_border = range(0, int(end_block))
    for i in cross_border:
        # Calculate if new grain will cross the border
        if ref + end_grain < last:
            ref += end_grain
            newpage = int(round(ref))
            if (newpage > page) and (newpage < last):
                page = newpage
                pages.append(page)
        else:
            break

    # Add the last page
    if last != page:
        pages.append(last)

    # Return the list of pages
    return pages


class MODELINFO:
    '''
    This is a special class that hodls information to be given to the GenList special methods
    when they request it, but it can also request special methods is self.

    Usage of each special method:
    - __fields__(self,info): except you return a list with a optional tuple between 2 and 5 elements where:
            ('key',_('Name')[,lenght_in_pixels[,'alignment'[,'filter']]])
            ('key',_('Name'),30)
            ('key',_('Name'),30,'center')
            ('key',_('Name'),None,'center')
            ('key',_('Name'),None,'center', 'skype')

        # Example:
        fields=[]
        fields.append(('title',_('Title')))
        fields.append(('content',_('Content'),30,'right'))
        return fields

    - __searchQ__(self,info,text): limit the result with the text you write on the search box, it is a dictionary with Q-objects
        # Example:
        tf={}
        tf['title']=Q(title__icontains=text)
        tf['content']='content__startwith'
        tf['content']=('content__icontains', lambda text: text.upper())
        tf['content']=Q(content__icontains=text)
        tf['created']='datetime' # <--- This is a special tag that indicates which field will be
                                 #      filtered by the date filter, only one field can act like this.

        return tf

    - __searchF__(self,info): it expect you to return a dictionary with subfilters (the one on the top right of the page), each value
                must contain a tuple with 3 elements where:
                (_('Name'),<function wich returns a Q-object>,[('key1',_('Text 1')),('key2',_('Text 2')),...])
                it can be as well:
                (_('Content'), <function 1>, <function 2>)
        # Example:
        tf={}
        tf['title']=(_('Title'), lambda x: Q(title__startswith=x),[('h',_('Starts with h')),('S',_('Starts with S'))])
        return tf

    - __limitQ__(self,info): it will limit always the resultant list of objects, it expects you to return a dicionary with Q-objects
        # Example:
        criterials=[]
        criterials.append(Q(tests__doctor__worker__person__user__username=info.user.username))
        criterials.append(Q(tests__geneticist__worker__person__user=info.user))
        l={}
        l['profile_people_limit']=reduce(operator_or_,criterials)
        return l
    '''
    def __init__(self, queryset, appname, modelname, viewname, request, user, profile, Mfields, MlimitQ, MsearchF, MsearchQ, listid, elementid, kwargs):
        # Internal attributes
        soul = queryset.__dict__.get('model',None)
        if soul:
            self.__soul = soul()
        else:
            self.__soul = None
        self.__appname = appname
        self.__modelname = modelname
        self.__viewname = viewname
        self.__Mfields = Mfields
        self.__MlimitQ = MlimitQ
        self.__MsearchF = MsearchF
        self.__MsearchQ = MsearchQ
        # Public attributes
        self.listid = listid
        self.elementid = elementid
        self.request = request
        self.user = user
        self.profile = profile
        self.kwargs = kwargs

    def fields(self):
        if self.__Mfields:
            f = self.__Mfields
        elif self.__soul:
            f = getattr(self.__soul, '__fields__', None)
        else:
            f = None
        if callable(f):
            return f(self)
        else:
            if self.__Mfields:
                e = "View {1} inside app {0} has a __fields__ attribute which is not callable".format(self.__appname, self.__viewname)
            else:
                e = "Model {1} inside app {0} is missing __fields__ method".format(self.__appname, self.__modelname)
            raise ImproperlyConfigured(e)

    def limitQ(self):
        # Get the limits from limitQ internal function
        if self.__soul:
            f=getattr(self.__soul,'__limitQ__',None)
            if callable(f):
                limitQi=f(self)
            else:
                limitQi={}
        else:
            limitQi={}

        # Get the limits from limitQ external function
        if self.__MlimitQ:
            if callable(self.__MlimitQ):
                limitQe=self.__MlimitQ(self)
            else:
                e="View {1} inside app {0} has a __limitQ__ attribute which is not callable".format(self.__appname,self.__viewname)
                raise ImproperlyConfigured(e)
        else:
            limitQe={}

        answer={}
        for key in limitQi:
            answer["i_{0}".format(key)]=limitQi[key]
        for key in limitQe:
            answer["e_{0}".format(key)]=limitQe[key]

        # Return the resulting list
        return answer

    def searchF(self):
        if self.__MsearchF:
            f=self.__MsearchF
        elif self.__soul:
            f=getattr(self.__soul,'__searchF__',None)
        else:
            f=None
        if callable(f):
            return f(self)
        else:
            if self.__MsearchF:
                e="View {1} inside app {0} has a __searchF__ attribute which is not callable".format(self.__appname,self.__viewname)
                raise ImproperlyConfigured(e)
            else:
                return {}

    def searchQ(self,search):
        if self.__MsearchQ:
            f=self.__MsearchQ
        elif self.__soul:
            f=getattr(self.__soul,'__searchQ__',None)
        else:
            f=None
        if callable(f):
            return f(self,search)
        else:
            if self.__MsearchQ:
                e="View {1} inside app {0} has a __searchQ__ attribute which is not callable".format(self.__appname,self.__viewname)
                raise ImproperlyConfigured(e)
            else:
                return {}


def gen_auth_permission(user, action_permission, model_name, appname, permission=None, permission_group=None, explained=False):
    # Check if the GENPERMISSIONS settings is shutting down the PERMISSION system control from CODENERIX
    if hasattr(settings, 'GENPERMISSIONS') and not settings.GENPERMISSIONS:
        if not explained:
            return True
        else:
            return (True, None)
    else:
        # Initialize reason
        reason = ''

        # Checking authorization, initialize auth
        auth = False

        # Rename action_permission for special case (detail -> view)
        if action_permission == 'detail':
            action_permission = 'view'

        # Set specific permission
        specific_permission = "{}_{}".format(action_permission, model_name)
        app_specific_permission = "{}.{}_{}".format(appname, action_permission, model_name)

        # Calculate hash
        # YES HAS PERMS:
        #   1_flights_pilot_add_list_pilots
        #   1_flights_pilot_add_list_pilotslist_planes
        # NO DOESN'T HAVE PERMS:
        #   1_flights_pilot_add
        try:
            # python 2.7
            hash_key = hashlib.sha1(settings.SECRET_KEY).hexdigest()
        except TypeError:
            # python 3.x
            secret_key = bytes(settings.SECRET_KEY, encoding='utf-8')
            hash_key = hashlib.sha1(secret_key).hexdigest()
        
        cache_key = "{}_{}_{}_{}_{}_".format(hash_key, user.pk, appname, model_name, action_permission)
        
        if permission:
            if type(permission) == str:
                cache_key += "".join(permission)
                permission = [permission]
            elif type(permission) == list:
                cache_key += "".join(permission)
            else:
                raise ImproperlyConfigured("Model {1} inside app {0} is wrong configured for attribute 'permission'".format(appname, model_name))
        else:
            permission = []

        if permission_group:
            cache_key += "_"
            if type(permission_group) == str:
                cache_key += permission_group
                permission_group = [permission_group]
            elif type(permission_group) == list:
                cache_key += "".join(permission_group)
            else:
                raise ImproperlyConfigured("Model {1} inside app {0} is wrong configured for attribute 'permission_group'".format(appname, model_name))
        else:
            permission_group = []

        # Look for the key in cache
        try:
            # python 2.7
            hash_key = hashlib.sha1(cache_key).hexdigest()
            result = cache.get(hash_key)
        except TypeError:
            # python 3.x
            cache_key = bytes(cache_key, encoding='utf-8')
            hash_key = hashlib.sha1(cache_key).hexdigest()
            result = cache.get(hash_key)

        # If I found it in cache
        if result is not None:
            # Get result from cache
            auth = result
            reason = "Found in cache! (KEY:{} - HASH:{})".format(cache_key, hash_key)
        else:

            # Check if some authorization system was set
            if permission or permission_group:

                # Check if the user is in an authorized group
                if permission_group:
                    auth = user.groups.filter(name__in=permission_group).exists()

                # If we couldn't authorize yet, check unitary permissions
                if not auth and permission:

                    # Check all permissions set in the class
                    for perm in permission:

                        # Check if user has permission
                        if user.has_perm(perm):

                            # The permission is authorized
                            auth = True
                            break

                    # If not authorized yet, check unitary permissions inside groups
                    if not auth:

                        # Get the list of gropus for this user
                        group_user = user.groups.all()

                        # For each permission
                        for perm in permission:

                            # For each group
                            for group in group_user:

                                # Check if the permission is authorized in the group
                                if group.permissions.filter(codename=perm).exists():

                                    # The permission is authorized
                                    auth = True
                                    break

                            # If already authorized, leave the bucle
                            if auth:
                                break
                    
                    if not auth:
                        reason = "Not authorized for: permissions: {} - permission group: {}".format(",".join(permission), ",".join(permission_group))

            else:
                # If no other permission details was set in the class, use standar checks
                if user.has_perm(specific_permission) or user.has_perm(app_specific_permission):
                    auth = True
                else:
                    
                    for group in user.groups.all():
                        if group.permissions.filter(codename=specific_permission).exists():
                            auth = True
                            break
                        elif group.permissions.filter(codename=app_specific_permission).exists():
                            auth = True
                            break
                    
                    if not auth:
                        reason = "Not authorized for {} or {}".format(specific_permission, app_specific_permission)

            # Set cache
            getattr(cache, "set")(cache_key, auth)

    # Return result
    if not explained:
        return auth
    else:
        if not reason:
            reason = "-"
        return (auth, reason)


class GenBase(object):

    json = False
    search_filter_button = False

    # Translations
    gentranslate = {
        'Add': _("Add"),
        'Edit': _("Edit"),
        'Cancel': _("Cancel"),
        'Search': _("Search"),
        'Filters': _("Filters"),
        'RowsPerPage': _("Rows per page"),
        'PageNumber': _("Page number"),
        'registers': _("registers"),
        'CleanFilters': _("Clean filters"),
        'PrintExcel': _("Print Excel"),
        'Date': _("Date"),
        'Year': _("Year"),
        'Month': _("Month"),
        'Day': _("Day"),
        'Time': _("Time"),
        'Hour': _("Hour"),
        'Minute': _("Minute"),
        'Second': _("Second"),
        'Change': _("Change"),
        'Delete': _("Delete"),
        'View': _("View"),
        'Download': _("Download"),
        }


    # Default tabs information
    tabs = []

    # Constants
    BASE_URL = getattr(settings, 'BASE_URL', '')
    DEFAULT_STATIC_PARTIAL_ROWS = os.path.join(settings.STATIC_URL, 'codenerix/partials/rows.html')

    def dispatch(self, *args, **kwargs):
        # Save arguments in the environment
        self.__args = kwargs
        self.__kwargs = kwargs
        # Prepare
        if getattr(self, 'public', False):
            # Django's original dispatch
            return super(GenBase, self).dispatch(*args, **kwargs)
        else:
            # Authenticated dispatch
            return login_required(self.dispatch_auth)(*args, **kwargs)

    @method_decorator(login_required)
    def dispatch_auth(self, *args, **kwargs):
        # Check if user is_admin is required
        if hasattr(self, 'must_be_superuser') and self.must_be_superuser:
            if not self.request.user.is_superuser:
                redir = redirect('not_authorized')
                if getattr(settings, 'DEBUG', False):
                    redir['NotAuthorizedReason']=_("The view/model definition requires, that this user must be a superuser")
                return redir

        (authorized, reason) = self.auth_permission(self.action_permission, explained=True)
        if not authorized:
            redir = redirect('not_authorized')
            if getattr(settings, 'DEBUG', False):
                redir['NotAuthorizedReason']=reason
            return redir

        # Keep going with dispatch
        return super(GenBase, self).dispatch(*args, **kwargs)

    def auth_permission(self, action_permission, explained=False):
        permission = getattr(self, 'permission', None)
        permission_group = getattr(self, 'permission_group', None)

        model_name = getattr(self.model, "_meta", None) and getattr(self.model._meta, "model_name")
        if not model_name:
            raise IOError("Couldn't find a model_name inside your model, did you provided a model or some other class? - Type of your object is '{}'".format(self.model.__module__))

        (authorized, reason) = gen_auth_permission(
            self.request.user,
            action_permission,
            model_name,
            self._appname,
            permission,
            permission_group,
            explained=True
        )
        if not explained:
            return authorized
        else:
            return (authorized, reason)

    def _setup(self, request):
        '''
        Entry point for this class, here we decide basic stuff
        '''

        # Get details from self
        info = model_inspect(self)
        self._appname = getattr(self, 'appname', info['appname'])
        self._modelname = getattr(self, 'modelname', info['modelname'])

        # Get user information
        if not hasattr(self, 'user'):
            self.user = self.request.user
        # Get profile
        self.profile = get_profile(self.user)

        # Get language
        self.language = get_language()

        # Build extracontext
        if not hasattr(self, 'extra_context'):
            self.extra_context = {}

        # Default value for no foreign key attribute
        if 'no_render_as_foreign' not in self.extra_context:
            self.extra_context['no_render_as_foreign'] = []

    def get_template_names(self):
        '''
        Build the list of templates related to this user
        '''

        # Get user template
        template_model = getattr(self, 'template_model', "{0}/{1}_{2}".format(self._appname.lower(),self._modelname.lower(),self.get_template_names_key))
        template_model_ext = getattr( self, 'template_model_ext', 'html')
        templates=get_template(template_model,self.user,self.language,template_model_ext, raise_error=False)
        if type(templates)==list:
            templates.append("codenerix/{0}.html".format(self.get_template_names_key))

        # Return thet of templates
        return templates

    def get_context_data(self, **kwargs):
        '''
        Set a base context
        '''

        # Call the base implementation first to get a context
        context = super(GenBase, self).get_context_data(**kwargs)

        # Update general context with the stuff we already calculated
        if hasattr(self, 'html_head'):
            context['html_head'] = self.html_head(self.object)

        # Add translation system
        if hasattr(self, 'gentrans'):
            context['gentranslate'] = self.gentrans.copy()
            context['gentranslate'].update(self.gentranslate)
        else:
            context['gentranslate'] = self.gentranslate

        # Return context
        return context

    def get_object_api(self, api, obj):
        # No answer
        answer = None

        # Check api request
        if (api is not None) and ('include' in api or 'exclude' in api):

            # Get the fields for the API
            includes=api.get('include', None)
            excludes=api.get('exclude', None)

            # Get the list of fields
            fields = [f.name for f in obj._meta.get_fields()]
            related = [f.related_name for f in obj._meta.get_all_related_objects()]

            # Rebuild the list of fields
            if excludes is not None:
                for fieldname in excludes:
                    fields.pop(fields.index(fieldname))
            elif includes is not None:
                newfields=[]
                for fieldname in includes:
                    newfields.append(fieldname)
                fields=newfields

            # Build the answer
            answer = {}
            for fieldname in fields:
                # Get value
                value = getattr(obj, fieldname)

                # Only add non-reversed relationships
                if fieldname not in related:

                    # Analize data type
                    if type(value)==datetime.datetime:
                        # Convert datetime to string
                        value=value.strftime(formats.get_format('DATETIME_INPUT_FORMATS', lang=self.language)[0])
                    elif type(value)==datetime.date:
                        # Convert datetime to string
                        value=value.strftime(formats.get_format('DATE_INPUT_FORMATS', lang=self.language)[0])
                    elif type(value)==datetime.time:
                        # Convert datetime to string
                        value=value.strftime(formats.get_format('TIME_INPUT_FORMATS', lang=self.language)[0])
                    else:
                        # Analize if is related with another field but it is not a reverse relationship
                        isrelated=(getattr(value,'all',None) is not None)
                        if isrelated:
                            # If the object is related, get the list of PKs
                            values=[]
                            for v in value.all():
                                # This is a recursive call to go through foreign keys
                                values.append(v.pk)
                            # Save the list in value
                            value=values
                        elif callable(value):
                            # Build the list of arguments
                            args={}
                            # if 'request' in value.func_code.co_varnames:
                            if 'request' in value.__code__.co_varnames:
                                args['request']=self.request
                            # Call the method
                            value=value(**args)
                        elif hasattr(value, 'pk'):
                            # It is a foreignkey
                            value=value.pk

                    # Save the value
                    answer[fieldname] = value

        # Return the answer
        return answer

    def get_tabs_js(self):
        return self.get_tabs_data(js=True)

    def get_tabs_autorender(self):
        return self.get_tabs_data(js=False)

    def get_tabs_data(self, js):
        # Initialize
        tabs_js = []
        tabs_autorender = []
        internal_id = 0

        # Decide from where to get DETAIL class information
        if self.action_permission == 'list':
            myurl = self.request.get_full_path()
            if myurl:
                myurl = myurl.split("?")[0]
            mydetailsurl = "{}/0".format(myurl)
            mydetailsclss = get_class(resolve(mydetailsurl).func)
        else:
            mydetailsclss = self

        # Check for 'tabs' in extra_context
        mydetailsextra = getattr(mydetailsclss,'extra_context',None)
        if mydetailsextra:
            if js:
                for tab in mydetailsextra.get('tabs',[]):
                    # Get destination LIST class
                    tabdetailsclss = get_class(resolve(reverse(tab["ws"], kwargs={"pk": 0})).func)

                    # Build the sublist tab
                    tabfinal=tab.copy()

                    # Set kind
                    tabfinal['auto'] = False

                    # Get static partial row information
                    if 'static_partial_row' not in tab:
                        tabdetailinfo = model_inspect(tabdetailsclss)
                        static_partial_row_path="{0}/{1}_rows.html".format(tabdetailinfo['appname'],"{0}s".format(tabdetailinfo['modelname'].lower()))
                    else:
                        static_partial_row_path=tab['static_partial_row']

                    # Save static partial information
                    tabfinal['static_partial_row_path'] = settings.STATIC_URL + static_partial_row_path
                    tabfinal['static_partial_row'] = get_static(static_partial_row_path, self.user, self.language, self.DEFAULT_STATIC_PARTIAL_ROWS, 'html', relative=True)

                    # Save Internal ID
                    tabfinal['internal_id'] = internal_id
                    internal_id+=1

                    # Save in the queue
                    tabs_js.append(tabfinal)
            else:
                internal_id = len(mydetailsextra.get('tabs',[]))

        first = True
        tab_auto_open = None
        for tab in mydetailsclss.tabs:
            # Get destination LIST class
            tabdetailsclss = get_class(resolve(reverse(tab["ws"], kwargs={"pk": 0})).func)

            # Build the sublist tab
            tabfinal=tab.copy()

            # Set kind (this is autorender)
            tabfinal['auto'] = True

            # Remember first tab
            if first:
                tab_auto_open = tabfinal
                first = False

            # Set to open automatically the first tab from the list (this function can be improved)
            if 'auto_open' not in tabfinal.keys():
                tabfinal['auto_open'] = False
            elif tabfinal['auto_open']:
                tab_auto_open = None

            # Get static partial row information
            if 'static_partial_row' not in tab:
                tabdetailinfo = model_inspect(tabdetailsclss)
                static_partial_row_path="{0}/{1}_rows.html".format(tabdetailinfo['appname'],"{0}s".format(tabdetailinfo['modelname'].lower()))
            else:
                static_partial_row_path=tab['static_partial_row']

            # Save static partial information
            tabfinal['static_partial_row_path'] = settings.STATIC_URL + static_partial_row_path
            tabfinal['static_partial_row'] = get_static(static_partial_row_path, self.user, self.language, self.DEFAULT_STATIC_PARTIAL_ROWS, 'html', relative=True)

            # Save Internal ID
            tabfinal['internal_id'] = internal_id
            internal_id+=1

            # Save in the right queue
            tabs_js.append(tabfinal)
            tabs_autorender.append(tabfinal)

        # Set default auto_open if none was set
        if tab_auto_open:
            tab_auto_open['auto_open'] = True

        # Deliver tabs information to the context
        if js:
            return tabs_js
        else:
            return tabs_autorender

    def get_object(self):
        # Autoindex
        if self.action_permission == 'detail':
            cut_index = 1
        elif self.action_permission in ['change', 'delete']:
            cut_index = 2
        else:
            raise IOError(_("You have used get_object accidentally, this function has been designed only for action_permission: detail, change and delete"))

        # Get object
        pk = super(GenBase, self).get_object().pk
        # Get queryset
        queryset = self.model.objects.all()

        # Check if this class has a limitQ method
        error = False
        if hasattr(self, '__limitQ__'):
            myclass = self.__class__
            mykwargs = self.__kwargs
        else:
            # Get list class
            myurl = self.request.get_full_path()
            if myurl:
                myurl = myurl.split("?")[0]
            mylisturl = "/".join(myurl.split("/")[0:-cut_index])
            try:
                resolved_url = resolve(mylisturl)
            except Http404:
                resolved_url = None
            if resolved_url is not None:
                mylistclss = get_class(resolved_url.func)
                mykwargs = resolved_url.kwargs

                if issubclass(mylistclss, GenList):
                    # Set class info
                    myclass = mylistclss
                else:
                    error = True
            else:
                error = True

        distinct = False
        if not error:
            # Configure class
            info = model_inspect(myclass)
            profile = get_profile(self.user)
            appname = getattr(myclass, 'appname', info['appname'])
            modelname = getattr(myclass, 'modelname', info['modelname'])

            # Get MODELINFO
            Mfields = None
            MlimitQ = None
            MsearchF = None
            MsearchQ = None
            if hasattr(myclass, '__limitQ__'):
                MlimitQ = myclass().__limitQ__
            MODELINF = MODELINFO(myclass, appname, modelname, myclass.__module__, self.request, self.user, profile, Mfields, MlimitQ, MsearchF, MsearchQ, None, None, mykwargs)

            # Filter on limits
            if hasattr(self, '__limitQ__'):
                limits = self.__limitQ__(MODELINF)
            else:
                limits = MODELINF.limitQ()

            # Keep going
            qobjects = None
            for name in limits:
                if name == 'i_distinct' or name == 'e_distinct':
                    distinct = True
                else:
                    if qobjects:
                        qobjects &= limits[name]
                    else:
                        qobjects = limits[name]

            if qobjects:
                queryset = queryset.filter(qobjects)

        if hasattr(self, 'annotations'):
            queryset = queryset.annotate(**self.annotations)

        if distinct:
            queryset = queryset.distinct()

        # Return result
        return get_object_or_404(queryset, pk=pk)


# ListView helper: https://docs.djangoproject.com/en/1.6/ref/class-based-views/flattened-index/#list-views
# ListView flow:   https://docs.djangoproject.com/en/1.6/ref/class-based-views/generic-display/#listview
class GenList(GenBase, ListView):
    '''
    Usage:
    class NewList(GenList):
        model = NewModel

        must_be_superuser = True                    # If True it will request to be superuser

        permission = 'permission1'                  # Allowed only if user has permission1
        permission = ['perm2', 'perm3', ... ]       # Allowed only if user has perm2 or perm3

        permission_group = 'permission1'            # Allowed only if user group has permission1
        permission_group = ['perm2', 'perm3', ... ] # Allowed only if user group has perm2 or perm3

        user = <User Instance>                      # User object that GenView will use for all the process (except permissions checks)

        default_rows_per_page = 50                  # Number of rows to use on each page (by default is 50)

        template_base  = 'base/base'                # Base template to use, during standard template inheritance the last template will be base
        template_model = 'app/model_list'           # Model template to use, this is the entry point to the templates system
        template_base_ext  = 'html'                 # Extension for the base template file
        template_model_ext = 'html'                 # Extension for the model template file

        # https://docs.djangoproject.com/en/1.8/topics/db/aggregation/
        annotations = {                             # list of aggregations
            'min_price': Min('books__price'),       # the import Count, Sum, Avg, etc must do in of view
            'max_price': Max('books__price')        #
        }

        default_ordering = '-name'                  # Set a default ordering (Example: descent order by name)

        # compact_rows = ( compact_field, compact_subelements ) # NO IDEA ?????? It looks outdated to me -> Already deprecated in the source code

        json = True                                 # If set to true the system will answer with JSON automatically, you can avoid using this one
                                                    # and user json_builder() method to push the system to answer with JSON as well, this attribute
                                                    # will be set to true automaticall if the class get a request which includes a "json" argument
                                                    # inside the GET parameters with a valid JSON string. IMPORTANT:  By default json is set to True.

        client_context = {}                         # Contains information for filters in the client side, this structure will be returned inside
                                                    # the meta structure from JSON answers

        linkadd = False                             # With 'False' it will disable add button (by default this is enabled, 'True')
        linkedit = False                            # With 'False' it will disable edit autolink for rows (by default this is enabled, 'True')
        show_details = True                         # With 'True' it will show the details panel before editing the register (by default this is disabled, 'False')
        show_modal = True                           # With 'True' it will push the system to render the result in a modal window
        vtable = False                              # With 'True' it will use one-page-only lists with scroll detection for autoloading rows
        ngincludes = {'name':'path_to_partial'}     # Keep trace for ngincludes extra partials
        export_excel = True                         # Export to excel the list

        ws_entry_point                              # Set ws_entry_point variable to a fixed value
        static_partial_row                          # Set static_partial_row to a fixed value
        static_filters_row                          # Set static_filters_row to a fixed value

        field_delete = False     # Show/Hide button for delete register ('True'/'False')
        field_check = None      # None don't show checkbox, else show checkbox. if 'True' checked ('None', 'True', 'False')


    Templates will be selected using the next process:
    Grammar: <path>/<filename>[.<profile>][.<language>].html for this example we use 'seller' profile and 'es' language (spanish)
    1) path/filename.seller.es.html
    2) path/filename.seller.html
    3) path/filename.user.es.html
    4) path/filename.user.html
    5) path/filename.es.html
    6) path/filename.html

    This system also support dynamic partials loading when using JSON and AngularJS, you are able to define inside the app statics
    folder 2 optional files:
    - model_rows.html  : it should contain all <td>...</td>... required by the renderer of the table, you are allowed to use use fully AngularJS
    - model_filters.js : it should contain a module named "customFilters" wich should define filters that will be availabe when rendered the table,
                         so you can use this filters inside your own <td>...</td> elements.

    If you define a method named json_builder() it will push render_to_response() to serialize the output context as a json string
    def json_builder(self,answer,context):
        # This method precede to json attribute, if json attribute is set to False but json_builder() method exists, the system will answer with JSON
        # answer: brings a prebuilt answer with already preprocesed data
        # context: brings the Django's context so this function has all available data to make decisions

        # Here your code to build your new context
        answer['key']='value'

        # You can build the table body yourself or use bodybuilder, both solutions fill the structure the same way:

        # === 1: Body building on your own ===
        body=[]
        for o in context['object_list']:
            t={}
            t['name']=o.name
            t['surname']=o.surname
            phones=[]
            for o2 in o.phone.all():
                phone={}
                phone['country']=o2.country
                phone['prefix']=o2.prefix
                phone['number']=o2.number
                phones.append(t2)
            t['phone']=phones
            t['address']=o.address
            body.append(t)
        answer['table']['body']=body

        # Answer the new context
        return answer

        # === 2: Body building with bodybuilder() internal call ===
        answer['table']['body']=self.bodybuilder(context['object_list'],{
            'id:user__register__id':None,
            'name':None,
            'surname':None,
            'phone': {
                'country':None,
                'prefix':None,
                'number':None,
                },
            'address':None,
            })

        # Answer the new context
        return answer

        # === 3: Body building with autorules() and bodybuilder() internal calls ===
        # Get rules
        rules=self.autorules()
        # Get a key out from the rules
        rules.pop('id')
        # Add another key which includes an alias
        rules['id:user__id']=None
        # Call bodybuider with the new set of rules
        answer['table']['body']=self.bodybuilder(context['object_list'],rules)

        # Answer the new context
        return answer
    '''

    # Default values
    json=True
    default_rows_per_page = 50
    get_template_names_key='list'
    action_permission = 'list'
    extends_base = "base/base.html"

    def dispatch(self, *args, **kwargs):
        '''
        Entry point for this class, here we decide basic stuff
        '''

        # Check if this is a REST query to pusth the answer to responde in JSON
        if bool(self.request.META.get('HTTP_X_REST',False)):
            self.json = True
            if self.request.GET.get('json',self.request.POST.get('json',None)) is None:
                newget = {}
                newget['json'] = "{}"
                for key in self.request.GET:
                    newget[key] = self.request.GET[key]
                self.request.GET = QueryDict('').copy()
                self.request.GET.update(newget)

#                return HttpResponseBadRequest(_("The service requires you to set a GET argument named json={} which will contains all the filters you can apply to a list"))

        # Check if this is a REST query to add an element
        if self.request.method == 'POST':
            target = get_class(resolve("{}/add".format(self.request.META.get("REQUEST_URI"))).func)
            target.json = True
            return target.as_view()(self.request)

        # Set class internal variables
        self._setup(self.request)

        # Deprecations
        deprecated=[('retrictions','2016061000')]
        for (depre,version) in deprecated:
            if hasattr(self, depre):
                raise IOError("The attribute '{}' has been deprecated in version '{}' and it is not available anymore".format(version))

        # Build extracontext
        if not hasattr(self, 'extra_context'):
            self.extra_context={}
        if not hasattr(self, 'client_context'):
            self.client_context={}
        # Attach user to the extra_context
        self.extra_context['user']=self.user

        # Attach WS entry point and STATIC entry point
        self.extra_context['ws_entry_point'] = self.BASE_URL + getattr(self, "ws_entry_point", "{0}/{1}".format(self._appname, "{0}s".format(self._modelname.lower())))

        static_partial_row_path = getattr(self, 'static_partial_row', "{0}/{1}_rows.html".format(self._appname, "{0}s".format(self._modelname.lower())))
        self.extra_context['static_partial_row'] = get_static(static_partial_row_path, self.user, self.language, self.DEFAULT_STATIC_PARTIAL_ROWS, 'html', relative=True)

        static_filters_row_path = getattr(self, 'static_filters_row', "{0}/{1}_filters.js".format(self._appname, "{0}s".format(self._modelname.lower())))
        self.extra_context['static_filters_row'] = get_static(static_filters_row_path, self.user, self.language, 'codenerix/js/rows.js', 'js', relative=True)

        self.extra_context['field_delete'] = getattr(self, 'field_delete', False)
        self.extra_context['field_check'] = getattr(self, 'field_check', None)

        # Default value for extends_base
        if hasattr(self, 'extends_base'):
            self.extra_context['extends_base'] = self.extends_base
        elif hasattr(self, 'extends_base'):
            self.extra_context['extends_base'] = self.extends_base

        # Get if this is a template only answer
        self.__authtoken = (bool( getattr( self.request, "authtoken", False ) ))
        self.__json_worker=(hasattr(self, 'json_builder')) or self.__authtoken or (self.json is True)
        if self.__json_worker:
            # Check if the request has some json query, if not, just render the template
            if self.request.GET.get('json',self.request.POST.get('json',None)) is None:
                # Calculate tabs
                if getattr(self, 'show_details', False):
                    self.extra_context['tabs_js'] = json.dumps(self.get_tabs_js())

                # Silence the normal execution from this class
                self.get_queryset=lambda: None
                self.get_context_data=lambda **kwargs: self.extra_context
                self.render_to_response=lambda context, **response_kwargs: super(GenList, self).render_to_response(context, **response_kwargs)
                # Call the base implementation and finish execution here
                return super(GenList, self).dispatch(*args, **kwargs)

        # Initialize a default context
        self.__kwargs=kwargs
        self.__context={}

        # Call the base implementation
        return super(GenList, self).dispatch(*args, **kwargs)

    def autoSearchF(self, MODELINF):
        fields_show = [x[0] for x in MODELINF.fields()]
        fields = {}
        for field in self.model._meta.get_fields():
            if field.name in fields_show:
                if type(field) in [models.CharField, models.TextField]:
                    if field.choices:
                        fields[field.name] = (field.name, lambda x, fieldname=field.name: Q(**{'{}'.format(fieldname): x}), list(field.choices))
                    else:
                        fields[field.name] = (field.verbose_name, lambda x, fieldname=field.name: Q(**{'{}__icontains'.format(fieldname): x}), 'input')
                elif type(field) in [models.BooleanField, ]:
                    fields[field.name] = (field.verbose_name, lambda x, fieldname=field.name: Q(**{'{}'.format(fieldname): x}), [(True, _('Yes')), (False, _('No'))])
                elif type(field) in [models.DateField, models.DateTimeField, ]:
                    fields[field.name] = (field.verbose_name, lambda x, fieldname=field.name: Q(**daterange_filter(x, fieldname)), 'daterange')
                elif type(field) in [models.IntegerField, models.SmallIntegerField, models.FloatField, ]:
                    fields[field.name] = (field.verbose_name, lambda x, fieldname=field.name: Q(**{'{}'.format(fieldname): x}), 'input')
        return fields

    def get_queryset(self):
        # Call the base implementation
        queryset=super(GenList, self).get_queryset()

        # Optional tweak methods
        Mfields=None; MlimitQ=None; MsearchF=None; MsearchQ=None
        if hasattr(self, '__fields__'):     Mfields=self.__fields__
        if hasattr(self, '__limitQ__'):     MlimitQ=self.__limitQ__
        if hasattr(self, '__searchF__'):    MsearchF=self.__searchF__
        if hasattr(self, '__searchQ__'):    MsearchQ=self.__searchQ__

        self._viewname=self.__module__

        # Link to our context and kwargs
        context=self.__context

        # Update kwargs if json key is present
        jsonquery=self.request.GET.get('json',self.request.POST.get('json',None))
        if jsonquery is not None:
            jsondata=self.set_context_json(jsonquery)
            # Get listid
            listid=jsondata.pop('listid')
            # Get elementid
            elementid=jsondata.pop('elementid')
        else:
            listid=None
            elementid=None
            jsondata={}

        # Build info for GenModel methods
        MODELINF=MODELINFO(queryset, self._appname, self._modelname, self._viewname, self.request, self.user, self.profile, Mfields, MlimitQ, MsearchF, MsearchQ,listid,elementid,self.__kwargs)

        # Process the filter
        context['filters']=[]
        context['filters_obj']={}

        # Get field list
        fields = getattr(self, 'fields', MODELINF.fields())

        # Save GET values
        context['get']=[]
        context['getval']={}
        for name in jsondata:
            struct={}
            struct['name']=name
            if name=='rowsperpage':
                struct['value']=self.default_rows_per_page
            elif name=='page':
                struct['value']=1
            elif name=='pages_to_bring':
                struct['value']=1
            else:
                struct['value']=jsondata[name]
            context['get'].append(struct)
            context['getval'][name]=struct['value']

        # Filter on limits
        limits=MODELINF.limitQ()
        qobjects=None
        distinct=False
        for name in limits:
            if name=='i_distinct' or name=='e_distinct':
                distinct=True
            else:
                if qobjects:
                    qobjects&=limits[name]
                else:
                    qobjects=limits[name]

        if qobjects:
            queryset=queryset.filter(qobjects)

        if hasattr(self, 'annotations'):
            queryset=queryset.annotate(**self.annotations)

        if distinct:
            queryset=queryset.distinct()

        # Filters on fields requested by the user request
        try:
            filters_get=jsondata.get('filters','{}')
            if type(filters_get)==dict:
                filters_by_struct=filters_get
            else:
                filters_by_struct=json.loads(str(filters_get))
        except Exception:
            filters_by_struct=[]

        # 
        listfilters = self.autoSearchF(MODELINF)
        # List of filters from the model
        listfilters.update(MODELINF.searchF())

        # Process the search
        filters_struct={}
        for key in filters_by_struct:
            # Get the value of the original filter
            value=filters_by_struct[key]
            # If there is something to filter, filter is not being changed and filter is known by the class
            try:
                value = int(value)
            except ValueError:
                pass
            except TypeError:
                pass

            # ORIG if (key in listfilters) and ((value>0) or (type(value) == list)):
            # V1 if (value and type(value) == int and key in listfilters) and ((value > 0) or (type(value) == list)):
            # V2 if (value and type(value) == int and key in listfilters) or ((value > 0) or (type(value) == list)):
            if value and key in listfilters:
                # Add the filter to the queryset
                rule = listfilters[key]
                # Get type
                typekind = rule[2]
                if type(typekind) == list:
                    # Compatibility: set typekind and fv in the old fassion
                    if type(value) == int:
                        fv = typekind[value - 1][0]
                        queryset = queryset.filter(rule[1](fv))
                        typekind = 'select'
                elif typekind == 'select':
                    # Get selected value from rule
                    if type(value) == int:
                        fv = rule[3][value - 1][0]
                        queryset = queryset.filter(rule[1](fv))
                elif typekind in ['multiselect', 'multidynamicselect']:
                    # Get selected values from rule
                    if type(value) in (list, tuple) and len(value):
                        qobjects = Q(rule[1](value[0]))
                        for fvt in value[1:]:
                            qobjects |= Q(rule[1](fvt))
                        queryset = queryset.filter(qobjects)
                elif typekind in ['daterange', 'input']:
                    # No arguments
                    fv = value
                    queryset = queryset.filter(rule[1](fv))
                elif typekind in ['checkbox', ]:
                    fv = value
                    queryset = queryset.filter(rule[1](fv))
                else:
                    raise IOError("Wrong typekind '{0}' for filter '{1}'".format(typekind, key))
                # Save it in the struct as a valid filter
                filters_struct[key] = value

        # Rewrite filters_json updated
        filters_json=json.dumps(filters_struct)

        # Build the clean get for filters
        get=context['get']
        filters_get=[]
        for element in get:
            if element['name'] not in ['filters']:
                struct={}
                struct['name']=element['name']
                struct['value']=element['value']
                filters_get.append(struct)

        # Add filter_json
        struct={}
        struct['name']='filters'
        struct['value']=filters_json
        filters_get.append(struct)
        context['filters_get']=filters_get

        # Get the list of filters allowed by this class
        filters = []
        for key in listfilters:
            typekind = listfilters[key][2]
            if type(typekind) == list:
                # Compatibility: set typekind and fv in the old fassion
                choice = [_('All')]
                for value in typekind:
                    choice.append(value[1])

                # Decide the choosen field
                if key in filters_struct.keys():
                    value = int(filters_struct[key])
                else:
                    value = 0
                typekind = 'select'
                argument = choice
            elif typekind == 'select':
                typevalue = listfilters[key][3]
                choice = [_('All')]
                for value in typevalue:
                    choice.append(value[1])

                # Decide the choosen field
                if key in filters_struct.keys():
                    value = int(filters_struct[key])
                else:
                    value = 0
                # Set choice as the command's argument
                argument = choice
            elif typekind in ['multiselect', 'multidynamicselect']:
                if typekind == 'multiselect':
                    typevalue = listfilters[key][3]
                    choice = []
                    for value in typevalue:
                        choice.append({'id': value[0], 'label': value[1]})
                else:
                    choice = list(listfilters[key][3:])
                    choice[1] = reverse_lazy(choice[1], kwargs={'search': 'a'})[:-1]

                # Decide the choosen field
                if key in filters_struct.keys():
                    value = filters_struct[key]
                else:
                    value = []

                # Set choice as the command's argument
                argument = choice
            elif typekind in ['daterange', 'input']:
                # Commands withouth arguments
                argument = None
                # Get the selected value
                if key in filters_struct.keys():
                    value = filters_struct[key]
                else:
                    value = None
            elif typekind in ['checkbox']:
                # Commands withouth arguments
                argument = None
                # Get the selected value
                if key in filters_struct.keys():
                    value = filters_struct[key]
                else:
                    value = None
            else:
                raise IOError("Wrong typekind '{0}' for filter '{1}'".format(typekind, key))

            # Build filtertuple
            filtertuple = (key, listfilters[key][0], typekind, argument, value)
            # Save this filter in the corresponding list
            filters.append(filtertuple)

        # Save all filters
        context['filters']=filters

        # Search filter button
        search_filter_button = jsondata.get('search_filter_button',None)
        if search_filter_button is not None:
            self.search_filter_button=search_filter_button

        # Search text in all fields
        search=jsondata.get('search','').lower()
        # Remove extra spaces
        newlen=len(search)
        oldlen=0
        while newlen!=oldlen:
            oldlen=newlen
            search=search.replace("  "," ")
            newlen=len(search)
        if len(search)>0 and search[0]==' ':
            search=search[1:]
        if len(search)>0 and search[-1]==' ':
            search=search[:-1]

        # Save in context
        context['search']=search
        datetimeQ=None
        if len(search)>0:

            # Get ID
            tid=None
            if 'id:' in search:
                tid=search.split(":")[1].split(" ")[0]
                # Decide if it is what we expect
                try:
                    tid=int(tid)
                except:
                    tid=None
                # Remove the token
                if tid:
                    search=search.replace("id:%s" % (tid),'')
                    search=search.replace("  "," ")

            # Get PK
            tpk=None
            if 'pk:' in search:
                tpk=search.split(":")[1].split(" ")[0]
                # Decide if it is what we expect
                try:
                    tpk=int(tpk)
                except:
                    tpk=None
                # Remove the token
                if tpk:
                    search=search.replace("pk:%s" % (tpk),'')
                    search=search.replace("  "," ")

            # Spaces on front and behind
            if len(search)>0 and search[0]==' ':
                search=search[1:]
            if len(search)>0 and search[-1]==' ':
                search=search[:-1]

            # Get fields to search in
            searchs=MODELINF.searchQ(search)
            qobjects={}
            qobjectsCustom={}
            for name in searchs:
                # Extract the token
                qtoken=searchs[name]
                if qtoken=='datetime':
                    # If it is a datetime
                    datetimeQ=name
                    continue
                elif (type(qtoken) == str) or (type(qtoken) == list):
                    # Prepare query
                    if type(qtoken)==tuple:
                        (query,func)=qtoken
                    else:
                        query=qtoken
                        func=lambda x:x

                    # If it is a string
                    if search:
                        for word in search.split(" "):
                            # If there is a word to process
                            if len(word)>0:
                                # Build the key for the arguments and set the word as a value for the Q search
                                if word[0]=='-':
                                    # If negated request
                                    #key="-{}".format(hashlib.md5(word[1:]).hexdigest())
                                    qdict={'{}'.format(query):func(word[1:])}
                                    qtokens_element=~Q(**qdict)
                                else:
                                    # If positive request
                                    #key="-{}".format(hashlib.md5(word[1:]).hexdigest())
                                    qdict={'{}'.format(query):func(word)}
                                    qtokens_element=Q(**qdict)

                                # Safe the token
                                if word in qobjects:
                                    qobjects[word].append(qtokens_element)
                                else:
                                    qobjects[word]=[qtokens_element]
                else:
                    if qobjectsCustom:
                        qobjectsCustom|=searchs[name]
                    else:
                        qobjectsCustom=searchs[name]

            # Build positive/negative
            qdata=None
            if search and qobjects:
                for word in search.split(" "):
                    if word.split(":")[0] not in ['id','pk']:
                        if word[0]=='-':
                            negative=True
                        else:
                            negative=False
                        qword=None
                        for token in qobjects[word]:
                            if qword:
                                if negative:
                                    qword&=token
                                else:
                                    qword|=token
                            else:
                                qword=token
                        if qword:
                            if qdata:
                                qdata&=qword
                            else:
                                qdata=qword

            # Process ID/PK specific searches
            if tid:
                queryset=queryset.filter(id=tid)
            if tpk:
                queryset=queryset.filter(pk=tpk)
            # Add custom Q-objects
            if qobjectsCustom:
                queryset=queryset.filter(qobjectsCustom)
            # Add word by word search Q-objects
            if qdata:
                queryset=queryset.filter(qdata)
        else:
            # Look for datetimeQ field
            searchs=MODELINF.searchQ(search)
            for name in searchs:
                if (searchs[name]=='datetime'):
                    datetimeQ=name
                    continue

        # Datetime Q
        context['datetimeQ']=datetimeQ
        if datetimeQ:
            # Inicialization
            f={}
            f['year']=(1900,2100,False)
            f['month']=(1,12,False)
            f['day']=(1,31,False)
            f['hour']=(0,23,False)
            f['minute']=(0,59,False)
            f['second']=(0,59,False)
            date_elements=[None,'year','month','day','hour','minute','second']
            # Get configuration of dates and set limits to the queryset
            for element in date_elements[1:]:
                value=jsondata.get(element,None)
                if value:
                    f[element]=(int(value),int(value),True)
            if f['year'][2] and f['month'][2] and not f['day'][2]:
                (g,lastday)=calendar.monthrange(f['year'][1],f['month'][1])
                f['day']=(f['day'][0],lastday,f['day'][2])
            # Limits
            date_min=datetime.datetime(f['year'][0], f['month'][0], f['day'][0], f['hour'][0], f['minute'][0], f['second'][0])
            date_max=datetime.datetime(f['year'][1], f['month'][1], f['day'][1], f['hour'][1], f['minute'][1], f['second'][1])
            qarg1={"{}__gte".format(datetimeQ):date_min}
            qarg2={"{}__lte".format(datetimeQ):date_max}
            qarg3={datetimeQ:None}
            queryset=queryset.filter((Q(**qarg1) & Q(**qarg2)) | Q(**qarg3))

            # Find actual deepness
            deepness_index=0
            for element in date_elements[1:]:
                if f[element][2]:
                    deepness_index+=1
                else:
                    break

            # Get results from dates to set the new order
            exclusion={}
            exclusion[datetimeQ]=None
            date_results=queryset.exclude(**exclusion).values_list(datetimeQ, flat=True)
            # Remove empty results (usefull when the date is allowed to be empty)
            if f['day'][0]!=f['day'][1]:
                if f['month'][0]==f['month'][1]:
                    date_results=date_results.datetimes(datetimeQ,'day')
                elif f['year'][0]==f['year'][1]:
                    date_results=date_results.datetimes(datetimeQ,'month')
                else:
                    date_results=date_results.datetimes(datetimeQ,'year')

            get=context['get']
            context['datefilter']={}
            # Save the deepness
            if (deepness_index+1==len(date_elements)):
                context['datefilter']['deepness']=None
            else:
                context['datefilter']['deepness']=date_elements[deepness_index+1]
            context['datefilter']['deepnessback']=[]
            context['datefilter']['deepnessinit']=[]
            for element in get:
                if (not element['name'] in date_elements):
                    struct={}
                    struct['name']=element['name']
                    struct['value']=element['value']
                    context['datefilter']['deepnessinit'].append(struct)
                    context['datefilter']['deepnessback'].append(struct)
                elif (element['name']!=date_elements[deepness_index] and f[element['name']][2]):
                    struct={}
                    struct['name']=element['name']
                    struct['value']=element['value']
                    context['datefilter']['deepnessback'].append(struct)
            # Build the list of elements
            context['datefilter']['data']=[]
            for element in date_results:
                # Save the data
                context['datefilter']['data'].append(element.timetuple()[deepness_index])
            context['datefilter']['data']=list(set(context['datefilter']['data']))
            context['datefilter']['data'].sort()

            # Prepare the rightnow result
            if self.__json_worker:
                rightnow={}
                for key in ['year','month','day','hour','minute','second']:
                    rightnow[key]=(f[key][2] and f[key][0]) or None
            else:
                if f['month'][2]:
                    month=monthname(f['month'][0])
                else:
                    month='__'
                if f['hour'][2]:
                    rightnow=string_concat(grv(f,'day'),"/",month,"/",grv(f,'year')," ",grv(f,'hour'),":",grv(f,'minute'),":",grv(f,'second'))
                else:
                    rightnow=string_concat(grv(f,'day'),"/",month,"/",grv(f,'year'))
            context['datefilter']['rightnow']=rightnow
        else:
            context['datefilter']=None

        # Distinct
        #queryset=queryset.distinct()

        # Ordering field autofill
        try:
            order_get = jsondata.get('ordering', [])
            if type(order_get) == list:
                order_by_struct = order_get
            else:
                order_by_struct = json.loads(str(order_get))
        except Exception:
            order_by_struct = []
        order_by = []
        position = {}
        counter = 1

        # Build the columns structure and the fields list
        context['columns'] = []
        self.__fields = []
        for value in fields:
            self.__fields.append(value[0])

        # Auto build rules
        self.__autorules = self.autorules()

        for order in order_by_struct:
            name = list(order.keys())[0]
            lbl = None
            # use __autofields for ordering by alias
            for field in self.__autorules:
                if "{}:".format(name) in field:
                    name = field.split(":")[0]
                    lbl = field.split(":")[1]
                    break
            direction = order[name]

            if lbl and not lbl.startswith('get_') and not lbl.endswith('_display'):
                name = lbl

            if direction == 'asc':
                order_by.append("%s" % (remove_getdisplay(name)))
            elif direction == 'desc':
                order_by.append("-%s" % (remove_getdisplay(name)))
            position[name] = counter
            counter += 1

        if order_by:
            queryset = queryset.order_by(*order_by)
        else:
            if hasattr(self, 'default_ordering'):
                if type(self.default_ordering) == list:
                    queryset = queryset.order_by(*self.default_ordering)
                else:
                    queryset = queryset.order_by(self.default_ordering)
            else:
                queryset = queryset.order_by("pk")

        # Ordering field autofill
        sort = {}
        for value in fields:
            # Get values
            if value[0]:
                name = value[0].split(":")[0]
                order_key = name
            else:
                name = value[0]
                # not usable fields, example: fields.append((None, _('Selector'))) in airportslist
                try:
                    # python 2.7
                    hash_key = hashlib.md5(value[1]).hexdigest()
                except TypeError:
                    # python 3.x
                    info_key = bytes(value[1], encoding='utf-8')
                    hash_key = hashlib.md5(info_key).hexdigest()
                order_key = "#{}".format(hash_key)

            publicname = value[1]
            if len(value) > 2:
                size = value[2]
            else:
                size = None
            if len(value)>3:
                align = value[3]
            else:
                align = None
            # filter column
            if len(value)>4:
                filter_column=value[4]
            else:
                filter_column=None

            # Process ordering
            ordering = []
            found = False
            for order in order_by_struct:
                subname = list(order.keys())[0]
                direction = order[subname]
                if order_key == subname:
                    if direction == 'desc':
                        direction = ''
                        sort_class = 'headerSortUp'
                    elif direction == 'asc':
                        direction = 'desc'
                        sort_class = 'headerSortDown'
                    else:
                        sort_class =''
                        direction = 'asc'
                    found = True
                if direction == 'asc' or direction == 'desc':
                    ordering.append({subname: direction})

            if not found:
                ordering.append({order_key: 'asc'})
                sort_class = ''
            # Save the ordering method
            sort[order_key] = {}
            sort[order_key]['id'] = name
            sort[order_key]['name'] = publicname
            sort[order_key]['align'] = align
            if filter_column:
                sort[order_key]['filter'] = filter_column

            if jsonquery is None:
                sort[order_key]['size'] = size
                sort[order_key]['class'] = sort_class
                if order_key and order_key[0] != '*':
                        sort[order_key]['ordering'] = json.dumps(ordering).replace('"','\\"')
                if order_key in position:
                    sort[order_key]['position'] = position[order_key]

        # Save ordering in the context
        if jsonquery is not None:
            context['ordering'] = order_by_struct

        # Build the columns structure and the fields list
        context['columns'] = []
        for value in fields:
            field = value[0]
            if field:
                context['columns'].append(sort[field.split(":")[0]])
            else:
                try:
                    # python 2.7
                    hash_key = hashlib.md5(value[1]).hexdigest()
                except TypeError:
                    # python 3.x
                    info_key = bytes(value[1], encoding='utf-8')
                    hash_key = hashlib.md5(info_key).hexdigest()
                field = "#{}".format(hash_key)
                # selector
                context['columns'].append(sort[field])

        # Auto build rules
        # self.__autorules = self.autorules()

        # Columns
        self.__columns = ['pk']
        # self.__columns = ['id']
        self.__foreignkeys = []
        for column in self.model._meta.fields:
            self.__columns.append(column.name)
            if column.is_relation:
                self.__foreignkeys.append(column.name)

        # Localfields
        self.__related_objects = []
        for f in self.model._meta.related_objects:
            self.__related_objects.append(f.name)

        # Model properties
        model_properties = self.__columns + self.__related_objects

        # === Queryset optimization ===
        # Get autorules ordered
        autorules_keys = sorted(self.__autorules.keys())
        #
        query_renamed = {}
        query_optimizer = []
        query_verifier = []
        query_select_related = []
        fields_related_model = []

        for rule in autorules_keys:
            found = False
            # name rule origin
            rule_org = rule
            # If rule is an alias
            rulesp = rule.split(":")
            if len(rulesp) == 2:
                (alias, rule) = rulesp
            else:
                alias = rule

            # If rule has a foreign key path (check first level attributes only, nfrule = no foreign rule)
            nfrule = rule.split("__")
            do_select_related = False
            model = self.model
            if len(nfrule) > 1:
                ruletmp = []
                field_related_model = []
                for n in nfrule:
                    if model:
                        for fi in model._meta.fields:
                            if fi.name == n:
                                found = True
                                ruletmp.append(n)
                                if fi.is_relation:
                                    model = fi.related_model
                                    field_related_model.append(fi.name)
                                else:
                                    do_select_related = True
                                    model = None
                                break
                    if not found or model is None:
                        break
                if field_related_model:
                    fields_related_model.append("__".join(field_related_model))

                if ruletmp != nfrule:
                    do_select_related = False
            elif nfrule[0] in [x.name for x in self.model._meta.fields] or nfrule[0] == 'pk':
                found = True
                for fi in model._meta.fields:
                    if fi.name == nfrule[0] and fi.is_relation:
                        fields_related_model.append(nfrule[0])

            if do_select_related or rule in self.__foreignkeys:
                # Compatibility with Django 1.10
                if "__" in rule:
                    query_select_related.append("__".join(rule.split('__')[0:-1]))
                else:
                    query_select_related.append(rule)

            nfrule = nfrule[0]

            if nfrule in self.__columns:

                ############################
                # dejo comentada la restriccion, si se deja y hay una FK "nunca" usaria .extra ni .value
                # no la elimino del todo por si hubiera algun fallo mas adelante,
                # y se tuviera que parametrizarse de algun otro modo
                ############################

                # if nfrule not in self.__foreignkeys:
                if rule not in fields_related_model:
                    # Save verifier name
                    query_verifier.append(rule_org)
                
                # Save renamed field
                if alias != rule:
                    query_renamed[alias] = F(rule)
                    query_optimizer.append(alias)
                else:
                    # Save final name
                    query_optimizer.append(rule)

            if hasattr(self, 'annotations'):
                for xnfrule in self.annotations.keys():
                    found = True
                    if xnfrule not in query_verifier:
                        query_verifier.append(xnfrule)
                        query_optimizer.append(xnfrule)

            if not found:
                query_renamed = {}
                query_optimizer = []
                query_verifier = []
                query_select_related = []
                break

        for rename in query_renamed.keys():
            if rename in model_properties:
                if rename in self.__foreignkeys:
                    msg = "Invalid alias. The alias '{}' is a foreign key from model '{}' inside app '{}'"
                elif rename in self.__columns:
                    msg = "Invalid alias. The alias '{}' is a columns from model '{}' inside app '{}'"
                elif rename in self.__related_objects:
                    msg = "Invalid alias. The alias '{}' is a related object from model '{}' inside app '{}'"
                raise Exception(msg.format(rename, self._modelname, self._appname))

        if found and query_select_related:
            queryset = queryset.select_related(*query_select_related)
        # If we got the query_optimizer to optimize everything, use it
        use_extra = False
        query_verifier.sort()
        autorules_keys.sort()
        if found and query_verifier == autorules_keys:
            use_extra = True
            if query_renamed:
                # queryset=queryset.extra(select=query_renamed).values(*query_optimizer)
                queryset = queryset.annotate(**query_renamed).values(*query_optimizer)
            else:
                queryset = queryset.values(*query_optimizer)
        """
        raise Exception("FOUND: {} -- __foreignkeys: {} -- __columns: {} -- autorules_keys: {} -- \
            query_select_related: {} -- query_renamed: {} -- query_optimizer: {} | use_extra: {}| -- \
            query: {} -- meta.fields: {} -- fields_related_model: {} -- query_verifier: {}\
            -- ??? {} == {}".format(
                found,
                self.__foreignkeys, self.__columns, autorules_keys,
            query_select_related, query_renamed, query_optimizer,use_extra,
            queryset.query,
            [x.name for x in self.model._meta.fields],
            fields_related_model, query_verifier,
            query_verifier.sort(),autorules_keys.sort()
            ))
        #"""

        # Check the total count of registers + rows per page
        total_rows_per_page = jsondata.get('rowsperpage', self.default_rows_per_page)
        pages_to_bring = jsondata.get('pages_to_bring', 1)
        if total_rows_per_page == 'All' or 'printer' in context:
            total_rows_per_page = queryset.count()
        paginator = Paginator(queryset, total_rows_per_page)
        total_registers = paginator.count

        # Rows per page
        if total_rows_per_page:
            try:
                total_rows_per_page = int(total_rows_per_page)
            except Exception:
                total_rows_per_page = 'All'
        else:
            total_rows_per_page = self.default_rows_per_page
        if total_rows_per_page == 'All':
            page_number = 1
            total_rows_per_page = total_registers
            total_rows_per_page_out = _('All')
            total_pages = 1
        else:
            total_rows_per_page = int(total_rows_per_page) # By default 10 rows per page
            total_rows_per_page_out = total_rows_per_page
            total_pages=int(total_registers/total_rows_per_page)
            if total_registers%total_rows_per_page:
                total_pages+=1
            page_number=jsondata.get('page',1)                  # If no page specified use first page
            if page_number=='last':
                page_number=total_pages
            else:
                try:
                    page_number=int(page_number)
                except:
                    page_number=1
                if page_number<1:
                    page_number=1
                if page_number>total_pages:
                    page_number=total_pages

        # Build the list of page counters allowed
        choice = {}
        c = self.default_rows_per_page
        chk = 1
        while total_registers>=c:
            choice[c] = c
            if chk == 1:
                # From 5 to 10
                c = c * 2
                # Next level
                chk = 2
            elif chk == 2:
                # From 10 to 25 (10*2+10/2)
                c = c * 2 + int( c / 2 )
                # Next level
                chk = 3
            elif chk == 3:
                # From 25 to 50
                c *= 2
                chk = 1
            # Don't give a too long choice
            if c > 2000:
                break

        # Add all choice in any case
        if settings.ALL_PAGESALLOWED:
            choice['All'] = _('All')


        # Save the pagination in the structure
        context['rowsperpageallowed'] = choice
        context['rowsperpage'] = total_rows_per_page_out
        context['pages_to_bring'] = pages_to_bring
        context['pagenumber'] = page_number

        # Get the full number of registers and save it to context
        context['total_registers'] = total_registers
        if total_rows_per_page == 'All':
            # Remove total_rows_per_page if is all
            total_rows_per_page = None
            context['page_before'] = None
            context['page_after'] = None
            context['start_register'] = 1
            context['showing_registers'] = total_registers
        else:
            # Page before
            if page_number <= 1:
                context['page_before'] = None
            else:
                context['page_before'] = page_number-1
            # Page after
            if page_number >= total_pages:
                context['page_after'] = None
            else:
                context['page_after'] = page_number+1
            # Starting on register number
            context['start_register'] = (page_number-1)*total_rows_per_page+1
            context['showing_registers'] = total_rows_per_page

        # Calculate end
        context['end_register'] = min(context['start_register']+context['showing_registers']-1,total_registers)

        # Add pagination
        regs = []
        desired_page_number = page_number
        try:
            range_pages_to_bring = xrange(pages_to_bring)
        except NameError:
            range_pages_to_bring = range(pages_to_bring)
        for p in range_pages_to_bring:
            try:
                regs += paginator.page(desired_page_number)
                desired_page_number += 1
            except PageNotAnInteger:
                # If page is not an integer, deliver first page.
                regs += paginator.page(1)
                desired_page_number = 2
            except EmptyPage:
                # If page is out of range (e.g. 9999), deliver last page of results.
                if pages_to_bring == 1:
                    regs += paginator.page(paginator.num_pages)
                # Leave bucle
                break

        # Fill pages
        if total_registers:
            context['pages']=pages(paginator,page_number)
            try:
                range_fill = xrange(pages_to_bring-1)
            except NameError:
                range_fill = range(pages_to_bring-1)
            for p in range_fill:
                page_number+=1
                context['pages']+=pages(paginator,page_number)
        else:
            context['pages']=[]

        # Return queryset
        return regs

    def get_context_data(self, **kwargs):
        '''
        Generic list view with validation included and object transfering support
        '''

        # Call the base implementation first to get a context
        context = super(GenList, self).get_context_data(**kwargs)
        # Update general context with the stuff we already calculated
        context.update(self.__context)

        # Initialize with our timestamp
        context['now']=epochdate(time.time())
        context['profile']=self.profile

        # Check vtable
        context['vtable']=getattr(self,'vtable', False)

        # Export to excel
        context['export_excel'] = getattr(self, 'export_excel', True)

        # Check ngincludes
        context['ngincludes']=getattr(self,'ngincludes', {})
        if 'table' not in context['ngincludes'].keys():
            context['ngincludes']['table']="{}codenerix/partials/table.html".format(settings.STATIC_URL)

        # Check linkadd
        context['linkadd']=getattr(self,'linkadd', self.auth_permission('add') or getattr(self,'public',False))

        # Check linkedit
        context['linkedit']=getattr(self, 'linkedit', self.auth_permission('change') or getattr(self,'public',False))

        # Check showdetails
        context['show_details']=getattr(self, 'show_details', False)

        # Check showmodal
        context['show_modal']=getattr(self, 'show_modal', False)

        # Set search filter button
        context['search_filter_button'] = getattr(self, 'search_filter_button', False)

        # Get base template
        if not self.__json_worker:
            template_base=getattr(self,'template_base', 'base/base')
            template_base_ext=getattr(self, 'template_base_ext', 'html')
            context['template_base']=get_template(template_base,self.user,self.language,extension=template_base_ext)

        # Try to convert object_id to a numeric id
        object_id=kwargs.get('object_id',None)
        try:
            object_id=int(object_id)
        except:
            pass

        if type(object_id)==type(u'abc'):
            # If object_id is a string, we have a name not an object
            context['object_name']=object_id
            object_obj = None
        else:
            # If is not an string
            if object_id:
                # If we got one, load the object
                obj=context['obj']
                object_obj = get_object_or_404(obj, pk=object_id)
            else:
                # There is no object
                object_obj = None
            context['object_obj']=object_obj

        # Attach extra_context
        context.update(self.extra_context)
        # Return new context
        return context

    def __jcontext_metadata(self, context):
        # Initialiaze
        a = {}

        # Build get structure
        a['getval'] = {}
        for key in context['getval']:
            if key not in ['search', 'ordering', 'month', 'filters', 'page', 'pages_to_bring', 'rowsperpage', 'year', 'month', 'day', 'hour', 'minute', 'second', 'json', 'printer']:
                a['getval'] = context['getval'][key]

        # Set data
        a['username'] = self.user.username
        a['context'] = self.client_context
        a['url_media'] = settings.MEDIA_URL
        a['page'] = context['pagenumber']
        a['pages'] = context['pages']
        a['pages_to_bring'] = context['pages_to_bring']
        a['linkadd'] = context['linkadd']
        a['vtable'] = context['vtable']
        a['export_excel'] = context['export_excel']
        a['ngincludes'] = context['ngincludes']
        a['linkedit'] = context['linkedit']
        a['show_details'] = context['show_details']
        a['show_modal'] = context['show_modal']
        a['search_filter_button'] = context['search_filter_button']

        if self.__authtoken:
            a['version'] = getattr(settings, "VERSION", None)
            a['version_api'] = getattr(settings, "VERSION_API", None)

        if hasattr(self, 'gentrans'):
            gentranslate = self.gentrans.copy()
            gentranslate.update(self.gentranslate)
        else:
            gentranslate = self.gentranslate

        a["gentranslate"] = {}
        for key in gentranslate:
            try:
                a["gentranslate"][key] = unicode(gentranslate[key])
            except NameError:
                a["gentranslate"][key] = gentranslate[key]

        if type(context['rowsperpage']) == int:
            a['rowsperpage'] = context['rowsperpage']
        else:
            a['rowsperpage'] = gettext(context['rowsperpage'])
        a['rowsperpageallowed'] = context['rowsperpageallowed']
        a['row_total'] = context['total_registers']
        if a['row_total']:
            a['row_first'] = context['start_register']
            a['row_last'] = context['end_register']

        # Adapter
        if settings.ALL_PAGESALLOWED:
            translate_key = list(a['rowsperpageallowed'].keys())[-1]
            a['rowsperpageallowed'][translate_key] = a['rowsperpageallowed'][translate_key]

        if 'printer' in context['getval']:
            a['printer'] = context['getval']['printer']
        # Return answer
        return a

    def __jcontext_filter(self, context):
        # Initialiaze
        a={}

        # Set filters
        a['search']=context['search']
        a['date']=context['datefilter']
        if a['date']:
            if a['date']['deepness']=='year':       name=gettext(_("Year"))
            elif a['date']['deepness']=='month':    name=gettext(_("Month"))
            elif a['date']['deepness']=='day':      name=gettext(_("Day"))
            elif a['date']['deepness']=='hour':     name=gettext(_("Hour"))
            elif a['date']['deepness']=='minute':   name=gettext(_("Minute"))
            elif a['date']['deepness']=='second':   name=gettext(_("Second"))
            else:                                   name=gettext(_("Unknown"))
            a['date']['deepname']=name
            # Adapters
            a['date'].pop('deepnessinit')
            a['date'].pop('deepnessback')

        # Fill filters
        a['subfilters']=[]
        a['subfiltersC']=[]
        for (key,name,typekind,argument,value) in context['filters']:
            # Rebuild the tuple
            token={}
            token['key']=key.split(":")[0]
            token['name']=gettext(name)
            token['kind']=typekind
            # Decide by kind of data
            if typekind=='select':
                # Rebuild the choices
                newchoices=[]
                for filt in argument:
                    newchoices.append(gettext(filt))
                # Decide kind
                token['choice']=newchoices
                token['choosen']=value
            elif typekind=='multiselect':
                token['choice']=argument
                token['choosen']=value
            elif typekind=='multidynamicselect':
                token['choicedynamic']=argument
                token['choosen']=value


                func = resolve(argument[1]+'*').func
                clss = get_class(func)
                token['choices'] = clss().get_choices(value)

            elif typekind in ['daterange', 'input', 'checkbox']:
                # Decide kind
                token['value']=value
            else:
                raise IOError("Wrong typekind '{0}' for filter '{1}'".format(typekind,key))
            # Save it
            if key in self.__fields:
                a['subfiltersC'].append(token)
            else:
                a['subfilters'].append(token)

#        if 'rightnow' in a['date'] and a['date']['rightnow']:
#            a['date']['rightnow']=gettext(a['date']['rightnow'])

        # Return answer
        return a

    def __jcontext_tablehead(self,context):
        # Initialize the answer
        a={}

        # Add adapted columns
        a['columns']=[]
        for column in context['columns']:
            if column['name']:
                # Repair the name
                column['name']=gettext(column['name'])
                # Save the column
                a['columns'].append(column)

        # Remember ordering
        ordering = {}
        weight = 1
        for orderer in context['ordering']:
            # Get info
            key = list(orderer.keys())[0]
            value = orderer[key]
            # Prepare value
            if value == 'asc':
                newvalue =+ weight
                weight += 1
            elif value == 'desc':
                newvalue =- weight
                weight += 1
            else:
                newvalue = 0
            # Save
            ordering[key] = newvalue
        # Save ordering
        a['ordering'] = ordering

        # Special row
        a['datetimeQ'] = context['datetimeQ']

        a['extra_fields'] = {
            'field_check': context['field_check'],
            'field_delete': context['field_delete'],
        }
#        # Add hidding informatino
#        a['hide_head']=context['hide_head']
#        a['hide_tail']=context['hide_tail']
#        a['hide_subhead']=context['hide_subhead']
#        a['hide_subtail']=context['hide_subtail']

        # Return the answer
        return a

    def get_context_json(self,context):
        '''
        Return a base answer for a json answer
        '''
        # Initialize answer
        answer={}

        # Metadata builder
        answer['meta']=self.__jcontext_metadata(context)

        # Filter builder
        answer['filter']=self.__jcontext_filter(context)

        # Head builder
        answer['table']={}
        answer['table']['head']=self.__jcontext_tablehead(context)
        answer['table']['body']=None

        # Return answer
        return answer

    def set_context_json(self, jsonquery):
        '''
        Get a json parameter and rebuild the context back to a dictionary (probably kwargs)
        '''

        # Set we will answer json to this request
        self.json=True

        # Open json string
        v=json.loads(jsonquery)

        # Transfer keys
        newget={}
        for key in ['search','search_filter_button','page','pages_to_bring','rowsperpage','filters','year','month','day','hour','minute','second']:
            if key in v:
                newget[key]=v[key]

        # Add transformed ordering
        if ('ordering' in v) and (v['ordering']):
            # Convert to list
            ordering = []
            for key in v['ordering']:
                ordering.append({key: v['ordering'][key]})

            # Order the result from ordering
            # ordering = sorted(ordering, key=lambda x: abs(x.values()[0]))
            ordering = sorted(ordering, key=lambda x: abs(list(x.values())[0]))
            # Save ordering
            newget['ordering'] = []
            for orderer in ordering:
                key = list(orderer.keys())[0]
                value = orderer[key]
                if value > 0:
                    value = 'asc'
                elif value < 0:
                    value = 'desc'
                else:
                    value = None
                if value:
                    newget['ordering'].append({key: value})

        # Get listid
        if 'listid' in v:
            listid=v['listid']
        else:
            listid=None
        newget['listid']=listid

        # Get elementid
        if 'elementid' in v:
            elementid=v['elementid']
        else:
            elementid=None
        newget['elementid'] = elementid

        if 'printer' in v:
            printer = v['printer']
        else:
            printer = None
        newget['printer'] = printer

        # Return new get
        return newget

    def autorules(self):
        # Start the process
        a = {}
        a['pk'] = None
        for f in self.__fields:
            if f is not None:
                a[f] = None
        return a

    def bodybuilder(self,object_list,rules):

        # Initialize answer
        body=[]

        # Process all the list
        for o in object_list:
            # Initialize our token
            token={}

            # Check if we got a dict (optimized answer)
            if type(o) == dict:
                # Check all items if they need conversion
                for (key,value) in o.items():
                    # Rewrite values if required
                    if type(value)==datetime.datetime:
                        # Convert datetime to string
                        value=value.strftime(formats.get_format('DATETIME_INPUT_FORMATS', lang=self.language)[0])
                    elif type(value)==datetime.date:
                        # Convert datetime to string
                        value=value.strftime(formats.get_format('DATE_INPUT_FORMATS', lang=self.language)[0])
                    elif type(value)==datetime.time:
                        # Convert datetime to string
                        value=value.strftime(formats.get_format('TIME_INPUT_FORMATS', lang=self.language)[0])
                    # Save token
                    token[key]=value

            else:
                # Process all rules
                for rktemp in rules:
                    # Get the value
                    rkval=rules[rktemp]
                    # Check if as an alias
                    rktempsp=rktemp.split(":")
                    if len(rktempsp)==1:
                        alias=rktemp
                        rk=rktemp
                    else:
                        alias=rktempsp[0]
                        rk=rktempsp[1]

                    # Get actual value
                    rksp=rk.split("__")
                    head=rksp[0]
                    if len(rksp) > 1:
                        tail = "__".join(rksp[1:])
                    else:
                        tail = None
                    # value=getattr(o,head,None)  # 2016.02.24 Quitamos None para que aparezca la exception
                    value = getattr(o, head)

                    # If value is None, return None
                    if value is not None:
                        # Analize if is related
                        related=(getattr(value,'all',None) is not None)
                        # Analize data type
                        if type(rkval)==dict:
                            # This is a recursive call to go through foreign keys
                            value=self.bodybuilder(value.all(),rkval)
                        elif type(value)==datetime.datetime:
                            # Convert datetime to string
                            value=value.strftime(formats.get_format('DATETIME_INPUT_FORMATS', lang=self.language)[0])
                        elif type(value)==datetime.date:
                            # Convert datetime to string
                            value=value.strftime(formats.get_format('DATE_INPUT_FORMATS', lang=self.language)[0])
                        elif type(value)==datetime.time:
                            # Convert datetime to string
                            value=value.strftime(formats.get_format('TIME_INPUT_FORMATS', lang=self.language)[0])
                        elif related:
                            # If the object is related but nobody is taking care of it
                            values = []
                            for v in value.all():
                                # This is a recursive call to go through foreign keys
                                if tail is None:
                                    values.append(smart_text(v))
                                else:
                                    values.append(self.bodybuilder([v], {tail: rkval})[0][tail])
                            # Save the list in value
                            value = values
                        elif '__' in rk:
                            # This is a foreignkey, resolve with a recursive call to go through foreign keys
                            value = self.bodybuilder([value], {tail: rkval})[0][tail]
                        elif callable(value):
                            # Build the list of arguments
                            args = {}
                            if 'request' in value.__code__.co_varnames:
                                args['request'] = self.request
                            # Call the method
                            value = value(**args)
                        else:
                            # This is an attribute
                            value = smart_text(value)

                    # Save the value
                    token[alias] = value

            # Save token
            body.append(token)

        # Return the body
        return body

    def render_to_response(self, context, **response_kwargs):

        if self.__json_worker:
            # Get json ready context
            json_context=self.get_context_json(context)

            # Build the new answer
            if hasattr(self, 'json_builder'):
                answer=self.json_builder(json_context,context)
            else:
                # User doesn't want to change anything in our answer
                answer=json_context

            # Check if the user filled table body, if not, we will do it now
            if (type(answer)==dict) and ('table' in answer) and ('body' in answer['table']) and (answer['table']['body'] is None):
                # Call bodybuilder
                answer['table']['body'] = self.bodybuilder(context['object_list'], self.__autorules)

            if answer['meta']['printer']:
                if answer['meta']['printer'] == 'xls':
                    answer['meta']['content_type'] = 'application/vnd.ms-excel;charset=utf-8;'
                    # return_xls = self.response_to_xls(answer)
                    answer['table']['printer'] = self.response_to_xls(answer)
                else:
                    raise Exception("Export to {} invalid".format(answer['meta']['printer']))
            else:
                answer['meta']['content_type'] = None
                answer['table']['printer'] = {}
                answer['table']['printer']['message'] = None
                answer['table']['printer']['file'] = None
                answer['table']['printer']['filename'] = None

            # Try to serialize it as a JSON string
            try:
                json_answer=json.dumps(answer)
            except TypeError as  e:
                raise TypeError("The method json_builder() from model '{0}' inside app '{1}' didn't return a JSON serializable object. Error was: {2}".format(self._modelname,self._appname,e))
            # Return the new answer
            return HttpResponse(json_answer,content_type='application/json', **response_kwargs)
        else:
            return super(GenList, self).render_to_response(context, **response_kwargs)

    def response_to_xls(self, answer):
        wb = Workbook()

        dest_filename = '/tmp/empty_book.xlsx'

        ws1 = wb.active
        ws1.title = _("List")

        columns = []
        tmp = []
        for col in answer['table']['head']['columns']:
            tmp.append(col['name'])
            columns.append(col['id'])
        ws1.append(tmp)

        for col in answer['table']['body']:
            tmp = []
            for id in columns:
                if type(col[id]) != list:
                    tmp.append(col[id])
                else:
                    tmp.append("\n".join(col[id]))
            ws1.append(tmp)

        wb.save(filename=dest_filename)

        size_max = getattr(settings, "FILE_DOWNLOAD_SIZE_MAX", 1)
        tam_file = os.stat(dest_filename).st_size
        if tam_file <= (size_max * 1000000):
            return {
                'message': "",
                'file': base64.b64encode(open(dest_filename, 'r').read()),
                'filename': 'list.xlsx'
            }
        else:
            return {
                'message': _("The file is very big ({}M). Change the parameter FILE_DOWNLOAD_SIZE_MAX (in Megabytes) of the config".format(tam_file / 1000000.0)),
                'file': "",
                'filename': ""
            }


class GenListModal(GenList):
    get_template_names_key = 'listmodal'
    show_internal_name = False
    title = None

    def get_context_data(self, **kwargs):
        context = super(GenListModal, self).get_context_data(**kwargs)

        if hasattr(self, 'title'):
            context["title"] = self.title
        return context


class GenModify(object):
    '''
    Define generic methods for all our generic classes
    success_url = {'status':'accept','answer':''})  This is the URL where the view will go if everything goes fine (answer will be autofilled)
    success_url_keys = ['id','name:title']          List of keys from the CREATED/UPDATED object attached to answer attribute when success
                                                       the matching happens 'key1:key2' where answer[key1]=obj.key2
                                                       and remember that 'key' will be evaluated as 'key1:key1'
                                                       by default the system will add __pk__ (object primary key) and __str__ (string representation)
    get_template_names_key='add'                    Sufix added to all templates when templates name resolution is looking for the template
    show_details = True                             With 'True' it will keep a show_details variable inside the context (by default 'False')
    show_internal_name = False                      Will avoid showing the name of the model on the top of the form (default is 'True')
    hide_foreignkey_button = True                   With 'True' it will hide the '+' (plus button) from forms for creating new registers

    json = True                                     With 'True' it will return a JSON answer
    json_details = True                             With 'True' it will add details to JSON answer
    '''

    def __init__(self, *args, **kwargs):
        return super(GenModify, self).__init__(*args, **kwargs)

    def dispatch(self, request, **kwargs):
        '''
        Entry point for this class, here we decide basic stuff
        '''

        # Check if this is a webservice request
        self.__json_worker = (bool(getattr(self.request, "authtoken", False))) or (self.json is True)
        self.__authtoken = (bool(getattr(self.request, "authtoken", False)))

        # Check if this is an AJAX request
        if (request.is_ajax() or self.__json_worker) and request.body:
            request.POST = QueryDict('').copy()
            body = request.body
            if type(request.body) == bytes:
                body = body.decode("utf-8")
            post = json.loads(body)
            for key in post:
                if type(post[key]) == dict and '__JSON_DATA__' in post[key]:
                    post[key] = json.dumps(post[key]['__JSON_DATA__'])
            
            request.POST.update(post)

        # Set class internal variables
        self._setup(request)

        # Call the base implementation
        return super(GenModify, self).dispatch(request, **kwargs)

    def get_success_url(self):
        if self.object is None:
            # Built empty attr structure
            attr = {'__pk__': None, '__str__': 'OK'}
        else:
            # Built the attr structure
            attr = {'__pk__': self.object.pk, '__str__': smart_text(self.object)}
            # Fill attr with the rest of info
            for key in self.success_url_keys:
                keysp = key.split(":")
                if len(keysp) == 1:
                    key1 = keysp[0]
                    key2 = keysp[0]
                elif len(keysp) == 2:
                    key1 = keysp[0]
                    key2 = keysp[1]
                else:
                    raise TypeError("I found a key in success_url_attr neither with 1 or 2 elements, key is '{0}'".format(key))
                attr[key1] = self.object.__dict__[key2]
            # Attach object
            if self.__authtoken:

                # Get API field
                if getattr(self, '__api__', None):
                    api = self.__api__(self.request)
                elif getattr(self, '__api__', None):
                    api = self.object.__api__(self.request)
                else:
                    api = getattr(settings, 'API_DEFAULT', None)

                # Set the answer from the API
                api_obj = self.get_object_api(api, self.object)
                if api_obj is not None:
                    # Add the object information
                    attr['__obj__'] = api_obj

        # Set the pk in the success url
        self.success_url.__dict__['_proxy____kw']['kwargs']['answer'] = urlsafe_base64_encode(str.encode(json.dumps(attr)))
        # Let the system decide next step
        return super(GenModify, self).get_success_url()

    def get_context_data(self, **kwargs):
        # Get actual context
        context = super(GenModify, self).get_context_data(**kwargs)

        # Check showdetails
        context['show_details'] = getattr(self, 'show_details', False)

        # Check linkdelete
        context['linkdelete'] = getattr(self, 'linkdelete', True)

        # Check linkback
        context['linkback'] = getattr(self, 'linkback', True)

        # Check hide_foreignkey_button
        context['hide_foreignkey_button'] = getattr(self, 'hide_foreignkey_button', False)

        # Check hide internal_name
        context['show_internal_name'] = getattr(self, 'show_internal_name', True)

        if self.object is None:
            context["cannot_update"] = None
            context["cannot_delete"] = None
        else:
            try:
                context["cannot_update"] = self.object.lock_update(self.request)
            except TypeError:
                # Compatiblity mode for version 20160928 and lower
                context["cannot_update"] = self.object.lock_update()
            try:
                context["cannot_delete"] = self.object.internal_lock_delete(self.request)
            except TypeError:
                # Compatiblity mode for version 20160928 and lower
                context["cannot_delete"] = self.object.internal_lock_delete()

        # Update context
        context.update(self.extra_context)

        if hasattr(self, 'form_ngcontroller'):
            context['form'].set_attribute('ngcontroller', self.form_ngcontroller)

        # Return context
        return context

    def get_context_json(self,c):
        # Decide form
        jc = {}
        if 'form' in c:
            form = c['form']
        else:
            form = None

        # Define json_details
        json_details = bool( getattr( self.request, "json_details", getattr( self, "json_details", False ) ) )

        # Head
        h={}
        o={}
        if c['cannot_delete']: o['cannot_delete'] = c['cannot_delete']
        if c['cannot_update']: o['cannot_update'] = c['cannot_update']

        if o: h['options']=o
        if form: h['bound']=form.is_bound

        if json_details:
            groups = getattr(form,"__groups__",None)
            if groups:
                h['groups']=groups()
            else:
                h['groups']=None
            h['form_name']=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(15))

        jc['head']=h

        # Check version
        meta = {}
        if self.__authtoken:
            meta['version'] = getattr(settings, "VERSION", None)
            meta['version_api'] = getattr(settings, "VERSION_API", None)
        jc['meta']=meta

        # Build the list of forms
        if form:
            # Get forms list
            if 'forms' in c:
                formlist = c['forms']
            else:
                formlist = [form]
        else:
            formlist = None

        # Forms
        generrors={}
        fields={}

        if formlist:
            for formobj in formlist:
                # Set language
                formobj.set_language(self.language)

                # Append to the general list of errors
                if formobj.get_errors():
                    errs = []
                    for err in formobj.get_errors():
                        errs.append(err)
                    generrors["global"] = errs
                # Append list of errors by field
                for f in formobj.errors:
                    generrors[f] = formobj.errors[f]

                # Append to the general list of fields
                for group in formobj.get_groups():
                    for mainfield in group.get("fields",[]):
                        for field in [mainfield]+mainfield.get("fields",[]):
                            # Get the input
                            inp=field.get("input")

                            # Get value
                            if inp.html_name in inp.form.data:
                                inpvalue = inp.form.data[inp.html_name]
                            elif inp.html_name in inp.form.initial:
                                inpvalue = inp.form.initial[inp.html_name]
                            else:
                                inpvalue = ""

                            # Rewrite inpvalues if required
                            if type(inpvalue)==datetime.datetime:
                                # Convert datetime to string
                                inpvalue=inpvalue.strftime(formats.get_format('DATETIME_INPUT_FORMATS', lang=self.language)[0])
                            elif type(inpvalue)==datetime.date:
                                # Convert datetime to string
                                inpvalue=inpvalue.strftime(formats.get_format('DATE_INPUT_FORMATS', lang=self.language)[0])
                            elif type(inpvalue)==datetime.time:
                                # Convert datetime to string
                                inpvalue=inpvalue.strftime(formats.get_format('TIME_INPUT_FORMATS', lang=self.language)[0])

                            if not json_details:
                                fields[inp.html_name] = inpvalue
                            else:
                                # Build a new field
                                newfield={}
                                newfield['for']=inp.id_for_label
                                newfield['type']=inp.field.__class__.__name__.replace("Field","").lower()
                                newfield['html_name']=inp.html_name

                                if newfield['type']=='genrecaptcha':
                                    # Say the widget to work as it was designed (not to use CODENERIX code)
                                    inp.field.widget.legacy = True
                                    # Get html code
                                    newfield['value']=str(inp)
                                else:
                                    newfield['value']=inpvalue

                                if "label" in field:
                                    newfield['label']=field.get("label")
                                notes=[]
                                errors=[]
                                for (f1,f2,dirty,f4,f5,msg) in unlist(inp.errors).data:
                                    if msg and msg!="$message":
                                        if dirty=='$dirty':
                                            # Messages for dirty status (validations for AngularJS)
                                            notes.append(msg)
                                        elif dirty=='$pristine':
                                            # Messages for pristine status (validations from Django)
                                            errors.append(msg)
                                        else:
                                            raise IOError(_("This shouldn't happen, state is not $dirty or $pristine"))
                                if errors: newfield['errors']=errors
                                if notes: newfield['notes']=notes

                                # Limits
                                min_length=getattr(inp.field,"min_length",None)
                                max_length=getattr(inp.field,"max_length",None)
                                required=getattr(inp.field,"required",None)
                                limits={}
                                if min_length: limits['min_length']=min_length
                                if max_length: limits['max_length']=max_length
                                if required: limits['required']=required
                                newfield['limits']=limits

                                # Help
                                help_text=getattr(inp,"help_text",None)
                                if help_text:
                                    newfield['help']=help_text

                                # Attach a the field
                                fields[inp.name]=newfield

        # Save all errors and fields
        if generrors: jc['head']['errors']=generrors
        jc['body']=fields

        # Return json_context
        return jc

    def render_to_response(self, context, **response_kwargs):
        if self.__json_worker:
            # Get json ready context
            answer=self.get_context_json(context)

            # Try to serialize it as a JSON string
            try:
                json_answer=json.dumps(answer)
            except TypeError as  e:
                raise TypeError("The method json_builder() from model '{0}' inside app '{1}' didn't return a JSON serializable object. Error was: {2}".format(self._modelname,self._appname,e))
            # Return the new answer
            return HttpResponse(json_answer,content_type='application/json', **response_kwargs)
        else:
            return super(GenModify, self).render_to_response(context, **response_kwargs)


class GenCreate(GenModify, GenBase, CreateView):
    action_permission = 'add'
    get_template_names_key='add'
    success_url = reverse_lazy("status",kwargs={'status':'accept','answer':''})
    success_url_keys = []
    show_internal_name = True
    extends_base = "codenerix/form.html"


class GenCreateModal(GenCreate):
    get_template_names_key='addmodal'
    show_internal_name = False
    extends_base = "codenerix/form.html"


class GenUpdate(GenModify, GenBase, UpdateView):
    action_permission = 'change'
    get_template_names_key='form'
    success_url = reverse_lazy("status",kwargs={'status':'accept','answer':''})
    success_url_keys = []
    show_internal_name = True

    def get_context_data(self, **kwargs):
        context = super(GenUpdate, self).get_context_data(**kwargs)
        try:
            lock_delete = self.object.internal_lock_delete(self.request)
        except TypeError:
            # Compatiblity mode for version 20160928 and lower
            lock_delete = self.object.internal_lock_delete()
        try:
            lock_update = self.object.lock_update(self.request)
        except TypeError:
            # Compatiblity mode for version 20160928 and lower
            lock_update = self.object.lock_update()

        if lock_delete is not None:
            context["cannot_delete"] = lock_delete
        if lock_update is not None:
            context["cannot_update"] = lock_update

        return context


class GenUpdateModal(GenUpdate):
    get_template_names_key='formmodal'
    show_internal_name = False

class GenDelete(GenModify, GenBase, DeleteView):
    '''
    Define generic methods for all our generic classes
    success_url = {'status':'accept','answer':''})  This is the URL where the view will go if everything goes fine (answer will be autofilled)
    get_template_names_key='delete'                 Sufix added to all templates when templates name resolution is looking for the template
    '''
    #get_template_names_key='delete'
    success_url = reverse_lazy("status",kwargs={'status':'accept','answer':''})
    success_url_keys = []
    action_permission = 'delete'

    def dispatch(self, request, **kwargs):
        '''
        Entry point for this class, here we decide basic stuff
        '''

        # Check if this is a webservice request
        self.__authtoken = (bool( getattr( self.request, "authtoken", False ) ))
        self.__json_worker = self.__authtoken or (self.json is True)
        # Call the base implementation
        return super(GenDelete, self).dispatch(request, **kwargs)

    def delete(self, *args, **kwargs):
        obj = self.get_object()

        try:
            lock = obj.internal_lock_delete(self.request)
        except TypeError:
            # Compatiblity mode for version 20160928 and lower
            lock = obj.internal_lock_delete()

        # Attach object
        if self.__authtoken:

            # Get API field
            if getattr(self, '__api__', None):
                api=self.__api__(self.request)
            elif getattr(self, '__api__', None):
                api=self.object.__api__(self.request)
            else:
                api=getattr(settings,'API_DEFAULT', None)

            # Set the result
            api_obj = self.get_object_api(api, obj)
        else:
            # Set no result
            api_obj = None

        if lock:
            if self.__json_worker:
                json_struct = {"error": lock, "__pk__": obj.pk}
                if self.__authtoken and api_obj is not None:
                    json_struct['__obj__']=api_obj
                json_answer = json.dumps(json_struct)
                return HttpResponse(json_answer,content_type='application/json')
            else:
                return HttpResponseForbidden(lock, content_type="text/plain")
        else:
            try:
                return super(GenDelete, self).delete(*args, **kwargs)
            except ValidationError as e:
                if self.__json_worker:
                    json_struct = {"error": e, "__pk__": obj.pk}
                    if self.__authtoken and api_obj is not None:
                        json_struct['__obj__']=api_obj
                    json_answer = json.dumps(json_struct)
                    return HttpResponse(json_answer,content_type='application/json')
                else:
                    return HttpResponseForbidden(e,content_type="text/plain")


class GenDetail(GenBase, DetailView):
    get_template_names_key='details'
    action_permission = 'detail'

    #by default value of a necesary attribute
    groups=[]

    def dispatch(self, request, **kwargs):
        '''
        Entry point for this class, here we decide basic stuff
        '''

        # Check if this is a REST query to pusth the answer to responde in JSON
        if bool(self.request.META.get('HTTP_X_REST',False)):
            self.json = True

        # Check if this is a REST query to add an element
        if self.request.method in ['PUT','DELETE']:
            if self.request.method == 'PUT':
                action = 'edit'
            else:
                action = 'delete'

            # Set new method
            self.request.method == 'POST'

            # Find the URL
            target = get_class(resolve("{}/{}".format(self.request.META.get("REQUEST_URI"),action)).func)

            # Make sure we will answer as an API
            target.json = True

            # Lets go for it
            return target.as_view()(self.request, pk=kwargs.get('pk'))

        # Detect if we have to answer in json
        self.__authtoken = (bool( getattr( self.request, "authtoken", False ) ))
        self.__json_worker=self.__authtoken or (self.json is True)

        # Check if this is an AJAX request
        if (request.is_ajax() or self.__json_worker) and request.body:
            request.POST = json.loads(request.body)

        # Set class internal variables
        self._setup(request)

        # Call the base implementation
        return super(GenDetail, self).dispatch(request, **kwargs)

    def get_filled_structure(self,subgroup=None):
        '''
        method in charged of filling an structure containing the object fields
        values taking into account the 'group' attribute from the corresponding
        form object, which is necesary to fill the details form as it is configured
        in the 'group' attribute
        '''
        #initilize the result structure
        result = []

        #the object corresponding model content is taken into a dictionary
        object_content = model_to_dict(self.object)

        #generallically some common or specific fields are not interesting
        if not 'exclude_fields' in dir(self):
            self.exclude_fields = []

        self.exclude_fields.append("id")

        for field in (self.exclude_fields):
            if field in object_content.keys():
                object_content.pop(field)
        #following is going to be created an structure with the appropieate caption
        #for every existing field in the current model
        verbose_names = {}
        for field in object_content.keys():
            verbose_names[field] = self.model._meta.get_field(field).verbose_name
        #the found fields in the groups structure are going to be taked into
        #account
        gr_object_content=[]

        if subgroup:
            group_array = subgroup
        else:
            group_array = self.groups

        for group in group_array:

            #raise Exception(group)
            item={}

            item["name"]=smart_text(group[0])
            item["col"]=group[1]
            item_elements = group[2:]

            sublist=[]

            idx=0
            for item_element in item_elements:
                #the element can contains another groups
                if (idx>1) and (type(item_element)==tuple):
                    # Recursive
                    sublist.append(self.get_filled_structure([subgroup]))
                else:
                    filter_field = None
                    # Check if it is a list
                    if type(item_element) == list:
                        # if it is a list, that means that can be found the
                        # corresponding values for colums and any other
                        field = item_element[0]
                        # take into account that field caption can be passed as
                        # third list element
                        if len(item_element) >= 3 and item_element[2]:
                            verbose_names[field] = _(item_element[2])
                        if len(item_element) >= 9:
                            filter_field = item_element[8]
                    else:

                        field = item_element

                    if field not in verbose_names:
                        if field.startswith('get_') and field.endswith('_display'):
                            label_field = remove_getdisplay(field)
                            if self.model:
                                try:
                                    verbose_names[field] = self.model._meta.get_field(label_field).verbose_name
                                except FieldDoesNotExist:
                                    verbose_names[field] = _(label_field)
                            else:
                                verbose_names[field] = _(label_field)
                        else:
                            label_field = field
                            verbose_names[field] = _(label_field)

                    args = {}
                    value = getattr(self.object, field, None)

                    if callable(value):
                        # if 'request' in value.func_code.co_varnames:
                        if 'request' in value.__code__.co_varnames:
                            args['request'] = self.request
                            # Call the method
                        value = value(**args)

                    sublist.append({
                        "name": _(verbose_names[field]),
                        "value": value,
                        "filter": filter_field,
                    })
                    gr_object_content.append(field)

                # Increment index
                idx+=1

            item["value"]=sublist
            result.append(item)

        for field in object_content.keys():
            item={}
            if field not in gr_object_content:
                item["name"]=_(verbose_names[field])
                item["value"]=getattr(self.object, field)
                result.append(item)

        return result

    def get_context_data_html(self,object_property, **kwargs):
        context = super(GenDetail, self).get_context_data(**kwargs)
        context['object_detail']=self.get_filled_structure()

        # Get tabs_autorender information
        self.extra_context['tabs_autorender'] = self.get_tabs_autorender()

        # Check linkedit
        context['linkedit']=getattr(self, 'linkedit', True)

        # Check linkdelete
        context['linkdelete']=getattr(self, 'linkdelete', True)

        # Check linkback
        context['linkback']=getattr(self, 'linkback', True)

        # Check lock delete
        try:
            if "internal_lock_delete" in object_property and self.object.internal_lock_delete(self.request) is not None:
                context["cannot_delete"] = self.object.internal_lock_delete(self.request)
        except TypeError:
            # Compatiblity mode for version 20160928 and lower
            if "internal_lock_delete" in object_property and self.object.internal_lock_delete() is not None:
                context["cannot_delete"] = self.object.internal_lock_delete()

        # Check lock update
        try:
            if "lock_update" in object_property and self.object.lock_update(self.request) is not None:
                context["cannot_update"] = self.object.lock_update(self.request)
        except TypeError:
            # Compatiblity mode for version 20160928 and lower
            if "lock_update" in object_property and self.object.lock_update() is not None:
                context["cannot_update"] = self.object.lock_update()

        # Update context
        context.update(self.extra_context)

        # Return context
        return context

    def get_context_data_json(self,object_property, **kwargs):
        context = super(GenDetail, self).get_context_data(**kwargs)
        #info = self.get_filled_structure()

        datas = json.loads(serializers.serialize('json', [context["object"], ]))[0]
        body = datas["fields"]
        body["pk"] = datas["pk"]

        meta = {}
        meta["gentranslate"] = {}
        for key in context["gentranslate"]:
            meta["gentranslate"][key]=context["gentranslate"][key]
        # Check version
        if self.__authtoken:
            meta['version'] = getattr(settings, "VERSION", None)
            meta['version_api'] = getattr(settings, "VERSION_API", None)

        # Check linkedit
        meta['linkedit']=getattr(self, 'linkedit', True)

        # Check linkdelete
        meta['linkdelete']=getattr(self, 'linkdelete', True)

        # Check linkback
        meta['linkback']=getattr(self, 'linkback', True)

        # Check lock delete
        try:
            if "internal_lock_delete" in object_property and self.object.internal_lock_delete(self.request) is not None:
                meta["cannot_delete"] = self.object.internal_lock_delete(self.request)
            else:
                meta["cannot_delete"] = None
        except TypeError:
            # Compatiblity mode for version 20160928 and lower
            if "internal_lock_delete" in object_property and self.object.internal_lock_delete() is not None:
                meta["cannot_delete"] = self.object.internal_lock_delete()
            else:
                meta["cannot_delete"] = None

        # Check lock update
        try:
            if "lock_update" in object_property and self.object.lock_update(self.request) is not None:
                meta["cannot_update"] = self.object.lock_update(self.request)
            else:
                meta["cannot_update"] = None
        except TypeError:
            # Compatiblity mode for version 20160928 and lower
            if "lock_update" in object_property and self.object.lock_update() is not None:
                meta["cannot_update"] = self.object.lock_update()
            else:
                meta["cannot_update"] = None

        # Update context
        #context.update(self.extra_context)

        ncontext = {
            'meta': meta,
            'body': body,
        }

        # Return context
        return ncontext

    def get_context_data(self, **kwargs):
        object_property = dir(self.object)
        if self.__json_worker:
            return self.get_context_data_json(object_property, **kwargs)
        else:
            return self.get_context_data_html(object_property, **kwargs)


    def render_to_response(self, context, **response_kwargs):

        if self.__json_worker:
            # Try to serialize it as a JSON string
            try:
                json_answer=json.dumps(context)
            except TypeError as  e:
                raise TypeError("Couldn't serialize response from model '{0}' inside app '{1}', I can not return a JSON serializable object. Error was: {2}".format(self._modelname,self._appname,e))
            # Return the new answer
            return HttpResponse(json_answer,content_type='application/json', **response_kwargs)
        else:
            return super(GenDetail, self).render_to_response(context, **response_kwargs)


class GenDetailModal(GenDetail):
    get_template_names_key='detailsmodal'
    extends_base = "codenerix/details.html"


class GenForeignKey(GenBase, View):
    '''
    Every class tha inherit from GenForeignKey must implement 2 attributes and 1 method:
    === ATTRIBUTES ===
    - model = model to use for get_queryset()
    - label = string with "format" like: "{name}" or "{company__name}", the system will render it itself
    === METHOD ===
    - get_foreign(self, queryset, search, filter) where:
        queryset is the queryset ready to use result from model (you shouldn't use another queryset)
        search is the string the user is searching for ( when '*' is given you should return all possible results)
        filter is a dictionary that contains linked fields with their values:
            KEY: linked field name (ng-model name)
            VALUE: actual value from the linked field
        if you get a filter company:3 means your search must filter the results to all that belongs to company:3
    '''

    label_cached = None
    action_permission = 'list'

    def dispatch(self, request, **kwargs):
        # Set class internal variables
        self._setup(request)

        # Call the base implementation
        return super(GenForeignKey, self).dispatch(request, **kwargs)

    def build_label(self, obj):
        # Compile label and save it
        if not self.label_cached:
            # Replace language
            self.label = self.label.replace("<LANGUAGE_CODE>", self.language)
            # Build regex
            regex = re.compile('{[a-zA-Z][_a-zA-Z0-9]*}')
            # Find format
            f = regex.split(self.label)
            k = regex.findall(self.label)
            fmt = f[0]
            keys = []
            for idx, key in enumerate(k):
                fmt += "{{{0}}}{1}".format(idx, f[idx + 1].replace('{', '{{').replace('}', '}}'))
                keys.append(key.replace('{', '').replace('}', ''))
            self.label_cached = (fmt, keys)
        else:
            fmt, keys = self.label_cached

        # Process label
        args = []
        for key in keys:
            objd = obj
            for subkey in key.split("__"):
                objd = getattr(objd, subkey, None)
            args.append(objd)

        # Return final label
        # raise Exception(type(fmt), fmt, args)
        try:
            return fmt.decode('utf-8').format(*args)
        except AttributeError:
            return fmt.format(*args)

    def get_queryset(self):
        return self.model.objects

    def get_label(self, pk):
        # Get queryset
        qs = self.get_queryset()
        # Locate the object
        obj = qs.get(pk=pk)
        # Return the label
        return self.build_label(obj)

    def get_choices(self, choices=[]):
        qs = self.get_queryset()
        if choices:
            if type(choices[0] == dict):
                choices = [x["id"] for x in choices]
            qs = qs.filter(pk__in=choices)
        answer = []
        for e in qs.all():
            answer.append({'id': e.pk, 'label': self.build_label(e)})
        return answer

    def custom_choice(self, obj, info):
        # info['_readonly_'] = []
        # info['_clear_'] = []
        return info

    def get(self, request, *args, **kwargs):

        # Set class internal variables
        self._setup(request)

        # Get data
        search = kwargs.get('search', '')
        filterstxt = self.request.GET.get('filter', '{}')
        filters = json.loads(filterstxt)
        self.filters = filters

        # Empty search string if all where requested
        if search == '*':
            search = ''

        # Get the queryset requested by the user
        qs = self.get_foreign(self.get_queryset(), search, filters)

        # Limit answer
        limit = getattr(settings, "LIMIT_FOREIGNKEY", 100)

        # Build answer
        answer = [{'id': None, 'label': '---------'}]
        qscount = qs.count()
        for e in qs[0:limit]:
            answer.append(self.custom_choice(e, {'id': e.pk, 'label': self.build_label(e)}))
        if qscount > limit:
            answer.append({'id': '', 'label': '...'})

        # Convert the answer
        json_answer = json.dumps({
            "clear": getattr(self, 'clear_fields', []),
            "rows": answer,
            "readonly": getattr(self, 'readonly_fields', [])
        })

        # Send it
        return HttpResponse(json_answer, content_type='application/json')


# === FORMS ===
# We don't use log system when PQPRO_CASSANDRA == TRUE
if not (hasattr(settings, "PQPRO_CASSANDRA") and settings.PQPRO_CASSANDRA):
    from codenerix.models import Log

    class LogList(GenList):
        model = Log
        linkadd = False
        linkedit = True
        show_details = True
        show_modal = True
        extra_context={'menu':['manager','log'],'bread':[_('Manager'),_('Log')]}
        default_ordering="-action_time"
        must_be_superuser=True

    class LogDetails(GenDetailModal, GenDetail):
        model = Log
        linkedit = False
        linkdelete = False
        linkback = True
        exclude_fields = ["action_flag"]
        must_be_superuser=True
        get_template="detailsmodal_log.html"
        groups=[
               (_('Identification'),6,
                    ['action_time',1],
                    ['action',1],
                    ['user',3],
                    ['content_type',4],
                    ['object_id',4],
                    ['object_repr',4],
                    ),
                (_('Changes'),6,
                    ['change_txt',12],
                    ['change_json',12],
                    ),
            ]
