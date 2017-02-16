.. _class-genforeignkey:

GenForeignKey
=============

.. code:: python
    
    from codenerix.views import GenForeignKey


    class ModelNameForeign(GenForeignKey):
        model = ModelName
        label = '{label1} - {label2}'

        def get_foreign(self, queryset, search, filters):
            # Filter with search string
            qsobject = Q(field__icontains=search)
            queryset = queryset.filter(qsobject)

            return queryset[:settings.LIMIT_FOREIGNKEY]


Description
+++++++++++

:ref:`class-genforeignkey` is a Codenerix generic class used to obtain a dynamic list in foreign key boxes. Is recomended that the name of each class which inherit from :ref:`class-genforeignkey` follow the following pattern: NameModel+Foreign.

- Example:
    If model is User, then declarations should be, ``class UserForeign(GenForeignKey):`` 


Attributte
++++++++++

=====
label
=====

Is the structure of the string that the user will see in textbox. If you want a dynamic name, you can invoke using structure ``{field_name}``

.. code:: python

    # Result of this label, if field1=hello and field2=goodbye will be 
    # "This is hello - goodbye"
    label = 'This is {field1} - {field2}'

=====
model
=====

Model base for which Codenerix will make search.


Methods
+++++++

============================================
get_foreign(self, queryset, search, filters)
============================================

Method used to specify query search based in data sended by the client. An user can start to write in the foreign text box and the associated :ref:`class-genforeignkey` returns all founded coincidences.

.. code:: python
    
    class ExampleForeign(GenForeignKey):
        model = Example
        label = '{field}'
        
        def get_foreign(self, queryset, search, filters):
            queryset = queryset.filter(
                Q(field_string__icontains=search) | Q(field2__icontains=search)
            )
            return queryset[:settings.LIMIT_FOREIGNKEY]


Parameters
----------

-  queryset: Initialized queryset. All filter will make search using base model.

-  search: Text introduced to match.

-  filters: Dictionary of extra filters to customize searchs. This dictionary have one form field name and its value (if the field are not fill,  the value will be empy and its posible that don't find any tuple). ``More information in autofill of form.``

Return
------

-  queryset: Return a queryset.


More examples
+++++++++++++

============
Basic Detail
============

.. code:: python

    class ExampleForeign(GenForeignKey):
        model = Example
        label = '{field}'
        
        def get_foreign(self, queryset, search, filters):
            qs = queryset.filter(
                Q(field_string__icontains=search) | Q(field2__icontains=search)
            )
            return qs[:settings.LIMIT_FOREIGNKEY]

=======================
Foreignkey with filters
=======================

.. code:: python

    class ModelNameForeign(GenForeignKey):
        model = ModelName
        label = '{field}'
        
        def get_foreign(self, queryset, search, filters):
            # Build general queryset
            qs = queryset.filter(field__icontains=search)

            form_field = filters.get('filter_name', None)
            if att_filter:
                qs = qs.filter(field2=form_field)

            return qs[:settings.LIMIT_FOREIGNKEY]

==============
Overriding get
==============

Sometimes is necesary to create your own query with request parameters, this allows to change the structure and customize the result.

.. code:: python

    from django.db.models import Q
    from django.http import JsonResponse


    class ExampleForeign(GenForeignKey):
        model = Example
        label = '{lbl1} - {lbl2}'

        def get(self, request, *args, **kwargs):
            search = kwargs.get('search', None)

            filterstxt = self.request.GET.get('filter', '{}')
            filters = json.loads(filterstxt)

            queryset = Example.objects.all()
            if search != '*':
                qsobject = Q(charAttr__icontains=search)
                qsobject |= Q(charAttr2__icontains=search)
                queryset = queryset.filter(qsobject)

            pk_pk = filters.get('extraOption', None)
            if pk_pk:
                queryset = queryset.filter(pk_pk=pk_pk)

            answer = {
                'clear': ['attr1', 'attr2'],
                'readonly': ['attr1', 'attr2'],
                'rows': [
                    {
                        'attr1': 0,
                        'attr2': '',
                        'label': '---------',
                        'id': None,
                    }
                ]
            }
            for object in queryset[:settings.LIMIT_FOREIGNKEY]:
                answer['rows'].append({
                    'attr1': object.data,
                    'attr2': object.__unicode__(),
                    'label': object.__unicode__(),
                    'id': object.pk,
                })

            return JsonResponse(answer)
