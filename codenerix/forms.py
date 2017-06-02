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

from djng.forms.angular_model import NgModelFormMixin
from djng.forms import NgFormValidationMixin, NgForm, NgModelForm

from django.utils.translation import ugettext as _
from django.forms.widgets import Select

from codenerix.helpers import model_inspect
from codenerix.widgets import StaticSelect, DynamicSelect, DynamicInput, MultiStaticSelect, MultiDynamicSelect

class BaseForm(object):
    
    __language = None
    attributes = {}
    
    def set_language(self, language):
        self.__language = language

    def set_attribute(self, key, value):
        self.attributes[key] = value
    
    def get_name(self):
        # If name atrribute exists in Meta
        if 'name' in self.Meta.__dict__:
            # Try to get name from Meta
            name = self.Meta.name
        else:
            # If not try to find it automatically
            info = model_inspect(self.Meta.model())
            if info['verbose_name']:
                name = info['verbose_name']
            else:
                name = info['modelname']
        return name
    
    def __errors__(self):
        return []
    
    def clean_color(self):
        color = self.cleaned_data["color"]
        if len(color) != 0:
            valores_validos = "#0123456789abcdefABCDEF"
            r = True
            for l in color:
                if l not in valores_validos:
                    r = False
                    break
            if not r or color[0] != "#" or not (len(color) == 4 or len(color) == 7):
                self._errors["color"] = [_("Invalid color")]
                return color
            else:
                return color
        else:
            return color
    
    def get_errors(self):
        # Where to look for fields
        if 'list_errors' in dir(self):
            list_errors = self.list_errors
        else:
            r = self.non_field_errors()
            # list_errors = [element[5] for element in self.non_field_errors()[:-1]]
            list_errors = []
            for element in self.non_field_errors()[:-1]:
                if len(element) >= 5:
                    list_errors.append(element[5])
        return list_errors

    def __groups__(self):
        return []
    
    def get_groups(self, gs=None, processed=[], initial=True):
        '''
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
        '''
        
        # Check if language is set
        if not self.__language:
            raise IOError("ERROR: No language suplied!")
        
        # Initialize the list
        if initial: processed=[]
        # Where to look for fields
        if 'list_fields' in dir(self):
            list_fields=self.list_fields
            check_system="html_name"
        else:
            list_fields=self
            check_system="name"
        
        # Default attributes for fields
        attributes=[
                ('columns',6),
                ('color',None),
                ('bgcolor',None),
                ('textalign',None),
                ('inline',False),       # input in line with label
                ('label',True),
                ('extra',None),
                ('extra_div',None),
                ]
        labels=[x[0] for x in attributes]
        
        # Get groups if none was given
        if gs is None:
            gs=self.__groups__()
        
        # Prepare the answer
        groups=[]

        # html helper for groups and fields
        html_helper = self.html_helper()
        
        # Start processing
        for g in gs:
            token={}
            token['name']=g[0]
            
            if token['name'] in html_helper:
                if 'pre' in html_helper[token['name']]:
                    token["html_helper_pre"] = html_helper[token['name']]['pre']
                if 'post' in html_helper[token['name']]:
                    token["html_helper_post"] = html_helper[token['name']]['post']
            
            styles = g[1]
            if type(styles) is tuple:
                if len(styles)>=1: token['columns']=g[1][0]
                if len(styles)>=2: token['color']=g[1][1]
                if len(styles)>=3: token['bgcolor']=g[1][2]
                if len(styles)>=4: token['textalign']=g[1][3]
                if len(styles)>=5: token['inline']=g[1][4]
                if len(styles)>=7: token['extra']=g[1][5]
                if len(styles)>=8: token['extra_div']=g[1][6]
            else:
                token['columns']=g[1]
            fs=g[2:]
            fields=[]
            for f in fs:
                # Field
                atr={}
                # Decide weather this is a Group or not
                if type(f)==tuple:
                    # Recursive
                    fields+=self.get_groups([list(f)],processed,False)
                else:
                    try:
                        list_type = [str, unicode, ]
                    except NameError:
                        list_type = [str, ]
                    # Check if it is a list
                    if type(f) == list:
                        # This is a field with attributes, get the name
                        field = f[0]
                        
                        if html_helper and token['name'] in html_helper and 'items' in html_helper[token['name']] and field in html_helper[token['name']]['items']:
                            if 'pre' in html_helper[token['name']]['items'][field]:
                                atr["html_helper_pre"] = html_helper[token['name']]['items'][field]['pre']
                            if 'post' in html_helper[token['name']]['items'][field]:
                                atr["html_helper_post"] = html_helper[token['name']]['items'][field]['post']
                        
                        # Process each attribute (if any)
                        dictionary = False
                        for idx, element in enumerate(f[1:]):
                            if type(element) == dict:
                                dictionary = True
                                for key in element.keys():
                                    if key in labels:
                                        atr[key] = element[key]
                                    else:
                                        raise IOError("Unknown attribute '{0}' as field '{1}' in list of fields".format(key, field))
                            else:
                                if not dictionary:
                                    if element is not None:
                                        atr[attributes[idx][0]] = element
                                else:
                                    raise IOError("We already processed a dicionary element in this list of fields, you can not add anoother type of elements to it, you must keep going with dictionaries")
                    elif type(f) in list_type:
                        field = f
                    else:
                        raise IOError("Uknown element type '{0}' inside group '{1}'".format(type(f), token['name']))
                    
                    # Get the Django Field object
                    found=None
                    for infield in list_fields:
                        if infield.__dict__[check_system]==field:
                            found=infield
                            break
                    
                    if found:
                        # Fill base attributes
                        atr['name']=found.html_name
                        atr['input']=found
                        # Autocomplete
                        if 'autofill' in dir(self.Meta):
                            autofill=self.Meta.autofill.get(found.html_name,None)
                            atr['autofill']=autofill
                            if autofill:
                                # Check format of the request
                                autokind=autofill[0]
                                if type(autokind)==str:
                                    # Get old information
                                    wattrs=found.field.widget.attrs
                                    wrequired=found.field.widget.is_required

                                    # Using new format
                                    if autokind=='select':
                                        # If autofill is True for this field set the DynamicSelect widget
                                        found.field.widget=DynamicSelect(wattrs)
                                    elif autokind=='multiselect':
                                        # If autofill is True for this field set the DynamicSelect widget
                                        found.field.widget=MultiDynamicSelect(wattrs)
                                    elif autokind=='input':
                                        # If autofill is True for this field set the DynamicSelect widget
                                        found.field.widget=DynamicInput(wattrs)
                                    else:
                                        raise IOError("Autofill filled using new format but autokind is '{}' and I only know 'input' or 'select'".format(autokind))

                                    # Configure the field
                                    found.field.widget.is_required=wrequired
                                    found.field.widget.form_name=self.form_name
                                    found.field.widget.field_name=infield.html_name
                                    found.field.widget.autofill_deepness=autofill[1]
                                    found.field.widget.autofill_url=autofill[2]
                                    found.field.widget.autofill=autofill[3:]    
                                else:
                                    # Get old information [COMPATIBILITY WITH OLD VERSION]
                                    wattrs=found.field.widget.attrs
                                    wrequired=found.field.widget.is_required
                                    # If autofill is True for this field set the DynamicSelect widget
                                    found.field.widget=DynamicSelect(wattrs)
                                    found.field.widget.is_required=wrequired
                                    found.field.widget.form_name=self.form_name
                                    found.field.widget.field_name=infield.html_name
                                    found.field.widget.autofill_deepness=autofill[0]
                                    found.field.widget.autofill_url=autofill[1]
                                    found.field.widget.autofill=autofill[2:]
                        else:
                            
                            # Set we don't have autofill for this field
                            atr['autofill']=None
                        
                        # Check if we have to replace the widget with a newer one
                        if isinstance(found.field.widget, Select) and not isinstance(found.field.widget, DynamicSelect):
                            wattrs=found.field.widget.attrs
                            wrequired=found.field.widget.is_required
                            if not isinstance(found.field.widget, MultiStaticSelect):
                                found.field.widget=StaticSelect(wattrs)
                            found.field.widget.choices = found.field.choices
                            found.field.widget.is_required=wrequired
                            found.field.widget.form_name=self.form_name
                            found.field.widget.field_name=infield.html_name
                        
                        # Fill all attributes
                        for (attribute,default) in attributes:
                            if attribute not in atr.keys():
                                atr[attribute]=default
                        # Fill label
                        if atr['label'] is True:
                            atr['label']=found.label
                        # Set language
                        flang = getattr(found.field, "set_language", None)
                        if flang:
                            flang(self.__language)
                        flang = getattr(found.field.widget, "set_language", None)
                        if flang:
                            flang(self.__language)
                        # Attach the element
                        fields.append(atr)
                        # Remember we have processed it
                        processed.append(found.__dict__[check_system])
                    else:
                        raise IOError("Unknown field '{0}' specified in group '{1}'".format(f,token['name']))
            
            token['fields']=fields
            groups.append(token)
        
        # Add the rest of attributes we didn't use yet
        if initial:
            fields=[]
            for infield in list_fields:
                if infield.__dict__[check_system] not in processed:
                    atr={}
                    # Fill base attributes
                    atr['name']=infield.html_name
                    atr['input']=infield
                    if 'autofill' in dir(self.Meta):
                        autofill=self.Meta.autofill.get(infield.html_name,None)
                        atr['autofill']=autofill
                        if autofill:
                            # Check format of the request
                            autokind=autofill[0]
                            if type(autokind)==str:
                                # Get old information
                                wattrs=infield.field.widget.attrs
                                wrequired=infield.field.widget.is_required

                                # Using new format
                                if autokind=='select':
                                    # If autofill is True for this field set the DynamicSelect widget
                                    infield.field.widget=DynamicSelect(wattrs)
                                elif autokind=='multiselect':
                                    # If autofill is True for this field set the DynamicSelect widget
                                    infield.field.widget=MultiDynamicSelect(wattrs)
                                elif autokind=='input':
                                    # If autofill is True for this field set the DynamicSelect widget
                                    infield.field.widget=DynamicInput(wattrs)
                                else:
                                    raise IOError("Autofill filled using new format but autokind is '{}' and I only know 'input' or 'select'".format(autokind))

                                # Configure the field
                                infield.field.widget.is_required=wrequired
                                infield.field.widget.form_name=self.form_name
                                infield.field.widget.field_name=infield.html_name
                                infield.field.widget.autofill_deepness=autofill[1]
                                infield.field.widget.autofill_url=autofill[2]
                                infield.field.widget.autofill=autofill[3:]    
                            else:
                                # Get old information [COMPATIBILITY WITH OLD VERSION]
                                wattrs=infield.field.widget.attrs
                                wrequired=infield.field.widget.is_required
                                # If autofill is True for this field set the DynamicSelect widget
                                infield.field.widget=DynamicSelect(wattrs)
                                infield.field.widget.is_required=wrequired
                                infield.field.widget.form_name=self.form_name
                                infield.field.widget.field_name=infield.html_name
                                infield.field.widget.autofill_deepness=autofill[0]
                                infield.field.widget.autofill_url=autofill[1]
                                infield.field.widget.autofill=autofill[2:]
                    else:
                        
                        # Set we don't have autofill for this field
                        atr['autofill']=None
                    
                    # Check if we have to replace the widget with a newer one
                    if isinstance(infield.field.widget, Select) and not isinstance(infield.field.widget, DynamicSelect):
                        wattrs=infield.field.widget.attrs
                        wrequired=infield.field.widget.is_required
                        if not isinstance(infield.field.widget, MultiStaticSelect):
                            infield.field.widget=StaticSelect(wattrs)
                        infield.field.widget.choices = infield.field.choices
                        infield.field.widget.is_required=wrequired
                        infield.field.widget.form_name=self.form_name
                        infield.field.widget.field_name=infield.html_name
                    
                    # Fill all attributes
                    for (attribute,default) in attributes:
                        if attribute not in atr.keys():
                            atr[attribute]=default
                    # Fill label
                    if atr['label'] is True:
                        atr['label']=infield.label
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
                groups.append({'name':None,'columns':12,'fields':fields})
        
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
        """
        return {}

class GenModelForm(BaseForm, NgModelFormMixin, NgFormValidationMixin, NgModelForm):
    pass

class GenForm(BaseForm, NgFormValidationMixin, NgForm):
    add_djng_error = False
    
    class Meta:
        name=""

