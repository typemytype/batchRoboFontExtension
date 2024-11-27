import AppKit

from mojo.tools import CallbackWrapper

import batch
# just import batchCompileTools to make them available everywhere else
import batchCompileTools


class BatchMenu(object):

    def __init__(self):
        title = "Batch..."
        mainMenu = AppKit.NSApp().mainMenu()
        fileMenu = mainMenu.itemWithTitle_("File")

        if not fileMenu:
            return

        fileMenu = fileMenu.submenu()

        if fileMenu.itemWithTitle_(title):
            return

        index = fileMenu.indexOfItemWithTitle_("Generate Font")
        self.target = CallbackWrapper(self.callback)

        newItem = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, "action:", "")
        newItem.setTarget_(self.target)

        fileMenu.insertItem_atIndex_(newItem, index + 1)

    def callback(self, sender):
        OpenWindow(batch.BatchController)


BatchMenu()
