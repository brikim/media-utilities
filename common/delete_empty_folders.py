#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import sys

def delete_empty_folders(pathsToCheck, scriptName):
    # Delete empty folders in physical path if any exist
    for path in pathsToCheck:
        folderRemoved = True
        while folderRemoved == True:
            folderRemoved = False
            for dirpath, dirnames, filenames in os.walk(path, topdown=False):
                if not dirnames and not filenames:
                    shutil.rmtree(dirpath, ignore_errors=True)
                    sys.stdout.write("{}: Deleting Empty Folder: {}\n".format(scriptName, dirpath))
                    folderRemoved = True