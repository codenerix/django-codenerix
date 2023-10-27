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

import base64
import hashlib
import os
from os import path

from django import template
from django.conf import settings
from django.contrib.auth.models import Group
from django.template import Library, NodeList, Variable
from PIL import Image, ImageDraw, ImageFont

register = Library()


@register.filter
def txt2img(
    text,
    FontSize=14,  # noqa: N803
    bg="#ffffff",
    fg="#000000",
    font="FreeMono.ttf",
):
    font_dir = (
        settings.MEDIA_ROOT + "/txt2img/"
    )  # Set the directory to store the images
    img_name_temp = (
        text + "-" + bg.strip("#") + "-" + fg.strip("#") + "-" + str(FontSize)
    )  # Remove hashes
    try:
        # python 2.7
        img_name_encode = hashlib.md5(
            img_name_temp,
            usedforsecurity=False,
        ).hexdigest()
    except TypeError:
        # python 3.x
        img_name_temp = bytes(img_name_temp, encoding="utf-8")
        img_name_encode = hashlib.md5(
            img_name_temp,
            usedforsecurity=False,
        ).hexdigest()

    img_name = "%s.jpg" % (img_name_encode)

    if path.exists(font_dir + img_name):  # Make sure img doesn't exist already
        pass
    else:
        font_size = FontSize
        fnt = ImageFont.truetype(font_dir + font, font_size)
        w, h = fnt.getsize(text)
        img = Image.new("RGBA", (w, h), bg)
        draw = ImageDraw.Draw(img)
        draw.fontmode = "0"
        draw.text((0, 0), text, font=fnt, fill=fg)
        img.save(font_dir + img_name, "JPEG", quality=100)
    imgtag = (
        '<img src="'
        + settings.MEDIA_URL
        + "txt2img/"
        + img_name
        + '" alt="'
        + text
        + '" />'
    )
    return imgtag


@register.simple_tag
def file64(path, basepath):
    """
    Returns the given path as a Base 64 IMAGE tag
    """

    # Attach Base 64 string
    finalpath = basepath + "/" + path
    if os.path.exists(finalpath):
        with open(finalpath, "rb") as binary:
            img = base64.b64encode(binary.read()).decode()
    else:
        raise OSError(f"File not found at '{finalpath}'")

    return img


@register.simple_tag
def static64(path):
    """
    Returns the given path from STATIC as a Base 64 IMAGE tag
    """

    return file64(path, settings.STATIC_ROOT)


@register.simple_tag
def media64(path):
    """
    Returns the given path from MEDIA as a Base 64 IMAGE tag
    """

    return file64(path, settings.MEDIA_ROOT)


@register.tag
def ifusergroup(parser, token):
    """Check to see if the currently logged in user belongs to a specific
    group. Requires the Django authentication contrib app and middleware.

    Usage: {% ifusergroup Admins %} ... {% endifusergroup %}, or
           {% ifusergroup Admins Clients Sellers %}
                ...
           {% else %}
                ...
           {% endifusergroup %}
    """
    try:
        tokensp = token.split_contents()
        groups = []
        groups += tokensp[1:]
    except ValueError:
        raise template.TemplateSyntaxError(
            "Tag 'ifusergroup' requires at least 1 argument.",
        )

    nodelist_true = parser.parse(("else", "endifusergroup"))
    token = parser.next_token()

    if token.contents == "else":
        nodelist_false = parser.parse(
            tuple(
                [
                    "endifusergroup",
                ],
            ),
        )
        parser.delete_first_token()
    else:
        nodelist_false = NodeList()

    return GroupCheckNode(groups, nodelist_true, nodelist_false)


class GroupCheckNode(template.Node):
    def __init__(self, groups, nodelist_true, nodelist_false):
        self.groups = groups
        self.nodelist_true = nodelist_true
        self.nodelist_false = nodelist_false

    def render(self, context):
        user = Variable("user").resolve(context)

        if not user.is_authenticated:
            return self.nodelist_false.render(context)

        allowed = False
        for checkgroup in self.groups:
            try:
                group = Group.objects.get(name=checkgroup)
            except Group.DoesNotExist:
                break

            if group in user.groups.all():
                allowed = True
                break

        if allowed:
            return self.nodelist_true.render(context)
        else:
            return self.nodelist_false.render(context)
