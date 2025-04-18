# mypy: ignore-errors

import json
from base64 import b64encode
from importlib import import_module

import six
from django.core.exceptions import ValidationError
from django.forms import BoundField
from django.forms.utils import ErrorList
from django.http import QueryDict
from django.utils.encoding import force_str
from django.utils.html import format_html, format_html_join
from django.utils.safestring import SafeData, SafeText, mark_safe


class SafeTuple(SafeData, tuple):
    """
    Used to bypass escaping of TupleErrorList by the ``conditional_escape``
    function in Django's form rendering.
    """


class TupleErrorList(ErrorList):

    """
    A list of errors, which in contrast to Django's ErrorList, can contain
    a tuple for each item.
    If this TupleErrorList is initialized with a Python list, it behaves like
    Django's built-in ErrorList.
    If this TupleErrorList is initialized with a list of tuples, it behaves
    differently, suitable for AngularJS form validation. Then the tuple of
    each list item consist of the following fields:
    0: identifier: This is the model name of the field.
    1: The CSS class added to the embedding <ul>-element.
    2: property: '$pristine', '$dirty' or None used by ng-show on the
       wrapping <ul>-element.
    3: An arbitrary property used by ng-show on the actual <li>-element.
    4: The CSS class added to the <li>-element.
    5: The desired error message. If this contains the magic word '$message' it
       will be added with ``ng-bind`` rather than rendered inside the list item
    """

    ul_format = '<ul class="{1}" ng-show="{0}.{2}" ng-cloak>{3}</ul>'
    li_format = '<li ng-show="{0}.{1}" class="{2}">{3}</li>'
    li_format_bind = (
        '<li ng-show="{0}.{1}" class="{2}" ng-bind="{0}.{3}"></li>'
    )

    def as_json(self, escape_html=False):
        return json.dumps(self.get_json_data(escape_html))

    def as_ul(self):
        if not self:
            return SafeText()
        first = self[0]
        if isinstance(first, tuple):
            error_lists = {
                "$pristine": [],
                "$dirty": [],
            }
            for e in self:
                li_format = (
                    e[5] == "$message"
                    and self.li_format_bind
                    or self.li_format
                )
                err_tuple = (e[0], e[3], e[4], force_str(e[5]))
                error_lists[e[2]].append(format_html(li_format, *err_tuple))
            for key in error_lists.keys():
                error_lists[key].append(
                    format_html(
                        self.li_format,
                        first[0],
                        "djng_error",
                        "invalid",
                        "{{" + first[0] + ".djng_error_msg}}",
                    ),
                )
            # renders and combine both of these lists
            return mark_safe(
                "".join(
                    [
                        format_html(
                            self.ul_format,
                            first[0],
                            first[1],
                            prop,
                            mark_safe("".join(list_items)),
                        )
                        for prop, list_items in error_lists.items()
                    ],
                ),
            )
        return format_html(
            '<ul class="errorlist">{0}<li></li></ul>',
            format_html_join(
                "",
                "<li>{0}</li>",
                ((force_str(e),) for e in self),
            ),
        )

    def as_text(self):
        if not self:
            return ""
        if isinstance(self[0], tuple):
            return "\n".join(
                ["* %s" % force_str(e[5]) for e in self if bool(e[5])],
            )
        return "\n".join(["* %s" % force_str(e) for e in self])

    def __str__(self):
        return self.as_ul()

    def __repr__(self):
        if self and isinstance(self[0], tuple):
            return repr([force_str(e[5]) for e in self])
        else:
            return super().__repr__()

    def __getitem__(self, i):
        error = self.data[i]
        if isinstance(error, tuple):
            if isinstance(error[5], ValidationError):
                error[5] = list(error[5])[0]
            return error
        else:
            return super().__getitem__(i)


class NgBoundField(BoundField):
    @property
    def errors(self):
        """
        Returns a TupleErrorList for this field. This overloaded method adds
        additional error lists to the errors as detected by the form validator.
        """
        if not hasattr(self, "_errors_cache"):
            self._errors_cache = self.form.get_field_errors(self)
        return self._errors_cache

    def css_classes(self, extra_classes=None):
        """
        Returns a string of space-separated CSS classes for this field.
        """
        if hasattr(extra_classes, "split"):
            extra_classes = extra_classes.split()
        extra_classes = set(extra_classes or [])
        # field_css_classes is an optional member of a Form optimized
        # for django-angular
        field_css_classes = getattr(self.form, "field_css_classes", None)
        if hasattr(field_css_classes, "split"):
            extra_classes.update(field_css_classes.split())
        elif isinstance(field_css_classes, (list, tuple)):
            extra_classes.update(field_css_classes)
        elif isinstance(field_css_classes, dict):
            extra_field_classes = []
            for key in ("*", self.name):
                css_classes = field_css_classes.get(key)
                if hasattr(css_classes, "split"):
                    extra_field_classes = css_classes.split()
                elif isinstance(css_classes, (list, tuple)):
                    if "__default__" in css_classes:
                        css_classes.remove("__default__")
                        extra_field_classes.extend(css_classes)
                    else:
                        extra_field_classes = css_classes
            extra_classes.update(extra_field_classes)
        return super().css_classes(extra_classes)

    def as_widget(self, widget=None, attrs=None, only_initial=False):
        """
        Renders the field.
        """
        attrs = attrs or {}
        attrs.update(self.form.get_widget_attrs(self))
        if hasattr(self.field, "widget_css_classes"):
            css_classes = self.field.widget_css_classes
        else:
            css_classes = getattr(self.form, "widget_css_classes", None)
        if css_classes:
            attrs.update({"class": css_classes})
        widget_classes = self.form.fields[self.name].widget.attrs.get(
            "class",
            None,
        )
        if widget_classes:
            if attrs.get("class", None):
                attrs["class"] += " " + widget_classes
            else:
                attrs.update({"class": widget_classes})
        return super().as_widget(widget, attrs, only_initial)

    def label_tag(self, contents=None, attrs=None, label_suffix=None):
        attrs = attrs or {}
        css_classes = getattr(self.field, "label_css_classes", None)
        if hasattr(css_classes, "split"):
            css_classes = css_classes.split()
        css_classes = set(css_classes or [])
        label_css_classes = getattr(self.form, "label_css_classes", None)
        if hasattr(label_css_classes, "split"):
            css_classes.update(label_css_classes.split())
        elif isinstance(label_css_classes, (list, tuple)):
            css_classes.update(label_css_classes)
        elif isinstance(label_css_classes, dict):
            for key in (
                self.name,
                "*",
            ):
                extra_label_classes = label_css_classes.get(key)
                if hasattr(extra_label_classes, "split"):
                    extra_label_classes = extra_label_classes.split()
                extra_label_classes = set(extra_label_classes or [])
                css_classes.update(extra_label_classes)
        if css_classes:
            attrs.update({"class": " ".join(css_classes)})
        return super().label_tag(
            contents,
            attrs,
            label_suffix="",
        )


class BaseFieldsModifierMetaclass(type):
    """
    Metaclass that reconverts Field attributes from the dictionary
    'base_fields' into Fields with additional functionality required
    for AngularJS's Form control and Form validation.
    """

    field_mixins_module = "codenerix.djng.field_mixins"

    def __new__(cls, name, bases, attrs):
        new_class = super().__new__(
            cls,
            name,
            bases,
            attrs,
        )
        field_mixins_module = import_module(new_class.field_mixins_module)
        field_mixins_fallback_module = import_module(cls.field_mixins_module)
        # add additional methods to django.form.fields at runtime
        for field in new_class.base_fields.values():
            FieldMixinName = field.__class__.__name__ + "Mixin"  # noqa: N806
            try:
                FieldMixin = getattr(  # noqa: N806
                    field_mixins_module,
                    FieldMixinName,
                )
            except AttributeError:
                try:
                    FieldMixin = getattr(  # noqa: N806
                        field_mixins_fallback_module,
                        FieldMixinName,
                    )
                except AttributeError:
                    FieldMixin = (  # noqa: N806
                        field_mixins_fallback_module.DefaultFieldMixin
                    )
            field.__class__ = type(
                field.__class__.__name__,
                (field.__class__, FieldMixin),
                {},
            )
        return new_class


class NgFormBaseMixin:
    form_error_css_classes = "djng-form-errors"
    field_error_css_classes = "djng-field-errors"

    def __init__(self, data=None, *args, **kwargs):
        try:
            form_name = self.form_name
        except AttributeError:
            # if form_name is unset, then generate a pseudo unique name, based
            # upon the class name
            form_name = (
                b64encode(six.b(self.__class__.__name__)).rstrip(b"=").decode()
            )
        self.form_name = kwargs.pop("form_name", form_name)
        error_class = kwargs.pop("error_class", TupleErrorList)
        kwargs.setdefault("error_class", error_class)
        self.convert_widgets()
        if isinstance(data, QueryDict):
            data = self.rectify_multipart_form_data(data.copy())
        elif isinstance(data, dict):
            data = self.rectify_ajax_form_data(data.copy())
        super().__init__(data=data, *args, **kwargs)

    def __getitem__(self, name):
        "Returns a NgBoundField with the given name."
        try:
            field = self.fields[name]
        except KeyError:
            raise KeyError("Key %r not found in Form" % name)
        return NgBoundField(self, field, name)

    def add_prefix(self, field_name):
        """
        Rewrite the model keys to use dots instead of dashes, since thats the
        syntax used in Angular models.
        """
        return (
            ("%s.%s" % (self.prefix, field_name))
            if self.prefix
            else field_name
        )

    def get_field_errors(self, field):
        """
        Return server side errors. Shall be overridden by derived forms to
        add their extra errors for AngularJS.
        """
        identifier = format_html("{0}.{1}", self.form_name, field.name)
        errors = self.errors.get(field.html_name, [])
        return self.error_class(
            [
                SafeTuple(
                    (
                        identifier,
                        self.field_error_css_classes,
                        "$pristine",
                        "$pristine",
                        "invalid",
                        e,
                    ),
                )
                for e in errors
            ],
        )

    def non_field_errors(self):
        errors = super().non_field_errors()
        return self.error_class(
            [
                SafeTuple(
                    (
                        self.form_name,
                        self.form_error_css_classes,
                        "$pristine",
                        "$pristine",
                        "invalid",
                        e,
                    ),
                )
                for e in errors
            ],
        )

    def get_widget_attrs(self, bound_field):
        """
        Return a dictionary of additional attributes which shall be added to
        the widget, used to render this field.
        """
        return {}

    def convert_widgets(self):
        """
        During form initialization, some widgets have to be replaced by a
        counterpart suitable to be rendered the AngularJS way.
        """
        for field in self.base_fields.values():
            try:
                new_widget = field.get_converted_widget()
            except AttributeError:
                pass
            else:
                if new_widget:
                    field.widget = new_widget

    def rectify_multipart_form_data(self, data):
        """
        If a widget was converted and the Form data was submitted through
        a multipart request, then these data fields must be converted to
        suit the Django Form validation
        """
        for name, field in self.base_fields.items():
            try:
                field.widget.implode_multi_values(name, data)
            except AttributeError:
                pass
        return data

    def rectify_ajax_form_data(self, data):
        """
        If a widget was converted and the Form data was submitted through an
        Ajax request, then these data fields must be converted to suit the
        Django Form validation
        """
        for name, field in self.base_fields.items():
            try:
                data[name] = field.widget.convert_ajax_data(data.get(name, {}))
            except AttributeError:
                pass
        return data
