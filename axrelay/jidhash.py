import base64
import hashlib
import hmac
import logging
import sys

from Crypto import Random
from sleekxmpp.xmlstream import JID

log = logging.getLogger(__name__)


def secret_hash(name, secret):
    """
    creates a secure hash of the name using HMAC-SHA224

    The hash is encoded so that the output is a
    valid jabber id name.

    The hashed name alone is intended to provide no information
    about the original jid.

    validation of an association is trivial given the secret
    and a real jid (as the hash is itself a message authentication
    code for the real jid) which is useful to avoid storage
    poisoning.

    :return: a secure hash of the name and secret given.

    :param name: string to hash
    :param secret: secret value included in hash
    """
    h = hmac.new(secret, name, digestmod=hashlib.sha224)
    return base64.b32encode(h.digest()).replace("=", "").lower()


def hash_jid(jid, secret, domain, storage):
    """
    transforms the given jid into an anonymized version
    and stores the mapping from anonymized jid -> jid in the
    storage backend given.

    :param jid: the JID to hash
    :param secret: the secret to use during hashing. different secrets
                   yeild different hashed jids.  Prevents rainbow attacks
                   and generation of anonymous jid for a given person.
    :param domain: the domain that the anonymous jids belong to.
    :param storage: where to store the mapping between anonymous and real jid,
                    must have set and get method.

    :returns: a JID that is the anonymous alias of the JID given
    """
    if (jid is None):
        return None

    # already anonymous
    if (jid.domain == domain):
        log.debug("hash_jid: %s => %s" % (jid, jid))
        return jid
    else:
        secret_name = secret_hash(jid.full, secret)
        hashed_jid = JID('%s@%s/a' % (secret_name, domain))

        # store the hashed jid using the bare portion of the
        # jid, we don't really care about the resource.
        key = hashed_jid.bare
        storage.set(key, jid.full)

        log.debug("hash_jid: %s => %s" % (jid, hashed_jid))
        return hashed_jid


def lookup_jid(hashed_jid, storage):
    """
    look up the real jid of a previously generated
    anonymous jid in the storage backend given.

    :param hashed_jid: the hashed JID to lookup
    :param storage: the storage backend to use

    :returns: the real JID associated with the given JID or None
              if there is no known mapping.
    """
    # lookup using the bare portion of the jid only,
    # resource is ignored.
    key = hashed_jid.bare

    real_jid = storage.get(hashed_jid.bare)

    log.debug("lookup_jid: %s => %s" % (hashed_jid, real_jid))
    if real_jid is not None:
        return JID(real_jid)
    else:
        return None


def new_secret():
    """
    creates a new storage secret suitable for the hash secret
    or storage backend secret -- a base64 encoded 256 bit key
    """
    secret = Random.get_random_bytes(32)
    return base64.b64encode(secret)


def new_secret_main(argv):
    """
    prints a new storage secret to stdout
    """
    from cli import build_base_options, parse_config
    optparser = build_base_options()
    opts, args, config = parse_config(argv, optparser, require_config=False)

    print new_secret()


def hash_main(argv):
    """
    utility mainline for hashing and looking up jids.
    """

    from cli import build_base_options, parse_config
    from jidstorage import build_storage, no_storage

    optparser = build_base_options()

    optparser.add_option('-S', '--store', help='store results',
                         dest='build_storage', action="store_true", default=False)

    optparser.add_option(
        "-l", "--lookup", help='lookup real jid for hashed jid',
        dest="lookup", action="store_true", default=False)

    opts, args, config = parse_config(argv, optparser)

    if opts.build_storage == True or opts.lookup:
        storage = build_storage(config)
    else:
        storage = no_storage()

    if opts.lookup == True:
        for hjid in args:
            real_jid = lookup_jid(JID(hjid), storage)
            print "%s => %s" % (hjid, real_jid)

    else:
        section = "hash"
        if not config.has_section(section):
            sys.exit("Configuration file %s is missing the [%s] section" % (
                opts.config_file, section))

        cfg = {}
        for key in ["secret", "domain"]:
            if not config.has_option(section, key):
                sys.exit('Missing option "%s" in [%s] section of %s' %
                         (key, section, opts.config_file))
            cfg[key] = config.get(section, key)

        for real_jid in args:
            hashed_jid = hash_jid(
                JID(real_jid), cfg['secret'], cfg['domain'], storage)
            print "%s => %s" % (real_jid, hashed_jid)

if __name__ == "__main__":
    hash_main(sys.argv)
