#!/usr/bin/env python

import logging

from codenerix_lib.debugger import Debugger
from django.core.management.base import BaseCommand
from django.utils.log import AdminEmailHandler


class Command(BaseCommand, Debugger):
    # Show this when the user types help
    help = "Send a test email to admins"

    def handle(self, *args, **options):
        # Autoconfigure Debugger
        self.set_name("TEST ADMIN EMAIL")
        self.set_debug()

        # Check if the email backend is configured
        self.debug("Recording test email to admins", color="blue")
        handler = AdminEmailHandler()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="¡Prueba de email a admins!",
            args=(),
            exc_info=None,
        )
        self.debug("Emitting test email record", color="yellow")
        handler.emit(record)
        self.debug("Test email done!", color="green")
