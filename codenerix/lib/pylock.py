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
Library to handle lockers over files
"""

__version__ = "2015061200"

import fcntl
import os
import tempfile
import unittest

__all__ = ["pylock", "PyLock", "AlreadyLocked"]


class PyLock:
    """
    Function to control locking flags over a file
    """

    def __init__(self, lockfile, locktype):
        """
        Parameters:
        - `lockfile`: name of the file to check/apply the locking.
        - `locktype`: possible values are:
                wait: on a call to lock() function, the system will wait to
                        get the locker
                lock: on a call to lock() function, if locked the system will
                        raise an AlreadyLocked exception
        """

        # Save config
        self.__lockfile = lockfile
        self.__locktype = locktype
        self.__fd = None

        # Check file exists and create it if it does not
        if not os.path.exists(lockfile):
            file = open(lockfile, "w")
            file.close()

        # Check locktype
        if locktype not in ["wait", "lock"]:
            raise TypeError("Locking type unkown")

    def __del__(self):
        """
        when dying make sure the lock become free
        """
        # If file was open, close it and delete it!
        if self.__fd:
            self.__fd.close()

    def lock(self):
        """
        Try to get locked the file
        - the function will wait until the file is unlocked if 'wait' was
            defined as locktype
        - the funciton will raise AlreadyLocked exception if 'lock' was
            defined as locktype
        """

        # Open file
        self.__fd = open(self.__lockfile, "w")

        # Get it locked
        if self.__locktype == "wait":
            # Try to get it locked until ready
            fcntl.flock(self.__fd.fileno(), fcntl.LOCK_EX)
        elif self.__locktype == "lock":
            # Try to get the locker if can not raise an exception
            try:
                fcntl.flock(self.__fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise AlreadyLocked("File is already locked")

    def free(self):
        """
        Set the locked file free
        """

        # Close file
        self.__fd.close()

        # Delete it
        try:
            os.unlink(self.__lockfile)
        except Exception:
            pass


# Compatibility with older versions
pylock = PyLock


# Exceptions classes
class AlreadyLocked(Exception):
    def __init__(self, string):
        self.string = string

    def __str__(self):
        return self.string


# Testing
class TestPylock(unittest.TestCase):
    """
    Testing class for pylock
    """

    def setUp(self):
        pass

    def testpylock(self):
        # Get temporal file
        f = tempfile.NamedTemporaryFile(delete=False)
        f.close()

        locker1 = PyLock(f.name, "lock")
        locker1.lock()

        locker2 = PyLock(f.name, "lock")
        self.assertRaises(AlreadyLocked, locker2.lock)
        locker1.free()
        locker2.lock()
        self.assertRaises(AlreadyLocked, locker1.lock)
        locker2.free()

        # Remove the temporal file
        if os.path.exists(f.name):
            os.unlink(f.name)
            raise OSError("File should be already deleted by the library")


# Base call
if __name__ == "__main__":
    unittest.main()
