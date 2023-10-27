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

import decimal
import importlib
import io
import json

# System
import os
import random
import time
import zipfile
from datetime import datetime
from uuid import UUID

from dateutil.tz import tzutc
from django.conf import settings
from django.core.cache import cache

# Django
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template import TemplateDoesNotExist
from django.template.loader import get_template as django_get_template
from django.urls import reverse_lazy
from django.utils import dateparse
from django.utils.encoding import smart_str
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import View
from unidecode import unidecode


def epochdate(timestamp):
    """
    Convet an epoch date to a tuple in format ("yyyy-mm-dd","hh:mm:ss")
    Example: "1023456427" -> ("2002-06-07","15:27:07")

    Parameters:
    - `timestamp`: date in epoch format
    """

    dt = datetime.fromtimestamp(float(timestamp)).timetuple()
    fecha = "{:d}-{:02d}-{:02d}".format(dt.tm_year, dt.tm_mon, dt.tm_mday)
    hora = "{:02d}:{:02d}:{:02d}".format(dt.tm_hour, dt.tm_min, dt.tm_sec)
    return (fecha, hora)


def date2string(dtime, formt, default):
    try:
        list_type = [
            str,
            unicode,
        ]
    except NameError:
        list_type = [
            str,
        ]

    if dtime:
        if ("year" in dir(dtime)) and (dtime.year < 1900):
            return default
        elif type(dtime) in list_type:
            return dtime
        else:
            return dtime.strftime(formt)
    else:
        return default


def daterange_filter(value, variable):
    start = dateparse.parse_datetime(value["startDate"])
    end = dateparse.parse_datetime(value["endDate"])
    result = {
        "{}__gte".format(variable): start,
        "{}__lte".format(variable): end,
    }
    return result


def timezone_serialize(d, prettify=False):
    if d is None:
        result = None
    else:
        if d.tzinfo:
            d = d.astimezone(tzutc()).replace(tzinfo=None)
        if prettify:
            result = d.strftime(settings.DATETIME_INPUT_FORMATS[0])
        else:
            result = d.isoformat() + "Z"
    return result


def timezone_deserialize(string):
    if string is None:
        result = None
    else:
        result = dateparse.parse_datetime(string)
    return result


def zeropad(number, width):
    return "{number:0{width}d}".format(width=width, number=number)


def monthname(value):
    if value == 1:
        return _("January")
    elif value == 2:
        return _("February")
    elif value == 3:
        return _("March")
    elif value == 4:
        return _("April")
    elif value == 5:
        return _("May")
    elif value == 6:
        return _("June")
    elif value == 7:
        return _("July")
    elif value == 8:
        return _("August")
    elif value == 9:
        return _("September")
    elif value == 10:
        return _("Octuber")
    elif value == 11:
        return _("November")
    elif value == 12:
        return _("December")
    else:
        return None


# Name unify
def nameunify(name, url=False):
    # Make unicode
    name = smart_str(name)

    # Get it on lower
    namelow = unidecode(name).lower().strip(" \t\n\r")

    # Define valid characters
    allowed_characters = "abcdefghijklmnopqrstuvwxyz0123456789_-"
    if url:
        namelow = namelow.replace(" ", "-").replace("_", "-")
    else:
        namelow = namelow.replace("-", "").replace(" ", "_")

    # Replace all unknown characters
    result = ""
    for c in namelow:
        if c in allowed_characters:
            result += c

    if result[-1] in ("-", "_"):
        result = nameunify(result[0:-1], url)
    # Return the cleaned result
    return result


def get_profile(user):
    # Check if it has admin rights admin
    try:
        is_admin = bool(user.is_superuser or user.groups.get(name="Admins"))
    except Exception:
        is_admin = False

    if is_admin:
        # Administrator use root
        profile = "admin"
    else:
        profile = None

    # Return profile
    return profile


def get_profiled_paths(path, user, lang, extension):
    paths = []
    if user:
        # Check if it has admin rights admin
        profile = get_profile(user)

        # Define the base_path to use
        paths.append("{}.{}".format(user.username, lang))
        paths.append(user.username)
        if profile:
            paths.append("{}.{}".format(profile, lang))
            paths.append(profile)
        if profile != "admin":
            paths.append("user.{}".format(lang))
            paths.append("user")

    # Add an empty path
    paths.append(lang)
    paths.append("")

    # Split path name
    pathsp = path.split(".")
    if pathsp[-1] == extension:
        basepath = ".".join(pathsp[:-1])
    else:
        basepath = path

    # Return paths and basepath
    return (paths, basepath)


def get_template(template, user, lang, extension="html", raise_error=True):
    # Get profiled paths
    (templates, templatepath) = get_profiled_paths(
        template,
        user,
        lang,
        extension,
    )

    # Check templates
    test = []
    found = None
    for temp in templates:
        if len(temp):
            addon = ".%s" % (temp)
        else:
            addon = ""
        target = "%s%s.%s" % (templatepath, addon, extension)
        test.append(target)
        try:
            django_get_template(target)
            found = target
            break
        except TemplateDoesNotExist:
            pass

    # Return target template
    if found:
        return found
    else:
        if raise_error:
            raise OSError(
                "I couldn't find a valid template, I have tried: {}".format(
                    test,
                ),
            )
        else:
            return test


def get_static(desired, user, lang, default, extension="html", relative=False):
    # Get profiled paths
    (paths, basepath) = get_profiled_paths(desired, user, lang, extension)

    # Check paths
    found = None
    for temp in paths:
        if len(temp):
            addon = ".%s" % (temp)
        else:
            addon = ""
        target = "%s%s.%s" % (basepath, addon, extension)
        if (
            hasattr(settings, "STATIC_ROOT")
            and settings.STATIC_ROOT
            and os.path.exists(os.path.join(settings.STATIC_ROOT, target))
        ):
            if relative:
                found = os.path.join(settings.STATIC_URL, target)
            else:
                found = target
            break

    # Return target template
    if found:
        # Return the one we found
        return found
    else:
        # We didn't find any, return default one
        return default


def direct_to_template(request, template, lang):
    template = get_template(template, request.user)
    return render(request, template, lang)


def model_inspect(obj):
    """
    Analize itself looking for special information, right now it returns:
    - Application name
    - Model name
    """
    # Prepare the information object
    info = {}
    if hasattr(obj, "_meta"):
        info["verbose_name"] = getattr(obj._meta, "verbose_name", None)
    else:
        info["verbose_name"] = None

    # Get info from the object
    if hasattr(obj, "model") and obj.model:
        model = obj.model
    else:
        model = obj.__class__

    namesp = str(model)
    namesp = (
        namesp.replace("<class ", "")
        .replace(">", "")
        .replace("'", "")
        .split(".")
    )

    # Remember information
    info["appname"] = namesp[-3]
    info["modelname"] = namesp[-1]
    info["model"] = model

    # Return the info
    return info


def upload_path(instance, filename):
    """
    This method is created to return the path to upload files. This path
    must be different from any other to avoid problems.
    """
    path_separator = "/"
    date_separator = "-"
    ext_separator = "."
    empty_string = ""
    # get the model name
    model_name = model_inspect(instance)["modelname"]

    # get the string date
    date = datetime.now().strftime("%Y-%m-%d").split(date_separator)
    curr_day = date[2]
    curr_month = date[1]
    curr_year = date[0]

    split_filename = filename.split(ext_separator)
    filename = empty_string.join(split_filename[:-1])
    file_ext = split_filename[-1]

    new_filename = empty_string.join(
        [filename, str(random.random()).split(ext_separator)[1]],
    )
    new_filename = ext_separator.join([new_filename, file_ext])
    string_path = path_separator.join(
        [model_name, curr_year, curr_month, curr_day, new_filename],
    )
    # the path is built using the current date and the modelname
    return string_path


def get_class(func):
    if not getattr(func, "__closure__", None):
        return

    for closure in func.__closure__:
        contents = closure.cell_contents

        if not contents:
            continue

        if getattr(contents, "__bases__", None) and issubclass(contents, View):
            return contents

        result = get_class(contents)
        if result:
            return result


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def clean_memcache_item(key, item):
    # clean item from key
    result = cache.get(key)
    if result is not None and item in result:
        result.pop(item)
        cache.set(key, result)


class CodenerixEncoder:
    codenerix_numeric_dic = {
        # Basic dicts
        "num": "0123456789",
        "alpha": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "alphanc": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "alphanum": "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "alphanumnc": "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",  # noqa: E501
        # Original dicts
        "hex36": "ENWR6MV71JOQHADUGFCYZ25X3B4L0KPTSI98",
        "hex16": "54BEF80D1C96A732",
        "hexz17": "Z0123456789ABCDEF",
    }

    def list_encoders(self):
        return self.codenerix_numeric_dic.keys()

    def numeric_encode(self, number, dic="hex36", length=None, cfill=None):
        # Get predefined dictionary
        if dic in self.codenerix_numeric_dic:
            dic = self.codenerix_numeric_dic[dic]

        # Integrity check to dic
        nr = ""
        for c in dic:
            if c not in nr:
                nr += c
            else:
                raise OSError(_("ERROR: dic has repeated elements"))

        # If no cfill
        if cfill is None:
            cfill = dic[0]

        # Find lenght
        ldic = len(dic)

        # Initialize
        string = ""
        div = ldic + 1

        # Process number
        while div >= ldic:
            div = int(number / ldic)
            mod = number % ldic
            string += dic[mod]
            number = div

        # If something left behind
        if div:
            string += dic[div]

        # Fill the string if requested
        if length:
            string += cfill * (length - len(string))

        # Return the reverse string
        return string[::-1]

    def numeric_decode(self, string, dic="hex36"):
        # Get predefined dictionary
        if dic in self.codenerix_numeric_dic:
            dic = self.codenerix_numeric_dic[dic]

        # For each character in the string
        first = True
        number = 0
        for c in string:
            # Not the first loop
            if not first:
                number *= len(dic)
            else:
                first = False

            # Attach the character
            number += dic.index(c)

        # Return the final resulting number
        return number


class InMemoryZip:
    """
    # Compress
    imz = InMemoryZip()
    imz.append("info.dat", data).append("test.txt","asdfasfdsaf")
    datazip = imz.read()

    # Get FILE pointer and read() from it
    FILE = imz.get_fp()
    FILE.read()

    # Uncompress
    imz = InMemoryZip(datazip)$
    info_unzipped = imz.get("info.dat")
    """

    def __init__(self, data=None):
        # Create the in-memory file-like object
        self.in_memory_zip = io.BytesIO()
        if data:
            self.in_memory_zip.write(data)
            self.in_memory_zip.seek(0)

    def get_fp(self):
        self.in_memory_zip.seek(0)
        return self.in_memory_zip

    def append(self, filename_in_zip, file_contents):
        """
        Appends a file with name filename_in_zip and contents of
        file_contents to the in-memory zip.
        """
        # Set the file pointer to the end of the file
        self.in_memory_zip.seek(-1, io.SEEK_END)

        # Get a handle to the in-memory zip in append mode
        zf = zipfile.ZipFile(
            self.in_memory_zip,
            "a",
            zipfile.ZIP_DEFLATED,
            False,
        )

        # Write the file to the in-memory zip
        zf.writestr(filename_in_zip, file_contents)

        # Mark the files as having been created on Windows so that
        # Unix permissions are not inferred as 0000
        for zfile in zf.filelist:
            zfile.create_system = 0

        # Close the ZipFile
        zf.close()

        # Rewind the file
        self.in_memory_zip.seek(0)

        return self

    def get(self, filename):
        self.in_memory_zip.seek(0)
        zf = zipfile.ZipFile(
            self.in_memory_zip,
            "r",
            zipfile.ZIP_DEFLATED,
            False,
        )
        fp = zf.open(filename)
        data = fp.read()
        # Close the ZipFile
        zf.close()
        # Return the result
        return data

    def size(self):
        size = self.in_memory_zip.seek(-1, io.SEEK_END)
        self.in_memory_zip.seek(0)
        return size

    def read(self):
        """Returns a string with the contents of the in-memory zip."""
        self.in_memory_zip.seek(0)
        return self.in_memory_zip.read()

    def writetofile(self, filename):
        """Writes the in-memory zip to a file."""
        f = open(filename, "w")
        f.write(self.read())
        f.close()


def remove_getdisplay(field_name):
    """
    for string 'get_FIELD_NAME_display' return 'FIELD_NAME'
    """
    str_ini = "get_"
    str_end = "_display"
    if (
        str_ini == field_name[0 : len(str_ini)]
        and str_end == field_name[(-1) * len(str_end) :]
    ):
        field_name = field_name[len(str_ini) : (-1) * len(str_end)]
    return field_name


def trace_json_error(struct, path=[]):
    found = None
    kind = type(struct)
    if kind is dict:
        for key in struct:
            found = trace_json_error(struct[key], path + [key])
            if found:
                break
    elif kind is list:
        idx = 0
        for element in struct:
            found = trace_json_error(element, path + [str(idx)])
            if found:
                break
            idx += 1
    else:
        try:
            json.dumps(struct)
        except Exception:
            found = path

    # Return result
    return found


def qobject_builder_string_search(valid_fields, text, conditions="icontains"):
    fields = None
    for word in text.split(" "):
        if word and word[0] == "-":
            word = word[1:]
            neg = True
        else:
            neg = False

        temp = None
        for field in valid_fields:
            qobject = Q(**{"{}__{}".format(field, conditions): word})
            if temp:
                temp |= qobject
            else:
                temp = qobject

        if temp:
            if neg:
                temp = ~Q(temp)

            if fields:
                fields &= temp
            else:
                fields = temp
    return fields


def form_answer(status, answer):
    # Normalize answer
    if "__pk__" not in answer:
        answer["__pk__"] = None
    if "__str__" not in answer:
        answer["__str__"] = "OK"

    # Encode answer
    answer_encoded = urlsafe_base64_encode(
        str.encode(json.dumps(answer)),
    ).decode()

    # Build success URL
    success_url = reverse_lazy(
        "CDNX_status",
        kwargs={"status": "accept", "answer": answer_encoded},
    )

    # Return response
    return HttpResponseRedirect(success_url)


def JSONEncoder_newdefault(  # noqa: N802
    kind=["uuid", "datetime", "time", "decimal"],
):
    """
    JSON Encoder newdfeault is a wrapper capable of encoding several kinds
    Usage:
        from codenerix.helpers import JSONEncoder_newdefault
        JSONEncoder_newdefault()
    """
    JSONEncoder_olddefault = json.JSONEncoder.default  # noqa: N806

    def JSONEncoder_wrapped(self, o):  # noqa: N802
        """
        json.JSONEncoder.default = JSONEncoder_newdefault
        """
        if ("uuid" in kind) and isinstance(o, UUID):
            return str(o)
        if ("datetime" in kind) and isinstance(o, datetime):
            return str(o)
        if ("time" in kind) and isinstance(o, time.struct_time):
            return datetime.fromtimestamp(time.mktime(o))
        if ("decimal" in kind) and isinstance(o, decimal.Decimal):
            return str(o)
        return JSONEncoder_olddefault(self, o)

    json.JSONEncoder.default = JSONEncoder_wrapped


def context_processors_update(context, request):
    """
    Update context with context_processors from settings
    Usage:
        from codenerix.helpers import context_processors_update
        context_processors_update(context, self.request)
    """
    for template in settings.TEMPLATES:
        for context_processor in template["OPTIONS"]["context_processors"]:
            path = context_processor.split(".")
            name = path.pop(-1)
            processor = getattr(
                importlib.import_module(".".join(path)),
                name,
                None,
            )
            if processor:
                context.update(processor(request))
    return context
