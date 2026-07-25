# -*- coding: utf-8 -*-
"""
Make the modules in the repository root importable from the tests,
so that "python -m pytest tests/" and "pytest tests/" both work.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
