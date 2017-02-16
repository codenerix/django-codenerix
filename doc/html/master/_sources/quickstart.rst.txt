Quickstart
==========


Here we start a new basic project in Codenerix, explaining all necessary steps from configuration to simple deployment.


0. Start and configure
++++++++++++++++++++++

First step it's to create a project and configure its settings.

Follow this guide to set up a project from begin. We assume that you have Python (>=2.7) and Django (>=1.10) installed.

-  Execute the Django command startproject to create a new project named *librarymanager*.

.. code:: console

    django-admin startproject librarymanager


-  Enter in the project folder and start a new app, in this case the app will be a Python package named *library* inside the project root.

.. code:: console

    ./manage.py startapp library


-  Now we have our project and app created. Next step is to configure the project editing the *settings.py* module.

.. code:: python

    # Installed apps
    INSTALLED_APPS = [
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',

        'codenerix', # Codenerix app
        'library',   # Our app
    ]

    -  Add Codenerix authentication backends

.. code:: python

    AUTHENTICATION_BACKENDS=(
        'codenerix.authbackend.TokenAuth',              # TokenAuth
        'codenerix.authbackend.LimitedAuth',            # LimitedAuth
    )

    -  Add Codenerix templates context processors

.. code:: python

    # Templates
    TEMPLATES = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [],
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',

                    # Codenerix context processors
                    'codenerix.context.codenerix',
                    'codenerix.context.codenerix_js',
                ],
            },
        },
    ]


    -  Add Codenerix middlewares

.. code:: python

    MIDDLEWARE = [
        'django.middleware.security.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',

        #Codenerix middlewares
        'codenerix.authbackend.TokenAuthMiddleware',
        'codenerix.authbackend.LimitedAuthMiddleware',
        'codenerix.middleware.SecureRequiredMiddleware',
        'codenerix.middleware.CurrentUserMiddleware',
    ]

    -  Finally, add all Codenerix constants.

.. code:: python

    USERNAME_MIN_SIZE = 6
    PASSWORD_MIN_SIZE = 8
    ALARMS_LOOPTIME = 15000     # Refresh alarms every 15 seconds (15.000 miliseconds)
    ALARMS_QUICKLOOP = 1000     # Refresh alarms every 1 seconds (1.000 miliseconds) when the system is on quick loop processing (without focus)
    ALARMS_ERRORLOOP = 5000     # Refresh alarms every 5 seconds (5.000 miliseconds) when the http request fails
    CONNECTION_ERROR = 60000    # Connection error after 60 seconds (60.000 miliseconds)
    ALL_PAGESALLOWED = True

    LIMIT_FOREIGNKEY = 25

    CODENERIX_CSS = '<link href="/static/codenerix/codenerix.css" rel="stylesheet">'
    CODENERIX_JS = '<script type="text/javascript" src="/static/codenerix/codenerix.js"></script>'
    CODENERIX_JS += '<script type="text/javascript" src="/static/codenerix/codenerix.extra.js"></script>'

    # Other definitions about dates, hours
    DATETIME_FORMAT = 'Y-m-d H:i'

    DATETIME_INPUT_FORMATS = ('%Y-%m-%d %H:%M',)

    TIME_FORMAT = 'H:i'

    TIME_INPUT_FORMATS = ('%H:%M', '%H%M')

    DATETIME_RANGE_FORMAT = ('%Y-%m-%d', 'YYYY-MM-DD')

    DATERANGEPICKER_OPTIONS = '{{'
    DATERANGEPICKER_OPTIONS+= '    format: "{Format}",'
    DATERANGEPICKER_OPTIONS+= '    timePicker: true,'
    DATERANGEPICKER_OPTIONS+= '    timePicker12Hour: false,'
    DATERANGEPICKER_OPTIONS+= '    showDropdowns: true,'
    DATERANGEPICKER_OPTIONS+= '    locale: {{'
    DATERANGEPICKER_OPTIONS+= '        firstDay: 1,'
    DATERANGEPICKER_OPTIONS+= '        fromLabel: "{From}",'
    DATERANGEPICKER_OPTIONS+= '        toLabel: "{To}",'
    DATERANGEPICKER_OPTIONS+= '        applyLabel: "{Apply}",'
    DATERANGEPICKER_OPTIONS+= '        cancelLabel: "{Cancel}",'
    DATERANGEPICKER_OPTIONS+= '        daysOfWeek: ["{Su}", "{Mo}", "{Tu}", "{We}", "{Th}", "{Fr}", "{Sa}"],'
    DATERANGEPICKER_OPTIONS+= '        monthNames: ["{January}", "{February}", "{March}", "{April}", "{May}", "{June}", "{July}", "{August}", "{September}", "{October}", "{November}", "{December}"],'
    DATERANGEPICKER_OPTIONS+= '    }},'
    DATERANGEPICKER_OPTIONS+= '}}'


-  Last step is to check all dependencies used by Codenerix using the following `manage.py` command. This step is critical to have a fully functional Codenerix application.

.. code:: console

    ./manage.py license c


Following this step, you will have a basic Codenerix project ready to run.


1. Create a model
+++++++++++++++++

.. code:: python

    from codenerix.models import CodenerixModel
    from django.db import models

    class Author(CodenerixModel):
        name = models.CharField(_(u'Name'), max_length=128, blank=False, null=False)
        birth_date = models.CharField(_(u'Fecha de nacimiento'), max_length=128, blank=False, null=False)
        
        def __fields__(self, info):
            fields=[]
            fields.append(('name', _('Name'), 100, 'left'))
            fields.append(('birth_date', _('Birth Date')))
            return fields


    class Book(CodenerixModel):
        name = models.CharField(_(u'Name'), max_length=128, blank=False, null=False)
        author = models.ForeignKey(Author, max_length=128, blank=False, null=False)
        isbn = models.CharField(_(u'ISBN'), max_length=128, blank=False, null=False)

        def __fields__(self,info):
            fields = []
            fields.append(('name', _('Name'), 100, 'left'))
            fields.append(('isbn', _('ISBN')))
            fields.append(('author', _('Author')))
            return fields


The first step to start coding a Django project is create data models. In this case we will make two Models as showed above, Author and Book, both inheriting from the base class :ref:`class-codenerixmodel`. The structure is simple, we declare all fields (as in Django) and then the method __fields__. This method is mandatory because is needed by Codenerix to define which fields are shown and in which order.


2. Create a form
++++++++++++++++

.. code:: python

    from codenerix.forms import GenModelForm

    class BookForm(GenModelForm):
        model = Book
        exclude = []

        def __groups__(self):
            groups = [(_('Book'), 12, ['name', 6], ['isbn', 6], ['author', 3])]
            return groups


        @staticmethod
        def __groups_details__():
            details = [(_('Book'), 12, ['name' , 6], ['isbn', 6], ['author', 3])]
            return details


    class AuthorForm(GenModelForm):
        model = Author
        exclude = []

        def __groups__(self):
            groups = [(_('Author'), 12, ['name', 6], ['birth_date', 6])]
            return groups


        @staticmethod
        def __groups_details__():
            details = [(_('Author'), 12, ['name', 6], ['birth_date', 6])]
            return details


The second step is to create a form. In our example we are creating two forms, one for the Book model and another for the Author model. In addition, both forms have implemented the static method **__groups_details__**. This method is important because we will use them in :ref:`class-gendetail` to layout its representation.


3. Create views
+++++++++++++++

.. code:: python

    from codenerix.views import GenList, GenCreate, GenCreateModal, GenUpdate, GenUpdateModal, GenDelete
    from library.forms import AuthorForm 


    class AuthorList(GenList):
        model = Author
        show_details = True


    class AuthorCreate(GenCreate):
        model = Author
        form_class = AuthorForm


    class AuthorCreateModal(GenCreateModal, AuthorCreate):
        pass


    class AuthorUpdate(GenUpdate):
        model = Author
        form_class = AuthorForm


    class AuthorUpdateModal(GenUpdateModal, AuthorUpdate):
        pass


    class AuthorDelete(GenDelete):
        model = Author


    class AuthorDetails(GenDetail):
        model = Author
        groups = AuthorForm.__groups_details__()


    class AuthorDetailModal(GenDetailModal, AuthorDetails):
        pass


    class BookList(GenList):
        model = Book
        show_details = True


    class BookCreate(GenCreate):
        model = Book
        form_class = BookForm


    class BookCreateModal(GenCreateModal, BookCreate):
        pass


    class BookUpdate(GenUpdate):
        model = Book
        form_class = BookForm


    class BookUpdateModal(GenUpdateModal, BookUpdate):
        pass


    class BookDelete(GenDelete):
        model = Book


    class BookDetails(GenDetail):
        model = Book
        groups = BookForm.__groups_details__()


    class BookDetailModal(GenDetailModal, BookDetails):
        pass


The third step is to create the views. A basic view don't need to associated to any html template, generation will be automatically accomplished by Codenerix.


4. Urls
+++++++

.. code:: python

    from django.conf.urls import url
    from library import views


    urlpatterns = [

        url(r'^book$',views.BookList.as_view(), name='book_list'),
        url(r'^book/add$', views.BookCreate.as_view(), name='book_add'),
        url(r'^book/addmodal$', views.BookCreateModal.as_view(), name='book_addmodal'),
        url(r'^book/(?P<pk>\w+)$', views.BookDetail.as_view(), name='book_detail'),
        url(r'^book/(?P<pk>\w+)/edit$', views.BookUpdate.as_view(), name='book_edit'),
        url(r'^book/(?P<pk>\w+)/editmodal$', views.BookUpdateModal.as_view(), name='book_editmodal'),
        url(r'^book/(?P<pk>\w+)/delete$', views.BookDelete.as_view(), name='book_delete'),


        url(r'^author$', views.AuthorList.as_view(), name='author_list'),
        url(r'^author/add$', views.AuthorCreate.as_view(), name='author_add'),
        url(r'^author/addmodal$', views.AuthorCreateModal.as_view(), name='author_addmodal'),
        url(r'^author/(?P<pk>\w+)$', views.AuthorDetail.as_view(), name='author_detail'),
        url(r'^author/(?P<pk>\w+)/edit$', views.AuthorUpdate.as_view(), name='author_edit'),
        url(r'^author/(?P<pk>\w+)/editmodal$', views.AuthorUpdateModal.as_view(), name='author_editmodal'),
        url(r'^author/(?P<pk>\w+)/delete$', views.AuthorDelete.as_view(), name='author_delete'),

    ]


The last step is to associate the urls with the views using the Django routing system. The example from above shows the prefered naming conventions proposed by Codenerix.

Finally, we have a project ready to be tested using the Django development server.
