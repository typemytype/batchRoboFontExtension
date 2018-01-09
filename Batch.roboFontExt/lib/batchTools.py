from __future__ import print_function

import AppKit
import os

from mojo.roboFont import version

settingsIdentifier = "com.typemytype.toolbox"

if version < 2:
    ufoVersion = 2
else:
    ufoVersion = 3


class Report(object):

    INDENT = "    "

    def __init__(self):
        self._data = []
        self._indent = 0

    def append(self, value):
        try:
            value = value.encode("utf-8")
        except:
            pass
        self._data.append(value)

    def indent(self, value=None):
        if value is None:
            self._indent += 1
        else:
            self._indent = value

    def dedent(self):
        self._indent -= 1
        if self._indent < 0:
            self._indent = 0

    def write(self, value):
        indent = self.INDENT * self._indent
        value = value.replace("\n", "\n%s" % indent)
        self.append("%s%s" % (indent, value))

    def writeTitle(self, value, underline="*"):
        self.write(value)
        self.write(underline * len(value))

    def writeItems(self, items):
        for i in items:
            if i:
                self.write(i)

    def newLine(self):
        self.append("")

    def writeDict(self, d):
        maxLength = 0
        for key in d:
            length = len(key)
            if length > maxLength:
                maxLength = length

        for key in sorted(d):
            value = d[key]
            t = "%s = %s" % (key.ljust(maxLength), value)
            self.write(t)

    def writeList(self, l):
        for i in l:
            self.write(str(i))

    def save(self, path):
        f = file(path, "w")
        f.write(self.get())
        f.close()

    def get(self):
        return "\n".join(self._data)


def updateWithDefaultValues(data, defaults):
    for key, value in defaults.items():
        if key in data:
            continue
        data[key] = value


def buildTree(path):
    if not os.path.exists(path):
        os.makedirs(path)


class TaskRunner(AppKit.NSObject):

    def __new__(cls, *args, **kwargs):
        return cls.alloc().init()

    def __init__(self, callback, threaded, progress, kwargs=dict()):
        self._callback = callback
        self._kwargs = kwargs
        self._progress = progress

        if threaded:
            self._thread = AppKit.NSThread.alloc().initWithTarget_selector_object_(self, "runTask:", None)
            self._thread.start()
        else:
            self.runTask_(None)

    def runTask_(self, sender):
        try:
            self._callback(progress=self._progress, **self._kwargs)
        except:
            import traceback
            errorMessage = [
                "*" * 30,
                traceback.format_exc(),
                "*" * 30
            ]
            print("\n".join(errorMessage))
        self._progress.close()
