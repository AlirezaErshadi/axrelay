#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
"""

import sys
import logging
import getpass
from optparse import OptionParser

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
        garbled = '%s@%s' % (garble(jid.full, secret), domain)
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

    def __init__(self, jid, secret, server, port, garble_secret, domain):
        ComponentXMPP.__init__(self, jid, secret, server, port)
        self.garble_secret = garble_secret
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

def main():
    # Setup the command line arguments.
    optp = OptionParser()

    # Output verbosity options.
    optp.add_option('-q', '--quiet', help='set logging to ERROR',
                    action='store_const', dest='loglevel',
                    const=logging.ERROR, default=logging.INFO)
    optp.add_option('-d', '--debug', help='set logging to DEBUG',
                    action='store_const', dest='loglevel',
                    const=logging.DEBUG, default=logging.INFO)
    optp.add_option('-v', '--verbose', help='set logging to COMM',
                    action='store_const', dest='loglevel',
                    const=5, default=logging.INFO)

    # JID and password options.
    optp.add_option("-j", "--jid", dest="jid",
                    help="JID to use")
    optp.add_option("-p", "--password", dest="password",
                    help="password to use")
    optp.add_option("-s", "--server", dest="server",
                    help="server to connect to")
    optp.add_option("-P", "--port", dest="port",
                    help="port to connect to")

    opts, args = optp.parse_args()

    if opts.jid is None:
        opts.jid = raw_input("Component JID: ")
    if opts.password is None:
        opts.password = getpass.getpass("Password: ")
    if opts.server is None:
        opts.server = raw_input("Server: ")
    if opts.port is None:
        opts.port = int(raw_input("Port: "))

    # Setup logging.
    logging.basicConfig(level=opts.loglevel,
                        format='%(levelname)-8s %(message)s')

    xmpp = AXRComponent(opts.jid, opts.password, opts.server, opts.port, 'b00z', 'axr.localhost')
    # xmpp.registerPlugin('xep_0030') # Service Discovery
    # xmpp.registerPlugin('xep_0004') # Data Forms
    # xmpp.registerPlugin('xep_0060') # PubSub
    # xmpp.registerPlugin('xep_0199') # XMPP Ping

    # Connect to the XMPP server and start processing XMPP stanzas.
    if xmpp.connect():
        xmpp.process(block=True)
        print("Done")
    else:
        print("Unable to connect.")
        
if __name__ == '__main__':
    main()