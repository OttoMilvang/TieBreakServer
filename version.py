# -*- coding: utf-8 -*-
"""
Created on Tue Apr 29 09:21:45 2025

@author: otto
"""

def version():
    return {
        "version": "1.7.43",
        "version_major": 1,
        "version_minor": 7,
        "version_patch": 43,
    }

if __name__ == "__main__":
    ver = version()
    print("Version: " + ver["version"]) 