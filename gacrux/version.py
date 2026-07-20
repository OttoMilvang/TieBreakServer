# -*- coding: utf-8 -*-
"""
Created on Tue Apr 29 09:21:45 2025

@author: otto
"""

__version__ = "1.9.57"

def version():
    return {
        "version": __version__,
        "version_major": 1,
        "version_minor": 9,
        "version_patch": 57,
        "version_date": "2026-07-20", 
       }

if __name__ == "__main__":
    ver = version()
    print("Version: " + ver["version"]) 