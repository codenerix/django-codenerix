================
django-codenerix
================

Open source enterprise business management system built on top of Django + AngularJS + Bootstrap. Ready for fast development of any CMS, ERP, Business Management Software, you can discover more in `CODENERIX.com <https://www.codenerix.com>`_.

.. image:: https://github.com/codenerix/django-codenerix/raw/master/codenerix/static/codenerix/img/codenerix.png
    :target: https://www.codenerix.com
    :alt: Try our demo with Codenerix Cloud

********
Features
********

* it is just steroids for Django
* designed to build new django applications or to get integrated with existing ones
* easy to use methods for writing filters, granular control to limit results
* control what your users see on your software in just one line
* simple to develop customized views
* client-side validation with no extra work
* dynamic inputs and selects with real time autocomplete

	* search string sent to the server includes feedback from other form fields
	* response from server includes control information to perform form actions on any field (fill, clear, set readonly)
* all dynamic inputs and selects are declared in just on line with our powerfull 'autofill'
* get class information from instrospective analysis of classes
* ready to use Memcache with no extra effort
* full control of permissions with added new permissions
* integrated API system as standard
* several authentication methods' including OTP (One Time Password)
* ready for authentication with Microsoft Active Directory
* checked from Python 3.4 to Python 3.9
* checked from Django 2.2.9 to Django 4.0.4
* hotkeys support
* `Haystack <http://haystacksearch.org>`_ support (Search engines like: Solr, Elasticsearch, Whoosh and Xapian)
* nice packages with plenty of icons ready to use (Glyphicon, Font Awesome & Font Awesome Animation)
* special Codenerix directives

	* codenerixHtmlCompile to render HTML code straight from your scope variables (including AngularJS code)
	* codenerixOnEnter to detect when Enter key is pressed
	* codenerixOnTab to detect when Tab key is pressed
	* codenerixFocus to control when a input field get the focus
	* codenerixVtable to render tables with dynamic loading and cache system. It is used for really big tables that we would like to render virtually. The website will look like a really long list but when you scroll down the engine will send queries to the server to get the registers you should be seeing.
	* codenerixAutofocus to set the focus on the input who has it when the page is loaded
	* codenerixReallyClick to ask the user if it really clicked (it is a kind of "confirm" function)

Ready for:
''''''''''

* Debug Panel (https://github.com/recamshak/django-debug-panel)
* Debug Toolbar (https://github.com/jazzband/django-debug-toolbar)
* Spaghetti and Meatballs (https://github.com/LegoStormtroopr/django-spaghetti-and-meatballs)

New fields and widgets:
'''''''''''''''''''''''

* FileAngularField
* ImageAngularField
* Date2TimeField
* MultiEmailField
* WysiwygAngularField
* MultiBlockWysiwygField
* BootstrapWysiwygField (coming soon)
* GenReCaptchaField

****
Demo
****

You can have a look to our demos online:

* `CODENERIX Simple Agenda DEMO <http://demo.codenerix.com>`_.
* `CODENERIX Full ERP DEMO <https://erp.codenerix.com>`_.

You can find some working examples in GITHUB at `django-codenerix-examples <https://github.com/codenerix/django-codenerix-examples>`_ project.


**********
Quickstart
**********

1. Install your Linux (we checked it out on Debian 8.7)

2. Make sure you have installed the required packages to work with GIT and Python (zlib1g-dev, libjpeg-dev, python-dev, python3-dev are required by Pillow library)::

    apt-get install git python-pip python3-pip zlib1g-dev libjpeg-dev python-dev python3-dev

3. Clone the `CODENERIX Examples <https://github.com/codenerix/django-codenerix-examples>`_ project::

    git clone https://github.com/codenerix/django-codenerix-examples

4. Go to the desired folder (we will go to **agenda**)::

    cd django-codenerix-examples/agenda/

5. Install all requirements for the choosen example::

    For python 2: sudo pip2 install -r requirements.txt
    For python 3: sudo pip3 install -r requirements.txt

6. That's all...check it out::

    In python 2: python2 manage.py runserver
    In python 3: python3 manage.py runserver


*************
Documentation
*************

We have tried to write the most accurate documentation about this project so you have enought information to feel confortable
with CODENERIX. Nevertheless we are human, and we make mistakes, so please contact with us if
you find any mistake or you have doubts about the explanations.

You can get access to online documentation at `CODENERIX Documentation <http://doc.codenerix.com>`_.

You can find all documentation in GITHUB at `django-codenerix-documentation <https://github.com/codenerix/django-codenerix-documentation>`_ project.

You can get in touch with us `here <https://codenerix.com/contact/>`_.

***
FAQ
***

* sudo apt-get install libmysqlclient-dev, when using MySQL::

    EnvironmentError: mysql_config not found,

* sudo apt-get install default-libmysqlclient-dev, when using Maria DB::

    EnvironmentError: mysql_config not found,

* sudo apt-get install apache2-dev, when::

    RuntimeError: The 'apxs' command appears not to be installed or is not executable. Please check the list of prerequisites in the documentation for this package and install any missing Apache httpd server packages.

* sudo apt-get install python-dev, when::

    _mysql.c:40:20: fatal error: Python.h: No such file or directory
    #include "Python.h"
                         ^
    compilation terminated.
    error: command 'x86_64-linux-gnu-gcc' failed with exit status 1

* sudo apt-get install libssl-dev, when::

    build/temp.linux-x86_64-2.7/_openssl.c:434:30: fatal error: openssl/opensslv.h: No such file or directory
    #include <openssl/opensslv.h>
                                     ^
    compilation terminated.
    error: command 'x86_64-linux-gnu-gcc' failed with exit status 1

*******
Credits
*******

We are thankful to:

=================================== =================== =====================================================================================
Author                              Module              Contribution
=================================== =================== =====================================================================================
Mounir Messelmeni                   Haystack Engines    Contribution with Asciifolding support for Haystack Elasticsearch Engine
Khanh TO                            ngReallyClick       We added codenerixReallyClick as a version that works with uibModal of ngReallyClick
Francisco Torrejon                  Core                He was one of the first developers and part of the original project until 2015
=================================== =================== =====================================================================================

Several technologies have been used to build CODENERIX:

=================================== =================== =========================== =========================================================
Project name                        License             Owner                       Link to project
=================================== =================== =========================== =========================================================
Angular Material Design             MIT                 Google, Inc.                https://github.com/angular/material
AngularJS                           MIT                 Google, Inc.                https://github.com/angular/angular.js
AngularJS Color Contrast Directive  MIT                 Everton Yoshitani           https://github.com/evert0n/angular-color-contrast/
AngularJS reCaptcha                 MIT                 VividCortex                 https://github.com/VividCortex/angular-recaptcha
AngularUI                           MIT                 AngularUI Team              https://github.com/angular-ui
angular-base64-upload               MIT                 pitogo.adones@gmail.com     https://github.com/adonespitogo/angular-base64-upload
angular-bootstrap-colorpicker       MIT                 Michal Zielenkiewicz        https://github.com/buberdds/angular-bootstrap-colorpicker
angular-bootstrap-switch            Apache              Francesco Pontillo          https://github.com/frapontillo/angular-bootstrap-switch
angular-loading-bar                 MIT                 Wes Cruver                  https://github.com/chieffancypants/angular-loading-bar
Bootstrap                           MIT                 Twitter, Inc.               https://github.com/twbs/bootstrap
Bootstrap Tab Collapse              MIT                 flatlogic.com               https://github.com/flatlogic/bootstrap-tabcollapse
bootstrap-datetimepicker            Apache              Stefan Petre                https://github.com/smalot/bootstrap-datetimepicker
bootstrap-switch                    MIT                 Mattia Larentis             https://github.com/Bttstrp/bootstrap-switch
Checklist-model                     MIT                 noginsk@rambler.ru          https://github.com/vitalets/checklist-model
Date Range Picker                   MIT                 Fragaria, s.r.o.            https://github.com/dangrossman/bootstrap-daterangepicker
django-angular                      MIT                 Jacob Rief                  https://github.com/jrief/django-angular
Font Awesome                        MIT & SIL OFL 1.1   Dave Gandy                  https://github.com/FortAwesome/Font-Awesome/
Font Awesome Animation              MIT                 Louis Lin                   https://github.com/l-lin/font-awesome-animation/
hotkeys                             MIT                 Wes Cruver                  https://github.com/chieffancypants/angular-hotkeys/
HTML Clean for jQuery               BSD                 Anthony Johnston            https://github.com/components/jquery-htmlclean
HTML5 Shiv                          MIT or GPL2         Alexander Farkas            https://github.com/aFarkas/html5shiv
jQuery                              MIT                 jQuery Foundation, Inc.     https://github.com/jquery/jquery
moment.js                           MIT                 Tim Wood, Iskren Chernev    https://github.com/moment/moment/
notifyjs                            MIT                 Jaime Pillora               https://github.com/jpillora/notifyjs
nsPopover                           MIT                 contact@nohros.com          https://github.com/nohros/nsPopover
Quill                               COPYRIGHT           Jason Chen & salesforce.com https://quilljs.com/
Rangy                               MIT                 Tim Down                    https://github.com/timdown/rangy
textAngular                         MIT                 Austin Anderson             https://github.com/fraywing/textAngular/wiki
=================================== =================== =========================== =========================================================
