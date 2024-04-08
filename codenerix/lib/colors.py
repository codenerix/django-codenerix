#!/usr/bin/env python3
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
Deprecated library in favor for codenerix-lib
"""

import inspect
import sys
from os import getcwd

from codenerix_lib.colors import *  # noqa: F403,F401

# Show a warning message with information about who is importing this library
cf = inspect.currentframe()
me = True
who = None
while cf:
    if cf.f_code.co_name == "<module>":
        if me:
            me = False
        else:
            who = (
                cf.f_code.co_filename.replace(getcwd(), "."),
                cf.f_lineno,
                cf.f_code.co_name,
            )
            break
    cf = cf.f_back
if not who:
    who = ("<unknown>", 0, "<unknown>")

print(
    f"""

========================== W A R N I N G =============================
DJANGO-CODENERIX: you have imported 'lib.colors' which is DEPRECATED
it will not work in newer versions, instead use 'codenerix_lib.colors'
from codenerix-lib package", please update your code. This message was
shown because is being imported by:
'{who[0]}' at line {who[1]}
======================================================================

      """,
    file=sys.stderr,
)
