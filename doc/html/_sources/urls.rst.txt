.. _urls:

Urls
=======


.. code:: python

    from codenerix_cms.views import \
        ModelNameList, ModelNameCreate, ModelNameCreateModal, ModelNameUpdate, ModelNameUpdateModal, ModelNameDelete, ModelNameDetail, \
        ModelNameSublist, ModelNameCreate, ModelNameCreateModal, ModelNameUpdate, ModelNameUpdateModal, ModelNameDelete, \

    url(r'^modelname$', ModelNameList.as_view(), name='modelname_list'),
    url(r'^modelname/add$', ModelNameCreate.as_view(), name='modelname_add'),
    url(r'^modelname/addmodal$', ModelNameCreateModal.as_view(), name='modelname_addmodal'),
    url(r'^modelname/(?P<pk>\w+)$', ModelNameDetail.as_view(), name='modelname_detail'),
    url(r'^modelname/(?P<pk>\w+)/edit$', ModelNameUpdate.as_view(), name='modelname_edit'),
    url(r'^modelname/(?P<pk>\w+)/editmodal$', ModelNameUpdateModal.as_view(), name='modelname_editmodal'),
    url(r'^modelname/(?P<pk>\w+)/delete$', ModelNameDelete.as_view(), name='modelname_delete'),

    url(r'^modelname/(?P<pk>\w+)/sublist$', ModelNameSublist.as_view(), name='modelname_sublist'),
    url(r'^modelname/(?P<tpk>\w+)/sublist/addmodal$', ModelNameCreateModal.as_view(), name='modelname_sublist_add'),
    url(r'^modelname/(?P<tpk>\w+)/sublist/(?P<pk>\w+)/editmodal$', ModelNameUpdateModal.as_view(), name='modelname_sublist_edit'),
    url(r'^modelname/(?P<tpk>\w+)/sublist/(?P<pk>\w+)/delete$', ModelNameDelete.as_view(), name='modelname_sublist_delete'),



Description
++++++++++++++++++++++

Codenerix enforces a pattern to structure urls for each Model. We use a incremental order divided in two parts, one for the base url and another for sublists url. The example previously showed is a clear example of its use.
