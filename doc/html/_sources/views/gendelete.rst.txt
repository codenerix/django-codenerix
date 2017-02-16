.. _class-gendelete:

GenDelete
=========

.. code:: python

    from codenerix.views import GenDelete


    class ModelNameDelete(GenDelete):
        model = ModelName

Description
+++++++++++

:ref:`class-gendelete` is a generic class used to delete an instance. Is recommended that the name of each class which inherit from GenDelete follow the following pattern: ModelName+Delete.

- Example:
    If model is User, then, :ref:`class-gendelete` declarations should be, ``class UserDelete(GenDelete):`` 

Attributte
++++++++++

=====
model
=====

Model to be deleted.
