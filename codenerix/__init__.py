__version__ = "4.0.4"

__authors__ = [
    'Juanmi Taboada',
    'Juan Soler Ruiz',
]

__authors_email__ = [
    'juanmi@juanmitaboada.com',
    'soleronline@gmail.com',
]


__requirements__ = {
    'all': [
        "pymongo",
        "python-dateutil",
        "django-recaptcha>=1.2.1,<1.3",
        "django-rosetta>=0.9.8",
        "jsonfield",
        "openpyxl",
        "Pillow",
        "Unidecode",
        "Django>=2.2.9,<=4.0.9",
        "ldap3",
        "django-haystack>=2.6.1",
        "pytz",
        "elasticsearch>=2.0.0,<3.0.0",
        "django-debug-toolbar==3.2.2",
    ],
    '2': [
        "html5lib==1.0b8",  # Default version 0.99999999 is broken with error 'from html5lib import treebuilders, inputstream' => 'ImportError: cannot import name inputstream' (1.0b10 also fails)
    ],
    '3': [
        "html5lib",
    ],
}
