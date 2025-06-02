import os

from setuptools import setup

import codenerix

# from setuptools.command.install import install
# class CustomInstallCommand(install):
#    """Customized setuptools install command - prints a friendly greeting."""
#    def run(self):
#        print "Hello, developer, how are you? :)"
#        install.run(self)
#        #post-processing code

with open(os.path.join(os.path.dirname(__file__), "README.rst")) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name="django_codenerix",
    version=codenerix.__version__,
    packages=["codenerix"],
    include_package_data=True,
    zip_safe=False,
    license="Apache License Version 2.0",
    description="Codenerix it is a framework that goes on top of Django so "
    "it makes easier development and building of ERPs.",
    long_description=README,
    url="https://github.com/codenerix/django-codenerix",
    author=", ".join(codenerix.__authors__),
    author_email=", ".join(codenerix.__authors_email__),
    keywords=["django", "codenerix", "management", "erp", "crm"],
    platforms=["OS Independent"],
    classifiers=[
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 4.0",
        "Intended Audience :: Developers",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    # cmdclass={ 'install': CustomInstallCommand, },
    install_requires=[
        "Django>=4.1.1",
        "Pillow",
        "Unidecode",
        "codenerix_lib>=1.0.27",
        "elasticsearch>=2.0.0,<3.0.0",
        "django-debug-toolbar>=4.4.2",
        "django-debug-toolbar-request-history",
        "django-haystack>=2.6.1",
        "django-stubs",
        "django-stubs-ext",
        "django-recaptcha>=1.2.1,<1.3",
        "django-rosetta>=0.9.8",
        "html5lib",
        "jsonfield",
        "ldap3",
        "openpyxl==3.1.2",
        "pyinstrument",
        "pymongo",
        "pyotp",
        "python-dateutil",
        "pytz",
        "types-pytz",
        "yattag",
    ],
)
