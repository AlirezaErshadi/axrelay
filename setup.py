#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
try:
    from setuptools import setup, Command
except ImportError:
    from distutils.core import setup, Command

setup(
    name="axrelay",
    version="0.1",
    description="",
    long_description="",
    author='Willie Forkner',
    author_email='forkner@beercan.me',
    url='http://github.com/getlantern/axrelay',
    license='MIT',
    platforms=['any'],
    packages=["axrelay"],
    install_requires=['sleekxmpp', "dnspython",
                      "pylibmc==1.2.3", "pycrypto"],
    classifiers=[],
    entry_points="""
        [console_scripts]
        axrelay = axrelay.cli:main
    """
)
