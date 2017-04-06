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
Debugger helps to debug the system
'''

__version__ = "2016041200"

__all__ = ['Debugger','lineno']

import time
import datetime
import inspect

from codenerix.lib.colors import colors

def lineno():
    '''
    Returns the current line number in our program.
    '''
    return inspect.currentframe().f_back.f_lineno

class Debugger(object):
    
    __indebug={}
    __inname=None
    
    def __autoconfig(self):
        # Define debug configuration
        import sys
        debugger = {}
        debugger['screen'] = (sys.stdout, ['*'])
        #debugger['log'] = (open("log/debug.log","a"), ['*'] )
        self.set_debug(debugger)
    
    def set_debug(self,debug=None):
        if debug is None:
            self.__autoconfig()
        else:
            if type(debug) is dict:
                # Set the deepness system
                idebug=debug.copy()
                if 'deepness' in debug:
                    if debug['deepness']:
                        idebug['deepness']-=1
                    else:
                        idebug={}
                
                # Save internal debugger
                self.__indebug=idebug
            else:
                raise IOError("Argument is not a dictionary")
    
    def get_debug(self):
        return self.__indebug
    
    def set_name(self,name):
        self.__inname=name
    
    def get_name(self):
        return self.__inname
    
    def color(self,color):
        # Colors$
        if color in colors:
            (darkbit,subcolor)=colors[color]
            return "\033[%1d;%02dm" % (darkbit,subcolor)
        else:
            if color:
                self.debug("\033[1;31mColor '%s' unknown\033[1;00m\n" % (color))
            return ''
    
    def debug(self,msg=None,header=True,color=None, tail=True):
        
        # Retrieve the name of the class
        clname=self.__class__.__name__
        
        # Retrieve tabular
        if 'tabular' in self.__indebug:
            tabular=self.__indebug['tabular']
        else:
            tabular=''
        
        # For each element inside indebug
        for name in self.__indebug:
            
            # If this is no deepeness key, keep going
            if name not in ['deepness','tabular']:
                
                # Get color
                if name!='screen': color=None
                color_ini=self.color(color)
                color_end=self.color('close')
                
                # Get file output handler and indebug list
                (handler,indebug)=self.__indebug[name]
                if msg and type(handler)==str:
                    # Open handler buffer
                    handlerbuf=open(handler,"a")
                else:
                    handlerbuf=handler
                
                # Look up if the name of the class is inside indebug
                if (clname in indebug) or (('*' in indebug) and ('-%s' % (clname) not in indebug)):
                    
                    # Set line head name
                    if self.__inname:
                        headname=self.__inname
                    else:
                        headname=clname
                    
                    # Build the message
                    message=color_ini
                    if header:
                        now=datetime.datetime.fromtimestamp(time.time())
                        message+="%02d/%02d/%d %02d:%02d:%02d %-15s - %s" % (now.day, now.month, now.year, now.hour, now.minute, now.second, headname, tabular)
                    if msg:
                        message+=str(msg)
                    message+=color_end
                    if tail:
                        message+='\n'
                    
                    # Print it on the buffer handler
                    if msg:
                        handlerbuf.write(message)
                        handlerbuf.flush()
                    else:
                        # If we shouldn't show the output, say to the caller we should output something
                        return True
                
                # Autoclose handler when done
                if msg and type(handler)==str:
                    handlerbuf.close()
        
        # If we shouldn't show the output
        if not msg:
            # Say to the caller we shouldn't output anything
            return False
    
    def warning(self,msg,header=True,tail=True):
        self.warningerror(msg,header,'WARNING','yellow',tail)
    
    def error(self,msg,header=True,tail=True):
        self.warningerror(msg,header,'ERROR','red',tail)
    
    def warningerror(self,msg,header,prefix,color,tail):
        
        # Retrieve the name of the class
        clname=self.__class__.__name__
        
        # Retrieve tabular
        if 'tabular' in self.__indebug:
            tabular=self.__indebug['tabular']
        else:
            tabular=''
        
        # For each element inside indebug
        for name in self.__indebug:
            
            # If this is no deepeness key, keep going
            if name not in ['deepness','tabular']:
                
                # Get file output handler and indebug list
                (handler,indebug)=self.__indebug[name]
                if type(handler)==str:
                    # Open handler buffer
                    handlerbuf=open(handler,"a")
                else:
                    handlerbuf=handler
                
                # Get color
                if name!='screen': color=None
                color_ini=self.color(color)
                color_end=self.color('close')
                
                # Build the message
                message=color_ini
                if header:
                    # Set line head name
                    if self.__inname:
                        headname=self.__inname
                    else:
                        headname=clname
                    
                    now=datetime.datetime.fromtimestamp(time.time())
                    message+="\n%s - %02d/%02d/%d %02d:%02d:%02d %-15s - %s" % (prefix,now.day, now.month, now.year, now.hour, now.minute, now.second, headname, tabular)
                if msg:
                    message+=str(msg)
                message+=color_end
                if tail:
                    message+='\n'
                
                # Print it on the buffer handler
                handlerbuf.write(message)
                handlerbuf.flush()
                
                # Autoclose handler when done
                if type(handler)==str:
                    handlerbuf.close()

