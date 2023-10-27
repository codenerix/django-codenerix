from django import forms
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from multi_email_field.forms import MultiEmailField as MultiEmailFormField
from multi_email_field.tests.models import TestModel
from multi_email_field.widgets import MultiEmailWidget
from pyquery import PyQuery as pq


class MultiEmailFormTest(SimpleTestCase):
    def test__form(self):
        class TestForm(forms.Form):
            f = MultiEmailFormField()

        form = TestForm(initial={"f": ["foo@foo.fr", "bar@bar.fr"]})
        output = form.as_p()
        self.assertEqual(1, len(pq("textarea", output)))
        # The template-based widget add a line-return
        value = pq("textarea", output).text()
        self.assertEqual(value.lstrip(), "foo@foo.fr\nbar@bar.fr")


class MultiEmailModelFormTest(TestCase):
    def test__model_form(self):
        class TestModelForm(forms.ModelForm):
            class Meta:
                model = TestModel
                fields = forms.ALL_FIELDS

        form = TestModelForm()
        self.assertIsInstance(form.fields["f"].widget, MultiEmailWidget)

        form = TestModelForm(data={"f": "foo@foo.fr\nbar@bar.fr"})
        self.assertTrue(form.is_valid())
        instance = form.save()
        self.assertEqual(instance.f, ["foo@foo.fr", "bar@bar.fr"])

        form = TestModelForm(instance=instance)
        output = form.as_p()
        self.assertEqual(2, len(pq("textarea", output)))
        # The template-based widget add a line-return
        value = pq("textarea:first", output).text()
        self.assertEqual(
            value.lstrip(),
            "foo@foo.fr\nbar@bar.fr",
        )


class MultiEmailModelTest(TestCase):
    def test_default_value(self):
        self.assertEqual(TestModel().f, [])

    def test_custom_default_value(self):
        self.assertEqual(TestModel().f_default, ["test@example.com"])

    def test__clean(self):
        # Nothing of these should raise a ValidationError
        TestModel().full_clean()
        TestModel(f="").full_clean()
        TestModel(f=None).full_clean()
        TestModel(f=False).full_clean()
        TestModel(f="foobar@foobar.fr\nbaz@baz.fr").full_clean()
        TestModel(f=["foo@foo.fr", "bar@bar.fr"]).full_clean()

    def test__string_based_value(self):
        emails = "foobar@foobar.fr\nbaz@baz.fr"
        TestModel.objects.create(f=emails)
        values = TestModel.objects.values_list("f", flat=True)
        self.assertEqual(values[0], emails.splitlines())

        qs = TestModel.objects.all()
        self.assertTrue(qs.filter(f=emails).exists())

    def test__list_based_value(self):
        emails = ["foo@foo.fr", "bar@bar.fr"]
        TestModel.objects.create(f=emails)

        values = TestModel.objects.values_list("f", flat=True)
        self.assertEqual(values[0], emails)

    def test__empty_based_value(self):
        qs = TestModel.objects.all()

        TestModel.objects.create(f=[])
        self.assertEqual(qs.values_list("f", flat=True)[0], [])
        self.assertTrue(qs.filter(f=[]).exists())
        self.assertTrue(qs.filter(f="").exists())
        TestModel.objects.all().delete()

        TestModel.objects.create(f="")
        self.assertEqual(qs.values_list("f", flat=True)[0], [])
        self.assertTrue(qs.filter(f=[]).exists())
        self.assertTrue(qs.filter(f="").exists())
        TestModel.objects.all().delete()

        TestModel.objects.create(f=None)
        self.assertEqual(TestModel.objects.values_list("f", flat=True)[0], [])

        self.assertTrue(qs.filter(f=None).exists())


class MultiEmailFormFieldTest(SimpleTestCase):
    def test__widget(self):
        f = MultiEmailFormField()
        self.assertIsInstance(f.widget, MultiEmailWidget)

    def test__to_python(self):
        f = MultiEmailFormField()
        # Empty values
        for val in ["", None]:
            self.assertEqual([], f.to_python(val))
        # One line correct value
        val = "  foo@bar.com    "
        self.assertEqual(["foo@bar.com"], f.to_python(val))
        # Multi lines correct values (test of #0010614)
        val = "foo@bar.com\nfoo2@bar2.com\r\nfoo3@bar3.com"
        self.assertEqual(
            ["foo@bar.com", "foo2@bar2.com", "foo3@bar3.com"],
            f.to_python(val),
        )

    def test__validate(self):
        f = MultiEmailFormField(required=True)
        # Empty value
        val = []
        self.assertRaises(ValidationError, f.validate, val)
        # Incorrect value
        val = ["not-an-email.com"]
        self.assertRaises(ValidationError, f.validate, val)
        # An incorrect value with correct values
        val = ["foo@bar.com", "not-an-email.com", "foo3@bar3.com"]
        self.assertRaises(ValidationError, f.validate, val)
        # Should not happen (to_python do the strip)
        val = ["  foo@bar.com    "]
        self.assertRaises(ValidationError, f.validate, val)
        # Correct value
        val = ["foo@bar.com"]
        f.validate(val)


class MultiEmailWidgetTest(SimpleTestCase):
    def test__prep_value__empty(self):
        w = MultiEmailWidget()
        value = w.prep_value("")
        self.assertEqual(value, "")

    def test__prep_value__string(self):
        w = MultiEmailWidget()
        value = w.prep_value("foo@foo.fr\nbar@bar.fr")
        self.assertEqual(value, "foo@foo.fr\nbar@bar.fr")

    def test__prep_value__list(self):
        w = MultiEmailWidget()
        value = w.prep_value(["foo@foo.fr", "bar@bar.fr"])
        self.assertEqual(value, "foo@foo.fr\nbar@bar.fr")

    def test__prep_value__raise(self):
        w = MultiEmailWidget()
        self.assertRaises(ValidationError, w.prep_value, 42)

    def test__render(self):
        w = MultiEmailWidget()
        output = w.render("test", ["foo@foo.fr", "bar@bar.fr"])
        self.assertEqual(1, len(pq("textarea", output)))
        # The template-based widget add a line-return
        value = pq("textarea", output).text()
        self.assertEqual(value.lstrip(), "foo@foo.fr\nbar@bar.fr")
