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
    name="django-codenerix",
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
        "codenerix_lib>=1.0.23",
        "pymongo",
        "python-dateutil",
        "django-recaptcha>=1.2.1,<1.3",
        "django-rosetta>=0.9.8",
        "jsonfield",
        "openpyxl==3.1.2",
        "Pillow",
        "Unidecode",
        "Django>=4.1.1",
        "ldap3",
        "django-haystack>=2.6.1",
        "pytz",
        "elasticsearch>=2.0.0,<3.0.0",
        "django-debug-toolbar==3.2.2",
        "pyotp",
        "html5lib",
        "pyinstrument",
        "django-stubs",
        "django-stubs-ext",
    ],
)
