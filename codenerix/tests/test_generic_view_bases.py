"""GenCreate and GenUpdate keep Django's CreateView and UpdateView as bases.

The parametrised bases exist for type checkers only; at run time the classes
must still be Django's (CreateView[...] raises TypeError). The typing side is
checked outside the suite with django-stubs 6.1 (CDNX-DC-6.4.1 evidence doc).
"""

from django.test import override_settings
from django.views.generic.edit import CreateView, UpdateView

with override_settings(STATIC_URL="/static/"):
    from codenerix import views


def test_runtime_bases_are_django_views() -> None:
    assert CreateView in views.GenCreate.__mro__
    assert UpdateView in views.GenUpdate.__mro__
    assert views._CreateBase is CreateView
    assert views._UpdateBase is UpdateView
