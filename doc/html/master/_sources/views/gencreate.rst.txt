.. _class-gencreate:

GenCreate and GenCreateModal
============================

.. code:: python

    from codenerix.views import GenCreate, GenCreateModal


    class ModelNameCreate(GenCreate):
        model = ModelName
        form_class = ModelNameFormCreate

    class ModelNameCreateModal(GenCreateModal, ModelNameCreate):
        pass



Description
+++++++++++

:ref:`class-gencreate` are generic classes of Codenerix used to generate a form automatically that handle the task of creation of objects and their validation. Is recommended that the name of each class which inherits from GenCreate o GenCreateModal follow this pattern: ModelName+Create or ModelName+CreateModal respectively. Both GenCreate and GenCreateModal usually are created at the same time.

- Example:
    If model is User, then, GenCreate declarations should be, ``class UserCreate(GenCreate):`` 

    If model is User, then, GenCreateModal declarations should be, ``class UserCreateModal(GenCreateModal):`` 


Attribute
+++++++++

==========
form_class
==========

Is the form that will be rendered in the template.

======================
hide_foreignkey_button
======================

If False hide the add button at the right of the fields with a :ref:`class-genforeignkey` (Default value is False).

=====
model
=====

Model used to generate and validate the form.

============
show_details
============

Boolean field, if True after save a new register send to :ref:`class-gendetail`. Default value is False.


More examples
+++++++++++++

============
Basic Create
============

.. code:: python

    class ModelNameCreate(GenCreate):
        model = Modelname
        form_class = ModelNameCreateForm

=============
Normal create
=============

.. code:: python

    class ModelNameCreate(GenCreate):
        model = ModelName
        form_class = ModelNameFormCreateForm
        show_details = True
        hide_foreignkey_button = True


===================
Create from sublist
===================

.. code:: python

    class NameModelCreateModal(GenCreateModal):
        model = ModelName
        form_class = ModelNameCreateForm

        @method_decorator(login_required)
        def dispatch(self, *args, **kwargs):
            self.__field_pk = kwargs.get('tpk', None) # Its important, url can't use label pk or will fail.
            return super(ModelNameCreateModal, self).dispatch(*args, **kwargs)

        def form_valid(self, form):
            if self.__field_pk:
                data = NameModelFather.objects.get(pk=self.__field_pk)
                self.request.field = data
                form.instance.field = data

            return super(NameModelCreateModal, self).form_valid(form, forms)
