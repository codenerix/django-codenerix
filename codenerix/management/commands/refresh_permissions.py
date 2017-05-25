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


from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from codenerix.lib.debugger import Debugger


class Command(BaseCommand, Debugger):

    # Show this when the user types help
    help = "Refresh all permissions from a project"
    
    def handle(self, *args, **options):
        
        # Autoconfigure Debugger
        self.set_name("CODENERIX")
        self.set_debug()
        self.debug("Settings permissions for:", color='blue')
        
        # Get all users from the system
        person = None
        for user in User.objects.all():
            self.debug("    > {} ".format(user.username), color='cyan', tail=None)
            if hasattr(user, 'person') and user.person:
                self.debug("OK".format(user.username), color='green', header=None)
                user.person.refresh_permissions()
                person = user.person
            else:
                self.debug("NO PERSON".format(user.username), color='red', header=None)
        
        # Remake groups permissions if we have at least one valid user
        if person:
            self.debug("Refreshing group permissions... ", color='blue', tail=None)
            person.__class__.group_permissions(person.__class__)
            self.debug("DONE", color='green', header=None)
        else:
            self.debug("Can not refresh group permissions because I didn't find a user with a Person", color='red')
