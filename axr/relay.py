#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
"""

from ConfigParser import RawConfigParser
import getpass
import logging
from optparse import OptionParser
import sys

import sleekxmpp
from sleekxmpp.componentxmpp import ComponentXMPP
from sleekxmpp.xmlstream import JID

import base64
import copy
import hashlib
import re

# enforce utf-8 default encoding
if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf8')
else:
    raw_input = input


log = logging.getLogger(__name__)

names_lookup = {}

def garble(name, secret):
    h = hashlib.sha256()
    h.update(secret)
    h.update(name)
    return h.hexdigest()

def garbled_jid(jid, secret, domain):
    if (jid is None): 
        return None
    if (jid.domain == domain):
        log.debug("garble: %s => %s" % (jid, jid))
        return jid
    else:
        garbled = '%s@%s/a' % (garble(jid.full, secret), domain)
        names_lookup[garbled] = jid.full
        log.debug("garble: %s => %s" % (jid, garbled))
        return JID(garbled)
        
def ungarbled_jid(jid, domain):
    if (jid.domain != domain):
        return jid
    else:
        ungarbled = names_lookup.get(jid.full) 
        log.debug("ungarble: %s => %s" % (jid, ungarbled))
        if ungarbled is not None:
            return JID(ungarbled)
        else: 
            return None

class AXRComponent(ComponentXMPP):

    """
    """

    def __init__(self, jid, password, server, port, secret, domain):
        ComponentXMPP.__init__(self, jid, password, server, port)
        self.garble_secret = secret
        self.domain = domain
        self.bot_jid = JID(jid)
        
        # You don't need a session_start handler, but that is
        # where you would broadcast initial presence.

        # The message event is triggered whenever a message
        # stanza is received. Be aware that that includes
        # MUC messages and error messages.
        self.add_event_handler("message", self.message)

    def message(self, msg):
        """
        Process incoming message stanzas. Be aware that this also
        includes MUC messages and error messages. It is usually
        a good idea to check the messages's type before processing
        or sending replies.

        Since a component may send messages from any number of JIDs,
        it is best to always include a from JID.

        Arguments:
            msg -- The received message stanza. See the documentation
                   for stanza objects and the Message stanza to see
                   how it may be used.
        """

        log.debug(msg)
        
        # drop errors, groupchat and unknown
        mtype = msg.get('type')
        if mtype not in ('None', '', 'normal', 'chat'): 
            return

        # is the message to this bot?
        if (msg['to'] == self.bot_jid): 
            return self.bot_command(msg)
        else:
            return self.relay_message(msg)
            
    def relay_message(self, msg):
        
        relay_to = self.ungarbled_jid(msg['to'])
        if relay_to is None:
            log.warn("Couln't find a prior jid for %s" % msg['to'])
            return
        
        # the sender's jid is also garbled, so replies will thread back 
        # through the relay
        relay_from = self.garbled_jid(msg['from'])
        
        relay_msg = copy.copy(msg)
        relay_msg['to'] = relay_to
        relay_msg['from'] = relay_from
        relay_msg.send()
        
    WHOAMI = "/whoami"
    def bot_command(self, msg):
        cmd = msg.get('body', '').split(' ');
        if (cmd[0] == self.WHOAMI): 
            msg.reply(str(self.garbled_jid(msg['from'])))
            msg.send()

    def garbled_jid(self, jid):
        return garbled_jid(jid, self.garble_secret, self.domain)
    
    def ungarbled_jid(self, jid):
        return ungarbled_jid(jid, self.domain)

def die(msg):
    log.error(msg)
    sys.exit(1)

def main():
    # Setup the command line arguments.
    optparser = OptionParser()

    # Output verbosity options.
    optparser.add_option('-q', '--quiet', help='set logging to ERROR',
                    action='store_const', dest='loglevel',
                    const=logging.ERROR, default=logging.INFO)
    optparser.add_option('-d', '--debug', help='set logging to DEBUG',
                    action='store_const', dest='loglevel',
                    const=logging.DEBUG, default=logging.INFO)
    optparser.add_option('-c', '--config', help='specify configuration file', 
                    dest='config_file', default='/etc/axr.conf')

    opts, args = optparser.parse_args()

    # Setup logging.
    logging.basicConfig(level=opts.loglevel,
                        format='%(levelname)-8s %(message)s')

    config = RawConfigParser()
    if not config.read(opts.config_file):
        die("Could not read config file %s", opts.config_file)

    section = "main"
    if not config.has_section(section):
        die("Configuration file %s is missing the [%s] section" % (opts.config_file, section))

    cfg = {}
    for key in ["server", "password", "jid", "secret", "domain", "port"]:
        if not config.has_option(section, key):
            die('Missing option "%s" in [%s] section of %s' % (key, section, opts.config_file))
        cfg[key] = config.get(section, key)
    for key in ["port"]: 
        try: 
            cfg[key] = int(cfg[key])
        except: 
            die("option %s in section [%s] of %s must be an integer" % (key, section, opts.config_file))
        
    xmpp = AXRComponent(**cfg)

    # Connect to the XMPP server and start processing XMPP stanzas.
    if xmpp.connect():
        xmpp.process(block=True)
        print("Done")
    else:
        print("Unable to connect.")
        
if __name__ == '__main__':
    main()