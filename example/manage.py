#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    if len(sys.argv)>=3 and sys.argv[1]=="license":
        os.environ.setdefault("CODENERIX_LICENSE", "TRUE")
        import codenerix
    else:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "agenda.settings")

        from django.core.management import execute_from_command_line

        execute_from_command_line(sys.argv)
