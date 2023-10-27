#
# django-codenerix
#
# Codenerix GNU
#
# Project URL : http://www.codenerix.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Debugger helps to debug the system
"""
from datetime import datetime
from inspect import currentframe
from os import getcwd
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, Tuple, Union

from codenerix_lib.colors import colors

__version__ = "2023033000"

__all__ = ["Debugger", "lineno", "__FILE__", "__LINE__"]


def lineno():
    """
    Returns the current line number in our program.
    """
    return currentframe().f_back.f_lineno


def __LINE__():  # noqa: N802,N807
    """
    Returns the current line number in our program.
    """
    return currentframe().f_back.f_lineno


def __FILE__():  # noqa: N802,N807
    """
    Returns the current line number in our program.
    """
    filename = currentframe().f_back.f_code.co_filename.replace(getcwd(), ".")
    if len(filename) >= 2 and filename[0] == "." and filename[1] == "/":
        filename = filename[2:]
    return filename


class Debugger:
    __indebug: Dict[str, Tuple[Union[str, Path, TextIO], List[str]]] = {}
    __inname = None

    KINDS = [
        "primary",
        "secondary",
        "success",
        "danger",
        "warning",
        "info",
        "error",
    ]

    def __init__(self, **kwargs):
        self.set_debug(debug=kwargs.get("debug", None))

    def __autoconfig(self):
        # Define debug configuration
        import sys

        debugger = {}
        debugger["screen"] = (sys.stdout, ["*"])
        # debugger['log'] = (open("log/debug.log","a"), ['*'] )
        self.set_debug(debugger)

    def set_debug(
        self,
        debug: Optional[Dict[str, Any]] = None,
    ):
        if debug is None:
            self.__autoconfig()
        else:
            if isinstance(debug, dict):
                # Set the deepness system
                idebug = debug.copy()
                if "deepness" in debug:  # pragma: no cover
                    if debug["deepness"]:
                        idebug["deepness"] -= 1
                    else:
                        for key in idebug:
                            if key not in ["tabular", "deepness"]:
                                newlist = []
                                for element in idebug[key][1]:
                                    if element in ["-*error", "-*warning"]:
                                        newlist.append(element)
                                idebug[key][1] = newlist

                # Save internal debugger
                self.__indebug = idebug
            else:  # pragma: no cover
                raise OSError("Argument is not a dictionary")

    def set_origin(self, origin):  # pragma: no cover
        self.origin = origin

    def get_debug(self):
        return self.__indebug

    def set_name(self, name):
        self.__inname = name

    def get_name(self):
        return self.__inname

    def color(self, color):
        # Colors$
        if color in colors:
            (darkbit, subcolor) = colors[color]
            return "\033[%1d;%02dm" % (darkbit, subcolor)
        else:
            if color:
                self.debug(
                    "\033[1;31mColor '%s' unknown\033[1;00m\n" % (color),
                )
            return ""

    def debug(
        self,
        msg=None,
        header=None,
        color=None,
        tail=None,
        head=None,
        footer=None,
        origin=False,
        kind="",
    ):
        # If origin has been requested
        if origin or getattr(self, "origin", False):  # pragma: no cover
            origin = True
            line = currentframe().f_back.f_lineno
            filename = currentframe().f_back.f_code.co_filename.replace(
                getcwd(),
                ".",
            )
            if (
                len(filename) >= 2
                and filename[0] == "."
                and filename[1] == "/"
            ):
                filename = filename[2:]

        # Allow better names for debug calls
        if header is None:
            if head is None:
                header = True
            else:
                header = head
        if tail is None:
            if footer is None:
                tail = True
            else:
                tail = footer

        # Retrieve the name of the class
        clname = self.__class__.__name__

        # Retrieve tabular
        if "tabular" in self.__indebug:  # pragma: no cover
            tabular = self.__indebug["tabular"]
        else:
            tabular = ""

        # For each element inside indebug
        for name in self.__indebug:
            # If this is no deepeness key, keep going
            if name not in ["deepness", "tabular"]:
                # Get color
                if name == "screen" or name[-1] == "*":
                    color_ini = self.color(color)
                    color_end = self.color("close")
                else:
                    color_ini = self.color(None)
                    color_end = color_ini

                # Get file output handler and indebug list
                (handler, indebug) = self.__indebug[name]

                if not kind or "-*{}".format(kind) not in indebug:
                    if msg and isinstance(handler, str):
                        # Open handler buffer
                        handlerbuf = open(handler, "a")
                    else:
                        handlerbuf = handler

                    # Look up if the name of the class is inside indebug
                    if (clname in indebug) or (
                        ("*" in indebug) and ("-%s" % (clname) not in indebug)
                    ):
                        # Set line head name
                        if self.__inname:
                            headname = self.__inname
                        else:
                            headname = clname

                        # Build the message
                        message = color_ini
                        if header:
                            now = datetime.now()
                            message += (
                                f"{now.day:02d}/"
                                f"{now.month:02d}/"
                                f"{now.year} "
                                f"{now.hour:02d}:"
                                f"{now.minute:02d}:"
                                f"{now.second:02d} "
                            )
                            if origin:
                                message += "{}:{}: ".format(filename, line)
                            message += "{:<15s} - {}".format(headname, tabular)

                        if msg:
                            try:
                                message += str(msg)
                            except UnicodeEncodeError:
                                message += str(msg.encode("ascii", "ignore"))
                        message += color_end
                        if tail:
                            message += "\n"

                        # Print it on the buffer handler
                        if msg:
                            handlerbuf.write(message)
                            handlerbuf.flush()
                        else:
                            # If we shouldn't show the output, say to the
                            # caller we should output something
                            return True

                    # Autoclose handler when done
                    if msg and isinstance(handler, str):
                        handlerbuf.close()

        # If we shouldn't show the output
        if not msg:
            # Say to the caller we shouldn't output anything
            return False

    def primary(self, msg, header=True, tail=True, show_line_info=False):
        if show_line_info:  # pragma: no cover
            line = currentframe().f_back.f_lineno
            filename = currentframe().f_back.f_code.co_filename.replace(
                getcwd(),
                ".",
            )
            if (
                len(filename) >= 2
                and filename[0] == "."
                and filename[1] == "/"
            ):
                filename = filename[2:]
        else:
            line = None
            filename = None

        self.__warningerror(
            msg,
            "PRIMARY",
            "blue",
            "primary",
            line,
            filename,
            header,
            tail,
        )

    def secondary(self, msg, header=True, tail=True, show_line_info=False):
        if show_line_info:  # pragma: no cover
            line = currentframe().f_back.f_lineno
            filename = currentframe().f_back.f_code.co_filename.replace(
                getcwd(),
                ".",
            )
            if (
                len(filename) >= 2
                and filename[0] == "."
                and filename[1] == "/"
            ):
                filename = filename[2:]
        else:
            line = None
            filename = None

        self.__warningerror(
            msg,
            "SECONDARY",
            "purple",
            "secondary",
            line,
            filename,
            header,
            tail,
        )

    def success(self, msg, header=True, tail=True, show_line_info=False):
        if show_line_info:  # pragma: no cover
            line = currentframe().f_back.f_lineno
            filename = currentframe().f_back.f_code.co_filename.replace(
                getcwd(),
                ".",
            )
            if (
                len(filename) >= 2
                and filename[0] == "."
                and filename[1] == "/"
            ):
                filename = filename[2:]
        else:
            line = None
            filename = None

        self.__warningerror(
            msg,
            "SUCCESS",
            "green",
            "success",
            line,
            filename,
            header,
            tail,
        )

    def danger(self, msg, header=True, tail=True, show_line_info=False):
        if show_line_info:  # pragma: no cover
            line = currentframe().f_back.f_lineno
            filename = currentframe().f_back.f_code.co_filename.replace(
                getcwd(),
                ".",
            )
            if (
                len(filename) >= 2
                and filename[0] == "."
                and filename[1] == "/"
            ):
                filename = filename[2:]
        else:
            line = None
            filename = None

        self.__warningerror(
            msg,
            "DANGER",
            "simplered",
            "danger",
            line,
            filename,
            header,
            tail,
        )

    def warning(self, msg, header=True, tail=True, show_line_info=True):
        if show_line_info:  # pragma: no cover
            line = currentframe().f_back.f_lineno
            filename = currentframe().f_back.f_code.co_filename.replace(
                getcwd(),
                ".",
            )
            if (
                len(filename) >= 2
                and filename[0] == "."
                and filename[1] == "/"
            ):
                filename = filename[2:]
        else:
            line = None
            filename = None

        self.__warningerror(
            msg,
            "WARNING",
            "yellow",
            "warning",
            line,
            filename,
            header,
            tail,
        )

    def info(self, msg, header=True, tail=True, show_line_info=False):
        if show_line_info:  # pragma: no cover
            line = currentframe().f_back.f_lineno
            filename = currentframe().f_back.f_code.co_filename.replace(
                getcwd(),
                ".",
            )
            if (
                len(filename) >= 2
                and filename[0] == "."
                and filename[1] == "/"
            ):
                filename = filename[2:]
        else:
            line = None
            filename = None

        self.__warningerror(
            msg,
            "INFO",
            "cyan",
            "info",
            line,
            filename,
            header,
            tail,
        )

    def error(self, msg, header=True, tail=True, show_line_info=True):
        if show_line_info:  # pragma: no cover
            line = currentframe().f_back.f_lineno
            filename = currentframe().f_back.f_code.co_filename.replace(
                getcwd(),
                ".",
            )
            if (
                len(filename) >= 2
                and filename[0] == "."
                and filename[1] == "/"
            ):
                filename = filename[2:]
        else:
            line = None
            filename = None

        self.__warningerror(
            msg,
            "ERROR",
            "red",
            "error",
            line,
            filename,
            header,
            tail,
        )

    def debug_with_style(
        self,
        msg,
        title,
        color,
        kind,
        show_line_info,
        header=True,
        tail=True,
    ):
        if show_line_info:  # pragma: no cover
            line = currentframe().f_back.f_lineno
            filename = currentframe().f_back.f_code.co_filename.replace(
                getcwd(),
                ".",
            )
            if (
                len(filename) >= 2
                and filename[0] == "."
                and filename[1] == "/"
            ):
                filename = filename[2:]
        else:
            line = None
            filename = None

        self.__warningerror(
            msg,
            title,
            color,
            kind,
            line,
            filename,
            header,
            tail,
        )

    def __warningerror(
        self,
        msg,
        prefix,
        color,
        kind,
        line,
        filename,
        header,
        tail,
    ):
        # Retrieve the name of the class
        clname = self.__class__.__name__

        # Retrieve tabular
        if "tabular" in self.__indebug:  # pragma: no cover
            tabular = self.__indebug["tabular"]
        else:
            tabular = ""

        # For each element inside indebug
        for name in self.__indebug:
            # If this is no deepeness key, keep going
            if name not in ["deepness", "tabular"]:
                # Get file output handler and indebug list
                (handler, indebug) = self.__indebug[name]

                if "-*{}".format(kind) not in indebug:
                    if isinstance(handler, str):
                        # Open handler buffer
                        handlerbuf = open(handler, "a")
                    else:
                        handlerbuf = handler

                    # Get color
                    if name == "screen" or name[-1] == "*":
                        color_ini = self.color(color)
                        color_end = self.color("close")
                    else:
                        color_ini = self.color(None)
                        color_end = color_ini

                    # Build the message
                    message = color_ini
                    if header:
                        # Set line head name
                        if self.__inname:
                            headname = self.__inname
                        else:
                            headname = clname

                        now = datetime.now()
                        message += "\n%s - %02d/%02d/%d %02d:%02d:%02d " % (
                            prefix,
                            now.day,
                            now.month,
                            now.year,
                            now.hour,
                            now.minute,
                            now.second,
                        )
                        if filename or line:
                            message += "{}:{}: ".format(filename, line)
                        message += "%-15s - %s" % (headname, tabular)
                    if msg:
                        try:
                            message += str(msg)
                        except UnicodeEncodeError:
                            try:
                                message += str(msg.encode("ascii", "ignore"))
                            except Exception:
                                message += (
                                    "*** "
                                    "Message is in Binary format, "
                                    "I tried to convert to ASCII ignoring "
                                    "encoding errors but it failed as well. "
                                    "***"
                                )
                    message += color_end
                    if tail:
                        message += "\n"

                    # Print it on the buffer handler
                    handlerbuf.write(message)
                    handlerbuf.flush()

                    # Autoclose handler when done
                    if isinstance(handler, str):
                        handlerbuf.close()
