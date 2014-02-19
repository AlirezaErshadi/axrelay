Introduction
============

axrelay is an anonymous xmpp relay component for jabber servers


Quickstart
==========

install libmemcached

    $ brew install libmemcached  # or equivalent on your system

install axrelay in a virtualenv using pip:
    
    $ virtualenv axrelay && axrelay/bin/pip install -e 'git+https://github.com/getlantern/axrelay.git#egg=axrelay-dev'


run the axrelay binary:

    $ axrelay/bin/axrelay help


create a configuration file for the component:

    $ cp axrelay/src/axrelay/sample.conf /etc/axrelay.conf
    $ vi /etc/axrelay.conf
    ...


run the component: 

    $ axrelay/bin/axrelay run
