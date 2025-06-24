#!/usr/bin/env python

import contextlib
import importlib
import logging
import types

from codenerix_lib.debugger import Debugger
from django.conf import settings
from django.core.mail import get_connection
from django.core.management.base import BaseCommand, CommandError
from django.utils.log import AdminEmailHandler

# Make sure this command is not executed inside django server
if "runserver" in settings.INSTALLED_APPS:
    raise CommandError(
        "This command cannot be executed while the Django server is running. "
        "Please stop the server and try again.",
    )

# Ensure the settings module is configured
backend_string = getattr(settings, "EMAIL_BACKEND", None)
if not backend_string:
    raise CommandError("EMAIL_BACKEND setting is not configured.")

# Attempt to import the specified email backend
try:
    backend_module, backend_class = backend_string.rsplit(".", 1)
    smtp_backend = importlib.import_module(backend_module)
except (ImportError, AttributeError) as e:
    raise CommandError(f"Invalid EMAIL_BACKEND: {e!r}")


class Command(BaseCommand, Debugger):
    # Show this when the user types help
    help = "Send a test email to admins"

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbose",
            action="store_true",
            dest="verbose",
            default=False,
            help="Enable verbose output for debugging",
        )

    def handle(self, *args, **options):
        # Set verbosity level
        self.VERBOSE = options.get("verbose")

        # Autoconfigure Debugger
        self.set_name("TEST ADMIN EMAIL")
        self.set_debug()

        # Prepare handler
        self.debug("Getting AdminEmailHandler", color="blue")
        if self.VERBOSE:
            handler = self.get_patched_handler()
        else:
            handler = AdminEmailHandler()

        # Send the test email
        self.send(handler)

    def get_patched_handler(self):
        # Patch the open method of the SMTP backend to set debuglevel
        original_open = getattr(smtp_backend, backend_class).open

        # Patch the open method to enable SMTP debug
        def open_with_debug(self, *a, **kw):
            result = original_open(self, *a, **kw)
            try:
                # After each open(), force SMTP debug
                self.connection.set_debuglevel(1)
                self.stderr.write("→ [PATCH] SMTP debuglevel=1 enabled")
            except Exception:
                pass
            return result

        # Replace the open method with our patched version
        getattr(smtp_backend, backend_class).open = open_with_debug

        # Logger from smtplib to DEBUG level and output to stderr
        smtp_logger = logging.getLogger("smtplib")
        smtp_logger.setLevel(logging.DEBUG)
        smtp_ch = logging.StreamHandler(self.stderr)
        smtp_ch.setLevel(logging.DEBUG)
        smtp_logger.addHandler(smtp_ch)

        # Prepare the AdminEmailHandler to send emails to admins
        handler = AdminEmailHandler()
        handler.fail_silently = False

        # === Patch EMIT ===

        # Get original method
        orig_emit = handler.emit

        # Wrap the emit method to redirect stderr
        def emit_with_debug(record):
            with contextlib.redirect_stderr(self.stderr):
                orig_emit(record)

        # Patch the emit method to use our debug version
        handler.emit = emit_with_debug

        # === Patch SEND MAIL ===

        # Emit is calling to send_mail with a hardcoded
        # argument fail_silently=True which avoids producing
        # errors while sending emails. We want to avoid this
        # behavior because we want to DEBUG any error

        # Get the original send_mail method from the handler
        orig_send_mail = handler.send_mail

        # Wrap the send_mail method to avoid fail_silently
        def send_mail_no_fail_silently(self, *args, **kwargs):
            kwargs["fail_silently"] = False
            return orig_send_mail(*args, **kwargs)

        # Patch the send_mail method of the handler
        handler.send_mail = types.MethodType(
            send_mail_no_fail_silently,
            handler,
        )

        # === Patch connection method ===

        # Wrap the connection method to avoid fail_silently
        def connection_no_fail_silently(self, *args, **kwargs):
            return get_connection(
                backend=self.email_backend,
                fail_silently=False,
            )

        # Patch the connection method of the handler
        handler.connection = types.MethodType(
            connection_no_fail_silently,
            handler,
        )

        # Return the configured handler
        return handler

    def send(self, handler):
        # Check if the email backend is configured
        self.debug("Recording test email to admins", color="blue")
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="¡Emailt TEST to admins!",
            args=(),
            exc_info=None,
        )

        # Emit the test email record
        if self.VERBOSE:
            self.debug(
                "→ Emitting test email record with AdminEmailHandler:",
                color="yellow",
            )
        else:
            self.debug("Emitting test email record", color="yellow")

        try:
            handler.emit(record)
        except Exception as e:
            self.error(f"→ An error occurred while sending the email: {e!r}")
            if self.VERBOSE:
                self.error("→ Exception details:")
                self.error(f"{e.__class__.__name__}: {e}")
                self.debug("Analysing connection data:", color="white")
                conn = get_connection(
                    backend=handler.email_backend,
                    fail_silently=False,
                )
                if conn:
                    self.debug(f"{conn.host=}", color="white")
                    self.debug(f"{conn.port=}", color="white")
                    self.debug(f"{conn.username=}", color="white")
                    self.debug(f"{conn.password=}", color="white")
                    self.debug(f"{conn.use_tls=}", color="white")
                    self.debug(f"{conn.use_ssl=}", color="white")
                    self.debug(f"{conn.timeout=}", color="white")
                    self.debug(f"{conn.ssl_keyfile=}", color="white")
                    self.debug(f"{conn.ssl_certfile=}", color="white")
                else:
                    self.error("No connection available!")
                self.error("Re-raising exception")
                raise

        if self.VERBOSE:
            self.debug(
                "→ Register sent, review above the SMTP conversion.",
                color="green",
            )
        else:
            self.debug(
                "→ Email sent to admins, check your inbox.",
                color="green",
            )
            self.debug(
                "WARNING: fail_silently is enabled by default in Django "
                "(at least until Django 5.2.2) and it may hide ERRORs. Please "
                " consider trying executing this command with --verbose for "
                "improved details, SMTP communication and debugging.",
                color="blue",
            )
