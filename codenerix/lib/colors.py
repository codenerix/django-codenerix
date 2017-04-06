#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# django-codenerix
#
# Copyright 2017 Centrologic Computational Logistic Center S.L.
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
'''
Colors definition
'''

__version__ = "201109111106"

__all__ = ['colors']


colors={}

colors['simplegrey']   = (0, 30)
colors['simplered']    = (0, 31)
colors['simplegreen']  = (0, 32)
colors['simpleyellow'] = (0, 33)
colors['simpleblue']   = (0, 34)
colors['simplepurple'] = (0, 35)
colors['simplecyan']   = (0, 36)
colors['simplewhite']  = (0, 37)

colors['grey']   = (1, 30)
colors['red']    = (1, 31)
colors['green']  = (1, 32)
colors['yellow'] = (1, 33)
colors['blue']   = (1, 34)
colors['purple'] = (1, 35)
colors['cyan']   = (1, 36)
colors['white']  = (1, 37)

colors['close']  = (1, 0)

def colorize(msg,color=None):
    # Colors
    if color in colors:
        (darkbit,subcolor)=colors[color]
    else:
        (darkbit,subcolor)=(1,0)
    
    # Prepare the message
    result ="\033[%1d;%02dm" % (darkbit,subcolor)
    result+=msg
    result+="\033[%1d;%02dm" % (1,0)
    
    # Return the result
    return result

if __name__ == "__main__":
    
    # Reorder colors
    keys = []
    for key in colors.keys():
        keys.append((colors[key][0],colors[key][1],key))
    keys.sort()
    
    # Show up all colors
    for color in keys:
        # Get the color information
        (simplebit, subcolor) = colors[color[2]]
        # Show it
        print("{0:1d}:{1:02d} - \033[{2:1d};{3:02d}m{4:<14s}\033[1;00m{5:<s}".format(simplebit, subcolor, simplebit, subcolor, color[2], color[2]))

