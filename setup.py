import os
from setuptools import setup

import codenerix

#from setuptools.command.install import install
#class CustomInstallCommand(install):
#    """Customized setuptools install command - prints a friendly greeting."""
#    def run(self):
#        print "Hello, developer, how are you? :)"
#        install.run(self)
#        #post-processing code

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-codenerix',
    version=codenerix.__version__,
    packages=['codenerix'],
    include_package_data=True,
    zip_safe=False,
    license='Apache License Version 2.0',
    description='Codenerix it is a framework that goes on top of Django so it makes easier development and building of ERPs.',
    long_description=README,
    url='https://github.com/centrologic/django-codenerix',
    author=', '.join(codenerix.__authors__),
    keywords=['django', 'codenerix', 'management','erp','crm'],
    platforms=['OS Independent'],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.8',
        'Framework :: Django :: 1.9',
        'Framework :: Django :: 1.10',
        'Intended Audience :: Developers',
        'License :: Other/Proprietary License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    # cmdclass={ 'install': CustomInstallCommand, },
    install_requires = [
        "pymongo",
        "django-angular",
        "python-dateutil",
        "django-recaptcha>=1.2.1,<1.3",
        "django-rosetta",
        "jsonfield",
        "openpyxl",
        "Pillow",
        "Unidecode",
        "xhtml2pdf",
        "html5lib==1.0b8", # Default version 0.99999999 is broken with error 'from html5lib import treebuilders, inputstream' => 'ImportError: cannot import name inputstream' (1.0b10 also fails)
        "Django>=1.10.6,<1.11",
        "django-multi-email-field",
        "ldap3",
        ],
)

