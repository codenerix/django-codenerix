from django.conf.urls import url

from .views import ContactList, ContactCreate, ContactDetail, ContactEdit, ContactDelete, ContactForeign
from .views import PhoneList, PhoneCreate, PhoneDetail, PhoneEdit, PhoneDelete
from .views import ContactGroupList, ContactGroupCreate, ContactGroupDetail, ContactGroupEdit, ContactGroupDelete


urlpatterns = [
    # Contacts Routes
    url('^contacts$', ContactList.as_view(), name='contact_list'),
    url('^contacts/add$', ContactCreate.as_view(), name='contact_add'),
    url('^contacts/(?P<pk>\w+)$', ContactDetail.as_view(), name='contact_detail'),
    url('^contacts/(?P<pk>\w+)/edit$', ContactEdit.as_view(), name='contact_edit'),
    url('^contacts/(?P<pk>\w+)/delete$', ContactDelete.as_view(), name='contact_delete'),
    url('^contacts/(?P<search>[\w\W]+|\*)$', ContactForeign.as_view(), name='contact_foreign'),

    # Phones Routes
    url('^phones/(?P<pk>\w+)/sublist$', PhoneList.as_view(), name='phone_sublist'),
    url('^phones/(?P<pk>\w+)/sublist/addmodal$', PhoneCreate.as_view(), name='phone_sublist_add'),
    url('^phones/(?P<cpk>\w+)/sublist/(?P<pk>\w+)$', PhoneDetail.as_view(), name='phone_sublist_detail'),
    url('^phones/(?P<cpk>\w+)/sublist/(?P<pk>\w+)/editmodal$', PhoneEdit.as_view(), name='phone_sublist_edit'),
    url('^phones/(?P<cpk>\w+)/sublist/(?P<pk>\w+)/delete$', PhoneDelete.as_view(), name='phone_sublist_delete'),

    # ContactGroups Routes
    url('^contactgroups$', ContactGroupList.as_view(), name='contactgroup_list'),
    url('^contactgroups/add$', ContactGroupCreate.as_view(), name='contactgroup_add'),
    url('^contactgroups/(?P<pk>\w+)$', ContactGroupDetail.as_view(), name='contactgroup_detail'),
    url('^contactgroups/(?P<pk>\w+)/edit$', ContactGroupEdit.as_view(), name='contactgroup_edit'),
    url('^contactgroups/(?P<pk>\w+)/delete$', ContactGroupDelete.as_view(), name='contactgroup_delete'),
]
