import os
import sys
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

requirements = codenerix.__requirements__['all']
if sys.version_info[0] < 3:
    requirements += codenerix.__requirements__['2']
else:
    requirements += codenerix.__requirements__['3']

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
    install_requires = requirements,
)

