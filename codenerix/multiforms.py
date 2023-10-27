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

from django.db import transaction

# Warning: Q objects are used inside an eval() that you can find somewhere down
from django.db.models import Q  # noqa: F401
from django.http import HttpResponseRedirect


class MultiForm:
    """
    model = Flight                                  # Main model
    form_class = FlightForm                         # Main form
    groups = DepartureForm.__groups__(prefix='DepartureForm_')
        + FlightForm.__groups__(prefix="FlightForm_")
        + ArrivalForm.__groups__(prefix='ArrivalForm_') # Define groups, when declared the system will use one only form without tabs
    forms = [                                       # Define several forms together build with elements:
        (DepartureForm, 'flight', None),            # (ModalForm, 'field name used for linking', filters for the queryset ),
        (None, None, None),                         # (None, None, None), -> MainForm
        (ArrivalForm, 'flight', None)               # This definition is used on CREATE
        ]
    forms = [                                       # This definition is used on UPDATE
        (DepartureForm,'flight','kind="D",alternative=False'),
        (None, None, None),
        (ArrivalForm, 'flight','kind="A",alternative=False')
        ]
    """  # noqa: E501

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if "field_prefix" in self.__dict__:
            kwargs["scope_prefix"] = self.field_prefix
        return kwargs

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests and instantiates blank versions of the form and
        its inline formsets.
        """

        # Prepare base
        if "pk" in kwargs:
            self.object = self.get_object()
        else:
            self.object = None
        form_class = self.get_form_class()

        # Get prefix
        if "field_prefix" in form_class.Meta.__dict__:
            # Get name from the form
            field_prefix = form_class.Meta.field_prefix
        else:
            # Get name from the class
            field_prefix = str(form_class).split("'")[1].split(".")[-1]
        self.field_prefix = field_prefix

        # Build form
        form = self.get_form(form_class)

        # Find groups
        if "groups" in dir(self):
            # Save groups
            groups = self.groups
            # Redefine groups inside the form
            form.__groups__ = lambda: groups
            # Initialize list of fields
            fields = []
        else:
            groups = None

        # Add special prefix support to properly support form independency
        form.add_prefix = (
            lambda fields_name, field_prefix=field_prefix: "%s_%s"
            % (
                field_prefix,
                fields_name,
            )
        )
        if "autofill" not in dir(form.Meta):
            form.Meta.autofill = {}
        if "extend" not in dir(form.Meta):
            form.Meta.extend = {}

        # For every extra form
        forms = []
        position_form_default = 0
        for formelement, linkerfield, modelfilter in self.forms:
            if formelement is None:
                formobj = form
                position_form_default = len(forms)
            else:
                # Locate linked element
                if self.object:
                    related_name = formelement._meta.model._meta.get_field(
                        linkerfield,
                    ).related_query_name()
                    queryset = getattr(self.object, related_name)
                    if modelfilter:
                        queryset = queryset.filter(
                            eval("Q(%s)" % (modelfilter)),
                        )
                    get_method = getattr(queryset, "get", None)
                    if get_method:
                        instance = queryset.get()
                    else:
                        instance = queryset
                else:
                    instance = None

                if "autofill" in dir(formelement.Meta):
                    formname = str(formelement).split(".")[-1].split("'")[0]
                    for key in formelement.Meta.autofill:
                        form.Meta.autofill[
                            "{}_{}".format(formname, key)
                        ] = formelement.Meta.autofill[key]
                if "extend" in dir(formelement.Meta):
                    formname = str(formelement).split(".")[-1].split("'")[0]
                    for key in formelement.Meta.extend:
                        form.Meta.extend[
                            "{}_{}".format(formname, key)
                        ] = formelement.Meta.extend[key]

                # Get prefix
                if "field_prefix" in formelement.Meta.__dict__:
                    # Get name from the form
                    field_prefix = formelement.Meta.field_prefix
                else:
                    # Get name from the class
                    field_prefix = (
                        str(formelement).split("'")[1].split(".")[-1]
                    )
                self.field_prefix = field_prefix

                # Prepare form
                formobj = formelement(instance=instance)
                formobj.form_name = form.form_name

                # Excluded fields
                if "exclude" not in formobj.Meta.__dict__:
                    formobj.Meta.exclude = [linkerfield]
                elif linkerfield not in formobj.Meta.exclude:
                    formobj.Meta.exclude.append(linkerfield)
                if linkerfield in formobj.fields:
                    del formobj.fields[linkerfield]

                # Add special prefix support to properly support
                # form independency
                formobj.add_prefix = (
                    lambda fields_name, field_prefix=field_prefix: "%s_%s"
                    % (field_prefix, fields_name)
                )
                formobj.scope_prefix = field_prefix

            # Save fields to the list
            if groups:
                for field in formobj:
                    fields.append(field)
            else:
                # Add the form to the list of forms
                forms.append(formobj)

        if position_form_default == 0:
            open_tabs = 1
        else:
            open_tabs = 0
        # Remember list of fields
        if groups:
            form.list_fields = fields

        # Add context and return new context
        return self.render_to_response(
            self.get_context_data(
                form=form,
                forms=forms,
                open_tabs=open_tabs,
                position_form_default=position_form_default,
            ),
        )

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance and its inline
        formsets with the passed POST variables and then checking them
        for validity.
        """

        # Prepare base
        if "pk" in kwargs:
            self.object = self.get_object()
        else:
            self.object = None
        form_class = self.get_form_class()

        # Get prefix
        if "field_prefix" in form_class.Meta.__dict__:
            # Get name from the form
            field_prefix = form_class.Meta.field_prefix
            # Initialize list of fields
        else:
            # Get name from the class
            field_prefix = str(form_class).split("'")[1].split(".")[-1]
        self.field_prefix = field_prefix

        # Build the form
        form = self.get_form(form_class)

        # Find groups
        if "groups" in dir(self):
            # Save groups
            groups = self.groups
            # Redefine groups inside the form
            form.__groups__ = lambda: groups
            # Initialize list of fields
            fields = []
        else:
            groups = None

        # Add special prefix support to properly support form independency
        form.add_prefix = (
            lambda fields_name, field_prefix=field_prefix: "%s_%s"
            % (
                field_prefix,
                fields_name,
            )
        )

        # Check validation
        valid = form.is_valid()
        if (not valid) and ("non_field_errors" in dir(self)):
            errors = [
                element[5] for element in list(self.non_field_errors())[:-1]
            ]
        elif form.errors.as_data():
            errors = []
            for element in form.errors.as_data():
                for err in form.errors.as_data()[element][0]:
                    errors.append(err)
        else:
            errors = []

        # For every extra form
        temp_forms = []
        position_form_default = 0
        for formelement, linkerfield, modelfilter in self.forms:
            if formelement is None:
                formobj = form
                position_form_default = len(temp_forms)
            else:
                # Locate linked element
                if self.object:
                    related_name = formelement._meta.model._meta.get_field(
                        linkerfield,
                    ).related_query_name()
                    queryset = getattr(self.object, related_name)
                    if modelfilter:
                        queryset = queryset.filter(
                            eval("Q(%s)" % (modelfilter)),
                        )
                    get_method = getattr(queryset, "get", None)
                    if get_method:
                        instance = queryset.get()
                    else:
                        instance = queryset
                else:
                    instance = None

                # Get prefix
                if "field_prefix" in formelement.Meta.__dict__:
                    # Get name from the form
                    field_prefix = formelement.Meta.field_prefix
                else:
                    # Get name from the class
                    field_prefix = (
                        str(formelement).split("'")[1].split(".")[-1]
                    )
                self.field_prefix = field_prefix

                # Prepare form
                formobj = formelement(
                    instance=instance,
                    data=self.request.POST,
                )
                formobj.form_name = form.form_name

                # Excluded fields
                if "exclude" not in formobj.Meta.__dict__:
                    formobj.Meta.exclude = [linkerfield]
                elif linkerfield not in formobj.Meta.exclude:
                    formobj.Meta.exclude.append(linkerfield)
                if linkerfield in formobj.fields:
                    del formobj.fields[linkerfield]

                # Link it to the main model
                formobj.add_prefix = (
                    lambda fields_name, field_prefix=field_prefix: "%s_%s"
                    % (field_prefix, fields_name)
                )

                # Validate
                valid *= formobj.is_valid()

                # append error
                if not formobj.is_valid() and (
                    "non_field_errors" in dir(formobj)
                ):
                    errors += [
                        element[5]
                        for element in list(formobj.non_field_errors())[:-1]
                    ]

            # Save fields to the list
            if groups:
                for field in formobj:
                    # raise Exception (field.__dict__)
                    if "unblock_t2ime" in field.html_name:
                        raise Exception(field.field.__dict__)
                    fields.append(field)

            # Add a new form
            temp_forms.append((formobj, linkerfield))

        # execute validation specified
        validate_forms = None
        if valid and ("validate" in dir(self)):
            validate_forms = [tform[0] for tform in temp_forms]
            errors = self.validate(*validate_forms)
            # valid = len(errors) == 0
            valid = False
            if errors is None or len(errors) == 0:
                valid = True

        # Remember list of fields
        if groups:
            form.list_fields = fields
            forms = []
        else:
            if validate_forms:
                forms = validate_forms
            else:
                forms = [tform[0] for tform in temp_forms]

        if position_form_default == 0:
            open_tabs = 1
        else:
            open_tabs = 0

        # Check validation result
        if valid:
            # Everything is OK, call valid
            return self.multiform_valid(form, temp_forms)
        else:
            # Something went wrong, attach error and call invalid
            form.list_errors = errors
            return self.multiform_invalid(
                form,
                forms,
                open_tabs,
                position_form_default,
            )

    @transaction.atomic
    def multiform_valid(self, form, forms):
        """
        Called if all forms are valid. Creates a Recipe instance along with
        associated Ingredients and Instructions and then redirects to
        a success page.
        """
        if self.object:
            form.save()
            for formobj, linkerfield in forms:
                if form != formobj:
                    formobj.save()
        else:
            self.object = form.save()
            for formobj, linkerfield in forms:
                if form != formobj:
                    setattr(formobj.instance, linkerfield, self.object)
                    formobj.save()
        return HttpResponseRedirect(self.get_success_url())

    def multiform_invalid(self, form, forms, open_tabs, position_form_default):
        """
        Called if a form is invalid. Re-renders the context data with
        the data-filled forms and errors.
        """
        # return self.render_to_response(
        #   self.get_context_data( form = form, forms = forms )
        # )
        return self.render_to_response(
            self.get_context_data(
                form=form,
                forms=forms,
                open_tabs=open_tabs,
                position_form_default=position_form_default,
            ),
        )
