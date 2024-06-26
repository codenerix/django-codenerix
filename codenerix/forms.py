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

from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import NullBooleanField
from django.forms.widgets import CheckboxInput, Select, SelectMultiple
from django.utils.translation import gettext as _

from codenerix.djng import NgForm, NgFormValidationMixin, NgModelForm
from codenerix.djng.angular_model import NgModelFormMixin
from codenerix.helpers import model_inspect
from codenerix.widgets import (
    DynamicInput,
    DynamicSelect,
    MultiDynamicSelect,
    MultiStaticSelect,
    StaticSelect,
)


class BaseForm:
    def __init__(self, *args, **kwargs):
        self.__language = None
        self.attributes = {}
        self.__codenerix_uuid = None
        self.__codenerix_request = None
        return super().__init__(*args, **kwargs)

    def set_language(self, language):
        self.__language = language

    def set_attribute(self, key, value):
        self.attributes[key] = value

    def get_name(self):
        # If name atrribute exists in Meta
        if "name" in self.Meta.__dict__:
            # Try to get name from Meta
            name = self.Meta.name
        else:
            # If not try to find it automatically
            info = model_inspect(self.Meta.model())
            if info["verbose_name"]:
                name = info["verbose_name"]
            else:
                name = info["modelname"]
        return name

    def __errors__(self):
        return []

    def clean(self):
        for field in self.fields:
            # If field not found in cleaned_data, lets try to validate the
            # value directly
            if field not in self.cleaned_data:
                # If widget is SelectMultiple remake the cleaned_data
                if isinstance(self.fields[field].widget, SelectMultiple):
                    # Validate the pks is a list of positive integers
                    pks = self.data.get(field)
                    if pks:
                        try:
                            pks = [int(pk) for pk in pks]
                        except ValueError as e:
                            msg = _("Invalid ID detected in SelectMultiple")
                            if settings.DEBUG:
                                msg += f": {e}"
                            raise ValidationError(msg)
                    else:
                        pks = []

                    # Set the cleaned_data as a queryset with the
                    # selected values
                    self.cleaned_data[field] = self.fields[
                        field
                    ].choices.queryset.filter(pk__in=pks)

                    # If field was in errors, remove it
                    if field in self._errors:
                        self._errors.pop(field)

        # Call the parent method normally
        super().clean()

    # def clean_dev(self):
    #     print("clean")
    #     # print all fields being verified
    #     print(self.errors)
    #     print(type(self.errors))

    #     for field in self.fields:
    #         print(f"field: {field}")
    #         print(f"field errors: {self.errors.get(field)}")
    #         # show the value of the field
    #         print(f"field value: {self.data.get(field)}")
    #         # show the type of the field
    #         print(f"field type: {self.fields[field].__class__}")
    #         # show the widget of the field
    #         print(f"field widget: {self.fields[field].widget.__class__}")
    #         # if field not found in cleaned_data, get the post value
    #         if field not in self.cleaned_data:
    #             # if widget is selectmultiple remake the cleaned_data
    #             if isinstance(self.fields[field].widget, SelectMultiple):
    #                 # Show the model this field is related to
    #                 for choice in self.fields[field].choices:
    #                     print(f"choice: {choice} - {choice[0]}")
    #                 print(dir(self.fields[field].choices))
    #                 self.cleaned_data[field] = self.fields[
    #                     field
    #                 ].choices.queryset.filter(pk__in=self.data.get(field))
    #                 if field in self._errors:
    #                     self._errors.pop(field)
    #         # show the type of the cleaned_data
    #         print(f"field errors: {self.errors.get(field)}")
    #         print(f"cleaned_data type: {self.cleaned_data[field].__class__}")
    #         print(f"field value: {self.cleaned_data[field]}")
    #         print("")

    #     # Call the parent method
    #     super().clean()

    #     # Get the errors
    #     errors = self.get_errors()

    #     # If there are errors
    #     if errors:
    #         # Raise an error
    #         raise OSError(errors)

    def clean_color(self):
        color = self.cleaned_data["color"]
        if len(color) != 0:
            valores_validos = "#0123456789abcdefABCDEF"
            r = True
            for lt in color:
                if lt not in valores_validos:
                    r = False
                    break
            if (
                not r
                or color[0] != "#"
                or not (len(color) == 4 or len(color) == 7)
            ):
                self._errors["color"] = [_("Invalid color")]
                return color
            else:
                return color
        else:
            return color

    def get_errors(self):
        # Where to look for fields
        if "list_errors" in dir(self):
            list_errors = self.list_errors
        else:
            # r = self.non_field_errors()
            # list_errors = [
            #   element[5]
            #   for element in list(self.non_field_errors())[:-1]
            # ]
            list_errors = []
            for element in list(self.non_field_errors())[:-1]:
                if len(element) >= 5:
                    list_errors.append(element[5])
        return list_errors

    def get_extends(self, name, userextend):
        # Set extended variables
        if userextend:
            extends = []
            for fieldextend in userextend:
                extends.append("{}__{}".format(name, fieldextend))
        else:
            extends = None
        return extends

    def __groups__(self):
        return []

    @property
    def codenerix_uuid(self):
        return self.__codenerix_uuid

    @codenerix_uuid.setter
    def codenerix_uuid(self, uuid):
        self.__codenerix_uuid = uuid
        return uuid

    @property
    def codenerix_request(self):
        return self.__codenerix_request

    @codenerix_request.setter
    def codenerix_request(self, request):
        self.__codenerix_request = request
        return request

    def get_groups(self, gs=None, processed=[], initial=True):
        """
        <--------------------------------------- 12 columns ------------------------------------>
                    <--- 6 columns --->                           <--- 6 columns --->
         ------------------------------------------   ------------------------------------------
        | Info                                     | | Personal                                 |
        |==========================================| |==========================================|
        |  -----------------   ------------------  | |                                          |
        | | Passport        | | Name             | | | Phone                          Zipcode   |
        | |=================| | [.....]  [.....] | | | [...........................]  [.......] |
        | | CID     Country | | <- 6 ->  <- 6 -> | | |       <--- 8 columns --->      <-4 col-> |
        | | [.....] [.....] | |                  | | |                                          |
        | | <- 6 -> <- 6 -> |  -----------------   | | Address                                  |
        |  -----------------                       | | [.....................................]  |
         ------------------------------------------  |           <--- 12 columns --->           |
                                                     | [..] number                              |
                                                     |           <--- 12 columns --->           |
                                                     |                                          |
                                                      ------------------------------------------
        group = [
                (_('Info'),(6,'#8a6d3b','#fcf8e3','center'),
                    (_('Identification'),6,
                        ["cid",6],
                        ["country",6],
                    ),
                    (None,6,
                        ["name",None,6],
                        ["surname",None,6,False],
                    ),
                ),
                (_('Personal'),6,
                    ["phone",None,8],
                    ["zipcode",None,4],
                    ["address",None,12],
                    ["number",None,12, True],
                ),
            ]

        Group: it is defined as tuple with 3 or more elements:
            Grammar: (<Name>, <Attributes>, <Element1>, <Element2>, ..., <ElementN>)
            If <Name> is None: no name will be given to the group and no panel decoration will be shown
            If <Size in columns> is None: default of 6 will be used

            <Attributes>:
                it can be an integer that represent the size in columns
                it can be a tuple with several attributes where each element represents:
                    (<Size in columns>,'#<Font color>','#<Background color>','<Alignment>')

            <Element>:
                it can be a Group
                it can be a Field

            Examples:
            ('Info', 6, ["name",6], ["surname",6]) -> Info panel using 6 columns with 2 boxes 6 columns for each with name and surname inputs
            ('Info', (6,None,'#fcf8e3','center'), ["name",6], ["surname",6]) -> Info panel using 6 columns with a yellow brackground in centered title, 2 boxes, 6 columns for each with name and surname inputs
            ('Info', 12, ('Name', 6, ["name",12]), ('Surname',6, ["surname",12])) -> Info panel using 12 columns with 2 panels inside
              of 6 columns each named "Name" and "Surname" and inside each of them an input "name" and "surname" where it belongs.

        Field: must be a list with at least 1 element in it:
            Grammar: [<Name of field>, <Size in columns>, <Label>]

            <Name of field>:
                This must be filled always
                It is the input's name inside the form
                Must exists as a form element or as a grouped form element

            <Size in columns>:
                Size of the input in columns
                If it is not defined or if it is defined as None: default of 6 will be used

            <Label>:
                It it is defined as False: the label for this field will not be shown
                If it is not defined or if it is defined as None: default of True will be used (default input's label will be shown)
                If it is a string: this string will be shown as a label

            Examples:
            ['age']                             Input 'age' will be shown with 6 columns and its default label
            ['age',8]                           Input 'age' will be shown with 8 columns and its default label
            ['age', None, False]                Input 'age' will be shown with 6 columns and NO LABEL
            ['age',8,False]                     Input 'age' will be shown with 8 columns and NO LABEL
            ['age',8,_("Age in days")]          Input 'age' will be shown with 8 columns and translated label text "Age in days" to user's language
            ['age',8,_("Age in days"), True]    Input 'age' will be shown with 8 columns and translated label text "Age in days" to user's language, and input inline with label
            ['age',6, None, None, None, None, None, ["ng-click=functionjs('param1')", "ng-change=functionjs2()"]]    Input 'age' with extras functions
            ['age',None,None,None,None, 'filter']    Input 'age' with extras filter ONLY DETAILS
            ['age',6, {'color': 'red'}          Input 'age' will be shown with red title

        Meta:
        =====
        - autofill: autofill system (CODENERIX)
        - extend: extended variables system (CODENERIX)
            Example: {"attr1": ["subattr1", "subattr2"]} -> it will inject in the scope attributes "subattr1" and "subattr2" from "object.attr1" if object is available (GenUpdate)
        - widgets: widgets system (DJANGO)
        """  # noqa: E501

        # Check if language is set
        if not self.__language:
            raise OSError("ERROR: No language suplied!")

        # Initialize the list
        if initial:
            processed = []

        # Where to look for fields
        if "list_fields" in dir(self):
            list_fields = self.list_fields
            check_system = "html_name"
        else:
            list_fields = self
            check_system = "name"

        # Default attributes for fields
        attributes = [
            ("columns", 6),
            ("color", None),
            ("bgcolor", None),
            ("textalign", None),
            ("inline", False),  # input in line with label
            ("label", True),
            ("extra", None),
            ("extra_div", None),
            ("foreign_info", {}),
        ]
        labels = [x[0] for x in attributes]

        # Get groups if none was given
        if gs is None:
            gs = self.__groups__()

        # Prepare the answer
        groups = []

        # Prepare focus control
        focus_first = None
        focus_must = None

        # html helper for groups and fields
        html_helper = self.html_helper()

        # Start processing
        for g in gs:
            token = {}
            token["name"] = g[0]

            if token["name"] in html_helper:
                if "pre" in html_helper[token["name"]]:
                    token["html_helper_pre"] = html_helper[token["name"]][
                        "pre"
                    ]
                if "post" in html_helper[token["name"]]:
                    token["html_helper_post"] = html_helper[token["name"]][
                        "post"
                    ]

            styles = g[1]
            if isinstance(styles, tuple):
                if len(styles) >= 1:
                    token["columns"] = g[1][0]
                if len(styles) >= 2:
                    token["color"] = g[1][1]
                if len(styles) >= 3:
                    token["bgcolor"] = g[1][2]
                if len(styles) >= 4:
                    token["textalign"] = g[1][3]
                if len(styles) >= 5:
                    token["inline"] = g[1][4]
                if len(styles) >= 7:
                    token["extra"] = g[1][5]
                if len(styles) >= 8:
                    token["extra_div"] = g[1][6]
            else:
                token["columns"] = g[1]
            fs = g[2:]
            fields = []
            for f in fs:
                # Field
                atr = {}
                # Decide weather this is a Group or not
                if isinstance(f, tuple):
                    # Recursive
                    fields += self.get_groups([list(f)], processed, False)
                else:
                    try:
                        list_type = [
                            str,
                            unicode,
                        ]
                    except NameError:
                        list_type = [
                            str,
                        ]
                    # Check if it is a list
                    if isinstance(f, list):
                        # This is a field with attributes, get the name
                        field = f[0]

                        if (
                            html_helper
                            and token["name"] in html_helper
                            and "items" in html_helper[token["name"]]
                            and field in html_helper[token["name"]]["items"]
                        ):
                            if (
                                "pre"
                                in html_helper[token["name"]]["items"][field]
                            ):
                                atr["html_helper_pre"] = html_helper[
                                    token["name"]
                                ]["items"][field]["pre"]
                            if (
                                "post"
                                in html_helper[token["name"]]["items"][field]
                            ):
                                atr["html_helper_post"] = html_helper[
                                    token["name"]
                                ]["items"][field]["post"]

                        # Process each attribute (if any)
                        dictionary = False
                        for idx, element in enumerate(f[1:]):
                            if isinstance(element, dict):
                                dictionary = True
                                for key in element.keys():
                                    if key in labels:
                                        atr[key] = element[key]
                                    else:
                                        raise OSError(
                                            f"Unknown attribute '{key}' as "
                                            f"field '{field}' in list "
                                            "of fields",
                                        )
                            else:
                                if not dictionary:
                                    if element is not None:
                                        atr[attributes[idx][0]] = element
                                else:
                                    raise OSError(
                                        "We already processed a dicionary "
                                        "element in this list of fields, you "
                                        "can not add anoother type of "
                                        "elements to it, you must keep going "
                                        "with dictionaries",
                                    )
                    elif type(f) in list_type:
                        field = f
                    else:
                        raise OSError(
                            f"Uknown element type '{type(f)}' inside "
                            f"group '{token['name']}'",
                        )

                    # Get the Django Field object
                    found = None
                    foundbool = False
                    userwidget = None
                    userextend = None
                    for infield in list_fields:
                        if infield.__dict__[check_system] == field:
                            found = infield
                            foundbool = True

                            # Check if the user specified a extend
                            if "widgets" in dir(self.Meta):
                                userwidget = self.Meta.widgets.get(field, None)
                            # Check if the user specified a extend
                            if "extend" in dir(self.Meta):
                                userextend = self.Meta.extend.get(field, None)
                            break

                    if foundbool:
                        # Get attributes (required and original attributes)
                        wrequired = found.field.widget.is_required
                        wattrs = found.field.widget.attrs

                        # Fill base attributes
                        atr["name"] = found.html_name
                        atr["input"] = found
                        atr["inputbool"] = foundbool
                        atr["focus"] = False
                        atr["extend"] = self.get_extends(
                            found.html_name,
                            userextend,
                        )

                        # Set focus
                        if focus_must is None:
                            if focus_first is None:
                                focus_first = atr
                            if wrequired:
                                focus_must = atr

                        # Autocomplete
                        if "autofill" in dir(self.Meta):
                            autofill = self.Meta.autofill.get(
                                found.html_name,
                                None,
                            )
                            atr["autofill"] = autofill

                            if autofill:
                                # Check format of the request
                                autokind = autofill[0]
                                if isinstance(autokind, str):
                                    # Replace widget if the user didn't
                                    # define any
                                    if not userwidget:
                                        # Using new format
                                        if autokind == "select":
                                            # If autofill is True for this
                                            # field set the DynamicSelect
                                            # widget
                                            found.field.widget = DynamicSelect(
                                                wattrs,
                                            )

                                        elif autokind == "multiselect":
                                            # If autofill is True for this
                                            # field set the DynamicSelect
                                            # widget
                                            found.field.widget = (
                                                MultiDynamicSelect(wattrs)
                                            )

                                        elif autokind == "input":
                                            # If autofill is True for this
                                            # field set the DynamicSelect
                                            # widget
                                            found.field.widget = DynamicInput(
                                                wattrs,
                                            )

                                        else:
                                            raise OSError(
                                                "Autofill filled using new "
                                                "format but autokind is "
                                                f"'{autokind}' and I only "
                                                "know 'input' or 'select'",
                                            )

                                    # Configure widget
                                    found.field.widget.is_required = wrequired
                                    found.field.widget.form_name = (
                                        self.form_name
                                    )
                                    found.field.widget.field_name = (
                                        infield.html_name
                                    )
                                    found.field.widget.autofill_deepness = (
                                        autofill[1]
                                    )
                                    found.field.widget.autofill_url = autofill[
                                        2
                                    ]
                                    found.field.widget.autofill = autofill[3:]

                                else:
                                    # Get old information [COMPATIBILITY WITH
                                    # OLD VERSION]

                                    # Replace widget if the user didn't
                                    # define any
                                    if not userwidget:
                                        # If autofill is True for this field
                                        # set the DynamicSelect widget
                                        found.field.widget = DynamicSelect(
                                            wattrs,
                                        )

                                    # Configure widget
                                    found.field.widget.is_required = wrequired
                                    found.field.widget.form_name = (
                                        self.form_name
                                    )
                                    found.field.widget.field_name = (
                                        infield.html_name
                                    )
                                    found.field.widget.autofill_deepness = (
                                        autofill[0]
                                    )
                                    found.field.widget.autofill_url = autofill[
                                        1
                                    ]
                                    found.field.widget.autofill = autofill[2:]
                        else:
                            # Set we don't have autofill for this field
                            atr["autofill"] = None

                        # Check if we have to replace the widget with a
                        # newer one
                        if isinstance(
                            found.field.widget,
                            Select,
                        ) and not isinstance(
                            found.field.widget,
                            DynamicSelect,
                        ):
                            # Replace widget if the user didn't define any and
                            # we haven't done yet
                            if (
                                (not userwidget)
                                and (
                                    not isinstance(
                                        found.field.widget,
                                        MultiStaticSelect,
                                    )
                                )
                                and (
                                    not isinstance(
                                        found.field.widget,
                                        MultiDynamicSelect,
                                    )
                                )
                            ):
                                if isinstance(
                                    found.field.widget,
                                    SelectMultiple,
                                ):
                                    found.field.widget = MultiStaticSelect(
                                        wattrs,
                                    )
                                else:
                                    found.field.widget = StaticSelect(wattrs)
                            if hasattr(
                                found.field.widget,
                                "choices",
                            ) and hasattr(found.field, "choices"):
                                found.field.widget.choices = (
                                    found.field.choices
                                )
                            found.field.widget.is_required = wrequired
                            found.field.widget.form_name = self.form_name
                            found.field.widget.field_name = infield.html_name

                        # Fill all attributes
                        for attribute, default in attributes:
                            if attribute not in atr.keys():
                                atr[attribute] = default

                        # Check if we have to remove foreignkey buttons
                        if isinstance(
                            found.field.widget,
                            SelectMultiple,
                        ):
                            atr["foreign_info"] = None

                        # Fill label
                        if atr["label"] is True:
                            atr["label"] = found.label
                        # Set language
                        flang = getattr(found.field, "set_language", None)
                        if flang:
                            flang(self.__language)
                        flang = getattr(
                            found.field.widget,
                            "set_language",
                            None,
                        )
                        if flang:
                            flang(self.__language)
                        # Attach the element
                        fields.append(atr)
                        # Remember we have processed it
                        processed.append(found.__dict__[check_system])
                    else:
                        raise OSError(
                            f"Unknown field '{f}' specified in "
                            f"group '{token['name']}'",
                        )

            token["fields"] = fields
            groups.append(token)

        # Add the rest of attributes we didn't use yet
        if initial:
            fields = []
            for infield in list_fields:
                if infield.__dict__[check_system] not in processed:
                    # Check if the user specified a widget
                    if "widgets" in dir(self.Meta):
                        userwidget = self.Meta.widgets.get(
                            infield.html_name,
                            None,
                        )
                    else:
                        userwidget = None

                    # Check if the user specified a extend
                    if "extend" in dir(self.Meta):
                        userextend = self.Meta.extend.get(
                            infield.html_name,
                            None,
                        )
                    else:
                        userextend = None

                    # Get attributes (required and original attributes)
                    wattrs = infield.field.widget.attrs
                    wrequired = infield.field.widget.is_required

                    # Prepare attr
                    atr = {}

                    # Fill base attributes
                    atr["name"] = infield.html_name
                    atr["input"] = infield
                    atr["inputbool"] = True
                    atr["focus"] = False
                    atr["extend"] = self.get_extends(
                        infield.html_name,
                        userextend,
                    )

                    # Set focus
                    if focus_must is None:
                        if focus_first is None:
                            focus_first = atr
                        if wrequired:
                            focus_must = atr

                    # Autocomplete
                    if "autofill" in dir(self.Meta):
                        autofill = self.Meta.autofill.get(
                            infield.html_name,
                            None,
                        )
                        atr["autofill"] = autofill

                        if autofill:
                            # Check format of the request
                            autokind = autofill[0]

                            if isinstance(autokind, str):
                                # Get old information

                                # Replace widget if the user didn't define any
                                if not userwidget:
                                    # Using new format
                                    if autokind == "select":
                                        # If autofill is True for this field
                                        # set the DynamicSelect widget
                                        infield.field.widget = DynamicSelect(
                                            wattrs,
                                        )
                                    elif autokind == "multiselect":
                                        # If autofill is True for this field
                                        # set the DynamicSelect widget
                                        infield.field.widget = (
                                            MultiDynamicSelect(wattrs)
                                        )
                                    elif autokind == "input":
                                        # If autofill is True for this field
                                        # set the DynamicSelect widget
                                        infield.field.widget = DynamicInput(
                                            wattrs,
                                        )
                                    else:
                                        raise OSError(
                                            "Autofill filled using new "
                                            "format but autokind is "
                                            f"'{autokind}' and I only know "
                                            "'input' or 'select'",
                                        )

                                # Configure widget
                                infield.field.widget.is_required = wrequired
                                infield.field.widget.form_name = self.form_name
                                infield.field.widget.field_name = (
                                    infield.html_name
                                )
                                infield.field.widget.autofill_deepness = (
                                    autofill[1]
                                )
                                infield.field.widget.autofill_url = autofill[2]
                                infield.field.widget.autofill = autofill[3:]
                            else:
                                # Get old information [COMPATIBILITY WITH
                                # OLD VERSION]

                                # Replace widget if the user didn't define any
                                if not userwidget:
                                    # If autofill is True for this field set
                                    # the DynamicSelect widget
                                    infield.field.widget = DynamicSelect(
                                        wattrs,
                                    )

                                # Configure widget
                                infield.field.widget.is_required = wrequired
                                infield.field.widget.form_name = self.form_name
                                infield.field.widget.field_name = (
                                    infield.html_name
                                )
                                infield.field.widget.autofill_deepness = (
                                    autofill[0]
                                )
                                infield.field.widget.autofill_url = autofill[1]
                                infield.field.widget.autofill = autofill[2:]
                    else:
                        # Set we don't have autofill for this field
                        atr["autofill"] = None

                    # Check if we have to replace the widget with a newer one
                    if isinstance(
                        infield.field.widget,
                        Select,
                    ) and not isinstance(infield.field.widget, DynamicSelect):
                        # Replace widget if the user didn't define any
                        if not userwidget:
                            if isinstance(infield.field, NullBooleanField):
                                infield.field.widget = CheckboxInput(wattrs)
                            elif not isinstance(
                                infield.field.widget,
                                MultiStaticSelect,
                            ) and not isinstance(
                                infield.field.widget,
                                MultiDynamicSelect,
                            ):
                                if isinstance(
                                    infield.field.widget,
                                    SelectMultiple,
                                ):
                                    infield.field.widget = MultiStaticSelect(
                                        wattrs,
                                    )
                                else:
                                    infield.field.widget = StaticSelect(wattrs)

                        # Configure widget
                        if hasattr(
                            infield.field.widget,
                            "choices",
                        ) and hasattr(infield.field, "choices"):
                            infield.field.widget.choices = (
                                infield.field.choices
                            )
                        infield.field.widget.is_required = wrequired
                        infield.field.widget.form_name = self.form_name
                        infield.field.widget.field_name = infield.html_name

                    # Fill all attributes
                    for attribute, default in attributes:
                        if attribute not in atr.keys():
                            atr[attribute] = default

                    # Check if we have to remove foreignkey buttons
                    if isinstance(
                        infield.field.widget,
                        SelectMultiple,
                    ):
                        atr["foreign_info"] = None

                    # Fill label
                    if atr["label"] is True:
                        atr["label"] = infield.label
                    # Set language
                    flang = getattr(infield.field, "set_language", None)
                    if flang:
                        flang(self.__language)
                    flang = getattr(infield.field.widget, "set_language", None)
                    if flang:
                        flang(self.__language)
                    # Attach the attribute
                    fields.append(atr)

            # Save the new elements
            if fields:
                groups.append({"name": None, "columns": 12, "fields": fields})

        # Set focus
        if focus_must:
            focus_must["focus"] = True
        elif focus_first is not None:
            focus_first["focus"] = True

        # Return the resulting groups
        return groups

    def html_helper(self):
        """
        g={'Group Name':{
            'pre': 'text pre div',
            'post': 'text post div',
            'items': {
                'input name':{'pre': 'text pre name', 'post': 'text post name'},
                'example':{'pre': '<p>text <b>for</b> help</p>', 'post': '<div>more help</div>'},
                }
            }
        }
        """  # noqa: E501
        return {}


class GenModelForm(
    BaseForm,
    NgModelFormMixin,
    NgFormValidationMixin,
    NgModelForm,
):
    def save(self, *args, **kwargs):
        # Prepare the instance
        self.instance.codenerix_uuid = self.codenerix_uuid
        self.instance.codenerix_request = self.codenerix_request
        # Save the object
        obj = super().save(*args, **kwargs)
        # Return the object
        return obj

    pass


class GenForm(BaseForm, NgFormValidationMixin, NgForm):
    add_djng_error = False

    class Meta:
        name = ""
