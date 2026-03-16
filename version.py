# -*- coding: utf-8 -*-
"""
Created on Tue Apr 29 09:21:45 2025

@author: otto
"""

def version():
    return {
        "version": "1.8.49",
        "version_major": 1,
        "version_minor": 8,
        "version_patch": 49,
        "version_date": "2026-03-16",
    }

if __name__ == "__main__":
    ver = version()
    print("Version: " + ver["version"]) 