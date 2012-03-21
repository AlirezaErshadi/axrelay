#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
try:
    from setuptools import setup, Command
except ImportError:
    from distutils.core import setup, Command

setup(
    name             = "axr",
    version          = "0.1",
    description      = "",
    long_description = "",
    author       = 'Willie Forkner',
    author_email = 'forkner@beercan.me',
    url          = 'http://github.com/forkner/axr',
    license      = 'MIT',
    platforms    = [ 'any' ],
    packages     = ["axr"],
    install_requires     = [ 'sleekxmpp', "dnspython", "pylibmc" ],
    classifiers  = [],
    entry_points="""
       [console_scripts]
       anonymous_xmpp_relay = axr.relay:main
    """
)
