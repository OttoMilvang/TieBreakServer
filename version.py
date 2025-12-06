# -*- coding: utf-8 -*-
"""
Created on Tue Apr 29 09:21:45 2025

@author: otto
"""

def version():
    return {
        "version": "1.7.40",
        "version_major": 1,
        "version_minor": 7,
        "version_patch": 40,
    }

if __name__ == "__main__":
    ver = version()
    print("Version: " + ver["version"]) 