.. _class-codenerixmodel:

CodenerixModel
==============

.. code:: python

    from codenerix.models import CodenerixModel

    class ModelName(CodenerixModel):

        attr1 = models.CharField(_('attr1Label', max_length=100, blank=True, null=True)
        attr2 = models.IntegerField(_('attr2Label'), blank=False, null=False)

        def __fields__(self, info):
            fields = super(Staticheader, self).__fields__(info)
            fields.append(('attr1', _('attr1Label'), 100))
            fields.append(('attr2', _('attr2Label'), 100))
            return fields

        def __unicode__(self):
            return u'{}'.format(self.identifier)

Description
+++++++++++

:ref:`class-codenerixmodel` is a generic class used to define a single data model. This class inherits from django class models.Model

Methods
+++++++

======================
__fields__(self, info)
======================

This is a mandatory method to tell Codenerix which of the model fields must be showed. If this method is declared in a :ref:`class-genlist` for this model, the :ref:`class-genlist` definition will prevail.

.. code:: python

    def __fields__(self,info):
        fields = []
        fields.append(('nameField1', _('labelField1', 100, 'left'))
        fields.append(('nameField2', _('labelField2'), None, 'center'))
        fields.append(('nameField3', _('labelField3')))
        return fields



Parameters
----------
- info: Contains all the basic information from the session.

Return
------

- List of parameters list. Each list represents a model field and associated parameters:

    - Identifier: Field name, have to be a member of the model. ``cannot be null``
    - Label : Field label. ``cannot be null``
    - Size : Size in pixels of the form widget.
    - Alignment: Alignment of the columns name. Options are (left | center | right).

======================
__limitQ__(self, info)
======================

Filters data for a static value (For example, if you want that a certain role only see its own clients, limitQ can filter the resulting queryset by the clients of the logged user). If this method is declared in a :ref:`class-genlist` for this model, the :ref:`class-genlist` definition will prevail.

.. code:: python

    def __limitQ__(self, info):
        criteria = []
        criteria.append(Q(model__pk=pk_condition))
        criteria.append(Q(model__field1=condition))
        limits = {}
        limits['profile_people_limit'] = reduce(operator.or_, criterials)
        return limits

Parameters
----------
- info: Contains all basic information from the session.

Return
------

Returns a dictionary with a set of Q conditions.


=======================
__searchQ__(self, info)
=======================

Manages a text filter. If this method is declared in a :ref:`class-genlist` for this model, the :ref:`class-genlist` definition will prevail.

.. code:: python

    def __searchQ__(self, info, text):
        text_filters = {}
        text_filters['identifier1'] = Q(CharField1__icontains=text)
        text_filters['identifier2'] = Q(TextField1__icontains=text)
        text_filters['identifier3'] = Q(IntegerField=34)

        #If text have this a especific word can return another Q condition. 
        if text.find(u'magic') != -1:
            text_filters['identifier4'] = Q(identifier=34)

        return text_filters


Parameters
----------
- info: Contains all basic information from the session.
- text: Text used to filter.

Return
------

Returns a dictionary with all Q conditions.

=======================
__searchF__(self, info)
=======================

Declare predefined search filters. If this method is declared in a :ref:`class-genlist` for this model, the :ref:`class-genlist` definition will prevail.


.. code:: python

    def __searchF__(self, info):
        list1 = []
        for l1 in Model.objects.all():
            list1.append((l1.id, l1.field1 + ' ' + l1.field2))

        list2 = [] 
        for li in Model2.objects.all():
            list2.append((li.id, str(li.field)))

        text_filters = {}
        text_filters['field1'] = (_('Field1'), lambda x: Q(field1__startswith=x), [('h', _('Starts with h')), ('S', _('Starts with S'))])
        text_filters['field2'] = (_('Field2'), lambda x: Q(field2__pk=x), list1)
        text_filters['external'] = (_('Field3'), lambda x: Q(pk=x),list2)
        return text_filters


Parameters
----------
-  info: Contains all basic information from the session.

Return
------

Returns a dictionary of tuples. Each tuple have three fields with following structure:

-  Name: Name of the selector. If match a model field name, the filter will positionate in the column, else the choicebox will put on default site.
-  Function: Is a lambda function to specify search methods. 
-  Choices: A tuple with two fields (value, label).

More examples
+++++++++++++


==================
Basic GenModelForm
==================

.. code:: python

    from codenerix.models import CodenerixModel


    class ModelName(CodenerixModel):

        attr1 = models.CharField(_('attr1Label'), max_length=100, blank=True, null=True)
        attr2 = models.IntegerField(_('attr2Label'), blank=False, null=False)

        def __fields__(self, info):
            fields = super(Staticheader, self).__fields__(info)
            fields.append(('attr1', _('attr1Label'), 100))
            fields.append(('attr2', _('attr2Label'), 100))
            return fields

        def __unicode__(self):
            return u'{}'.format(self.identifier)
