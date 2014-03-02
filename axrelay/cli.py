import sys
import logging
from logging.config import dictConfig as configure_logging

# enforce utf-8 default encoding
if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf8')

DEFAULT_CONFIG_FILE = "/usr/local/etc/axrelay.conf"


log = logging.getLogger(__name__)


def build_base_options():
    from optparse import OptionParser

    # Setup the basic command line arguments.
    optparser = OptionParser()

    optparser.add_option('-c', '--config', help='specify configuration file',
                         dest='config_file', default=DEFAULT_CONFIG_FILE)

    optparser.add_option('-q', '--quiet', help='set logging to ERROR',
                         action='store_const', dest='loglevel',
                         const=logging.ERROR, default=logging.INFO)

    optparser.add_option('-d', '--debug', help='set logging to DEBUG',
                         action='store_const', dest='loglevel',
                         const=logging.DEBUG, default=logging.INFO)

    optparser.add_option('--log-file', help='log to file',
                         dest='logfile', metavar="FILE")

    return optparser


def parse_config(argv, optparser, require_config=True):
    from ConfigParser import RawConfigParser

    opts, args = optparser.parse_args(argv)

    # Setup logging.
    logging_opts = {
        'version': 1,
        'disable_existing_loggers': False,

        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'default',
            },
        },

        'root': {
            'level': opts.loglevel,
            'handlers': ['console', ]
        },

        'formatters': {
            'default': {
                'format': '%(asctime)s %(levelname)-8s %(message)s',
            }
        }
    }
    if (opts.logfile is not None):
        logging_opts['handlers']['file'] = {
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': opts.logfile,
            'formatter': 'default'
        }
        logging_opts['root']['handlers'].append('file')

    configure_logging(logging_opts)

    config = RawConfigParser()
    if not config.read(opts.config_file) and require_config:
        msg = "Could not read config file %s" % opts.config_file
        log.error(msg)
        sys.exit(msg)

    return opts, args, config


def main():
    from relay import relay_main
    from jidhash import hash_main, new_secret_main

    COMMANDS = {
        "run": (relay_main, "start the relay"),
        "hash": (hash_main, "perform a jid hash or hash lookup"),
        "secret": (new_secret_main, "create a random secret"),
    }

    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print "usage: %s [command] <options>" % sys.argv[0]
        print "\nCommands:"
        for cmd, info in COMMANDS.items():
            print "  %s : %s" % (cmd.ljust(10), info[1])
        print "\nfor more info, run %s [command] --help" % sys.argv[0]
        sys.exit(1)

    return COMMANDS[sys.argv[1]][0](sys.argv[2:])
