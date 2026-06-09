"""Smoke tests: the package imports and Django can load codenerix models."""


def test_version_is_exposed():
    import codenerix

    assert isinstance(codenerix.__version__, str)
    assert codenerix.__version__


def test_models_load_under_app():
    from codenerix.models import Log

    assert Log._meta.app_label == "codenerix"
