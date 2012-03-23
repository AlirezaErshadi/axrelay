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

import copy
import re

from jidhash import hash_jid, lookup_jid
from jidstorage import build_storage

# enforce utf-8 default encoding
if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf8')
else:
    raw_input = input


log = logging.getLogger(__name__)


class AXRComponent(ComponentXMPP):

    """
    """
    def __init__(self, jid, password, server, port, secret, domain, storage):
        """
        :param jid:      the jid of the component itself (bot)
        :param password: the server password to attach this component
        :param server:   the address of the jabber server to attach to
        :param secret:   the secret used to garble jids
        :param storage:  the storage backend to use to store jids
        """
        ComponentXMPP.__init__(self, jid, password, server, port)
        self.hash_secret = secret
        self.domain = domain
        self.name_lookup = storage
        
        self.bot_jid = JID(jid)
        # the specific resource the bot replies from
        self.specific_bot_jid = JID(jid)
        self.specific_bot_jid.resource = 'a'
        
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
        if (msg['to'].bare == self.bot_jid.bare):
            return self.bot_command(msg)
        else:
            return self.relay_message(msg)
            
    def relay_message(self, msg):
        
        relay_to = self.lookup_jid(msg['to'])
        if relay_to is None:
            log.warn("Couln't find a prior jid for %s" % msg['to'])
            return
        
        # the sender's jid is also garbled, so replies will thread back 
        # through the relay
        relay_from = self.hash_jid(msg['from'])
        
        relay_msg = copy.copy(msg)
        relay_msg['to'] = relay_to
        relay_msg['from'] = relay_from
        relay_msg.send()
        
    WHOAMI = "/whoami"
    WHOIS  = "/whois"
    def bot_command(self, msg):
        cmd = msg.get('body', '').split(' ');
        if (cmd[0] == self.WHOAMI): 
            body = str(self.hash_jid(msg['from']).bare)
            
            msg.reply(body)
            msg['from'] = self.specific_bot_jid;
            msg.send()

    def hash_jid(self, jid):
        return hash_jid(jid, self.hash_secret, self.domain, self.name_lookup)
    
    def lookup_jid(self, jid):
        return lookup_jid(jid, self.name_lookup)

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
        sys.exit("Could not read config file %s" % opts.config_file)
    
    storage = build_storage(config)
    xmpp = build_relay(config, storage)
    
    # Connect to the XMPP server and start processing XMPP stanzas.
    if xmpp.connect():
        xmpp.process(block=True)
        print("Done")
    else:
        print("Unable to connect.")

    
def build_relay(config, storage):
    section = "relay"
    
    if not config.has_section(section):
        die("Configuration file %s is missing the [%s] section" % (opts.config_file, section))
    
    relay_cfg = {}
    for key in ["server", "password", "jid", "port"]:
        if not config.has_option(section, key):
            sys.exit('Missing option "%s" in [%s] section of %s' % (key, section, opts.config_file))
        relay_cfg[key] = config.get(section, key)
    for key in ["port"]: 
        try: 
            relay_cfg[key] = int(relay_cfg[key])
        except: 
            sys.exit("option %s in section [%s] of %s must be an integer" % (key, section, opts.config_file))

    section = "hash"
    if not config.has_section(section):
        sys.exit("Configuration file %s is missing the [%s] section" % (opts.config_file, section))

    for key in ["secret", "domain"]:
        if not config.has_option(section, key):
            sys.exit('Missing option "%s" in [%s] section of %s' % (key, section, opts.config_file))
        relay_cfg[key] = config.get(section, key)

    relay_cfg['storage'] = storage
    xmpp = AXRComponent(**relay_cfg)
    

if __name__ == '__main__':
    main()