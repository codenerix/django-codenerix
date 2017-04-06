================
django-codenerix
================

Open source enterprise business management system built on top of Django + AngularJS + Bootstrap. Ready for fast development of any CMS, ERP, Business Management Software, you can discover more in `CODENERIX.com <http://www.codenerix.com/>`_.

.. image:: http://www.centrologic.com/wp-content/uploads/2017/01/logo-codenerix.png
    :target: http://www.codenerix.com
    :alt: Try our demo with Centrologic Cloud

********
Features
********

* is just Django with steroids
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
* compatible with Python 2.7 and Python >= 3.4

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

More information on `our website <http://www.codenerix.com>`_.

****
Demo
****

You can have a look to our `demo online <http://demo.codenerix.com>`_.

***********
Quick start
***********

1. Add "codenerix" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'codenerix',
    ]

2. Since Codenerix is a library, you only need to import its parts into your project and use them.


*************
Documentation
*************

We have tried to write the most accurate documentation about this project so you have enought information to feel confortable
with `CODENERIX <http://www.codenerix.com/>`_. Nevertheless we are human, and we make mistakes, so please contact with us if
you find any mistake or you have doubts about the explanations.

You can get access to the documentation at `CODENERIX Documentation <http://doc.codenerix.com>`_.


******************
Commercial support
******************

This project is backed by `Centrologic <http://www.centrologic.com/>`_. You can discover more in `CODENERIX.com <http://www.codenerix.com/>`_.
If you need help implementing or hosting django-codenerix, please contact us:
http://www.centrologic.com/contacto/

.. image:: http://www.centrologic.com/wp-content/uploads/2015/09/logo-centrologic.png
    :target: http://www.centrologic.com
    :alt: Centrologic is supported mainly by Centrologic Computational Logistic Center

*******
Credits
*******
Several technologies have been used to build `CODENERIX <http://www.codenerix.com>`_:

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
angular-loading-bar                 MIT                 Wes Cruver                  https://github.com/chieffancypants/angular-loading-bar
Bootstrap                           MIT                 Twitter, Inc.               https://github.com/twbs/bootstrap
Bootstrap Tab Collapse              MIT                 flatlogic.com               https://github.com/flatlogic/bootstrap-tabcollapse
bootstrap-datetimepicker            Apache              Stefan Petre                https://github.com/smalot/bootstrap-datetimepicker
Checklist-model                     MIT                 noginsk@rambler.ru          https://github.com/vitalets/checklist-model
Date Range Picker                   MIT                 Fragaria, s.r.o.            https://github.com/dangrossman/bootstrap-daterangepicker
django-angular                      MIT                 Jacob Rief                  https://github.com/jrief/django-angular
Font Awesome                        MIT & SIL OFL 1.1   Dave Gandy                  https://github.com/FortAwesome/Font-Awesome/
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
