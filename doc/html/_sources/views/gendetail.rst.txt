.. _class-gendetail:

GenDetail and GenDetailModal
============================

.. code:: python
    
    from codenerix.views import GenDetail, GenDetailModal
    from .forms import ModelNameForm

    class ModelNameDetails(GenDetail):
        model = ModelName
        groups = ModelNameForm.__groups_details__()


    class ModelNameDetailModal(GenDetailModal, ModelNameDetails):
        pass


.. code:: python

    # forms.py
    class ModelNameForm(ModelNameForm):

        class Meta:
            model = ModelName

        def __groups__(self):
            return [
                (
                    _('Details'), 12,
                    ['field1', 6],
                    ['field2', 6],
                    ['field3', 6],
                )
           ]

        @staticmethod
        def __groups_details__():
            return [
                (
                    _('Details'), 12,
                    ['field1', 6],
                    ['field2', 6],
                    ['field3', 6],
                )
            ]

Description
+++++++++++

:ref:`class-gendetail` are Codenerix generic classes used to show details of an instance. Is recomended that the name of each class which inherit from GenDetail or GenDetailModal follow the following pattern: ModelName+Detail or ModelName+DetailModal respectively.


- Example:
    If model is User, then, GenDetail deiclarations should be, ``class UserDetail(GenDetail):`` 

    If model is User, then, GenDetailModal declarations should be, ``class UserDetailModal(GenDetailModal):`` 

Attributte
++++++++++

==============
exclude_fields
==============

Exclude a list of fields of showing. 
``Warning. If you don't have a field in exclude_fields or in groups,``
``this field will appear without format at botton.``

.. code:: python

        exclude_fields = ['field1', 'field2']

=============
extra_context
=============

Dictionary used to send extra information to the template.

.. code:: python

        extra_context = {
            'extra_field': 'new information'
        } 

======
groups
======

Manage how the fields layout in the template. There is two ways to initialize groups, in views or using a form. **It's recommendable use a static methods on forms.**

Initialize groups using forms:
------------------------------

.. code:: python

        groups = ModelNameForm.__groups_details__()

        @staticmethod
        def __groups_details__():
            return [
                (
                    _('Details'), 12,
                    ['field1', 6],
                    ['field2', 6],
                    ['field3', 6],
                )
           ]

Initialize groups in views:
---------------------------

In this case, you should create a new group with this structure.

Groups are a list of tuples. Each tuple create a new space of information and have the name of the space, how many columns to use (based in Bootstrap 12 columns model), and fields with extra information. This fields are represented by a list of options which follow this order:

-   attr[0]: Referer field name. You should put here name of the attribute. ``Mandatory``.
-   attr[1]: Number of columns used to show these fields (Default value is 6).
-   attr[2]: Label color (Default value is black).
-   attr[3]: Label padding color (Default value is white).
-   attr[4]: Alignment of the label (Default value is 'left'). Options are (left|center|right)
-   attr[5]: Label and field are in the same line? (Boolean). Is used for check box and roundcheck.
-   attr[6]: Alternative label. If there is some text specified Codenerix will show it on the template (Default value is None).

.. code:: python

        groups = [
            (
                _('Details'), 12,
                ['field1', 6, '#23fe33', '#005476', "center", True, _("field inline, centered and label green with padding dark blue.")],
                ['field2', 6],
                ['field3'],
            )
        ]
        

========
linkedit
========

If True adds a link to edit the model (Default value is True).

==========
linkdelete
==========

If True adds a link to delete the model (Default value is True).

=====
model
=====

Model used to present the detail view.

====
tabs
====

List of dictionaries used to create sublist tabs. Each dictionary should have this keys:

-  id  : Sublist identifier.
-  name: Tab name.
-  ws  : Sublist related name.
-  rows: 

  .. TODO:: What's *rows* for?

==============
template_model
==============

If specified, Codenerix will load this template. If doesn’t exist, Codenerix will try to figure out automatically which template to use. If the specified template doesn’t exist, this view won’t work.

Methods
+++++++

=================================
get_context_data(self, \**kwargs)
=================================

Method used in :ref:`class-gendetail` to add or edit some fields in the context. Override Django default behaviour.

.. code:: python

    def get_context_data(self, **kwargs):
        context = super(Object, self).get_context_data(**kwargs)
        context['key'] = value
        return context

Parameters
----------

Base class keyword parameters.

Return
------
-  context: Dictionary with context data.


More examples
+++++++++++++

============
Basic Detail
============

.. code:: python
    
    from codenerix.views import GenDetail, ModelNameDetailModal
    from .forms import ModelNameForm


    class ModelNameDetails(GenDetail):
        model = ModelName
        groups = ModelNameForm.__groups_details__() # Declaration it's at bottom
        exclude_fields = ['field4', 'field5']

    class ModelNameDetailModal(GenDetailModal, ModelNameDetails):
        pass

===================
Detail with sublist
===================

.. code:: python

    from codenerix.views import GenDetail, ModelNameDetailModal
    from .forms import ModelNameForm


    class ModelNameDetails(GenDetail):
        model = ModelName
        groups = ModelNameForm.__groups_details__() # Declaration it's at bottom

        tabs = [
            {
                'id': 'tabId',
                'name': _('Tab 1'),
                'ws': 'relatedname_sublist',
                'rows': 'base'
            },
        ]
        exclude_fields = []

.. code:: python        

    # forms.py
    class ModelNameForm(GenModelForm):

        class Meta:
            model = ModelName

        def __groups__(self):
            return [
                (
                    _('Details'), 12,
                    ['field1', 6],
                    ['field2', 6],
                    ['field3', 6],
                )
           ]

        @staticmethod
        def __groups_details__():
            return [
                (
                    _('Details'), 12,
                    ['field1', 6],
                    ['field2', 6],
                    ['field3', 6],
                )
           ]

