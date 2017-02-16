.. _class-genupdate:

GenUpdate and GenUpdateModal
============================


.. code:: python

    from codenerix.views import GenUpdate, GenUpdateModal


    class ModelNameUpdate(GenUpdate):
        model = ModelName
        form_class = ModelNameFormCreate


    class ModelNameUpdateModal(GenUpdateModal, ModelNameUpdate):
        pass

Description
+++++++++++

:ref:`class-genupdate` are generic classes of Cdenerix used to generate a form automatically that handle the task of editing objects and their validation. Is recomended that the name of each class which inherit from GenUpdate or GenUpdateModal follow this pattern: NameModel+Update or NameModel+UpdateModal respectively. Both GenUpdate and GenUpdateModal usually are created at the same time.

- Example:
    If model is User, then, GenUpdate declarations should be, ``class UserUpdate(GenUpdate):`` 

    If model is User, then, GenUpdateModal declarations should be, ``class UserUpdateModal(GenUpdateModal):`` 

Attributte
++++++++++

==========
form_class
==========

Is the form that will be rendered in the template.

======================
hide_foreignkey_button
======================

If False hide the add button at the right of the fields with a :ref:`class-genforeignkey` (Default value is False).

==========
linkdelete
==========

If True, Codenerix don't show delete button (Default value is False).

=====
model
=====

Model used to generate and validate the form.

============
show_details
============

If True, after save a new register the view will move to the associated :ref:`class-gendetail` (Default value is False).

More examples
+++++++++++++

============
Basic Update
============

.. code:: python

    class ModelNameUpdate(GenUpdate):
        model = ModelName
        form_class = ModelNameForm

=============
Normal Update
=============

.. code:: python

    class ModelNameUpdate(GenUpdate):
        model = ModelName
        form_class = ModelNameForm
        show_details = True
        hide_foreignkey_button = True

===================
Update from sublist
===================

.. code:: python

    class ModelNameUpdateModal(GenUpdateModal):
        model = ModelName
        form_class = ModelNameForm

        @method_decorator(login_required)
        def dispatch(self, *args, **kwargs):
            self.__field_pk = kwargs.get('tpk', None) # Is important that the url don't use the label pk or will fail.
            return super(ModelNameUpdateModal, self).dispatch(*args, **kwargs)

        def form_valid(self, form):
            if self.__field_pk:
                data = ModelNameFather.objects.get(pk=self.__field_pk)
                self.request.field = data
                form.instance.field = data

            return super(ModelNameUpdateModal, self).form_valid(form, forms)
