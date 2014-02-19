axrelay is an anonymizing xmpp relay component for xmpp servers.


Quickstart
==========

Install libmemcached:

    brew install libmemcached  # or equivalent on your system

Install axrelay in a virtualenv using pip:

    virtualenv axrelay && axrelay/bin/pip install -e 'git+https://github.com/getlantern/axrelay.git#egg=axrelay-dev'

Run the axrelay binary:

    axrelay/bin/axrelay help

Create a configuration file (becoming root as needed):

    cp axrelay/src/axrelay/sample.conf /etc/axrelay.conf
    vi /etc/axrelay.conf

To run against a local xmpp server for testing, prosody is installable via homebrew:

    brew install https://prosody.im/files/homebrew/prosody.rb

To run against a local memcached:

    /usr/local/opt/memcached/bin/memcached

Finally, run axrelay:

    axrelay/bin/axrelay run
