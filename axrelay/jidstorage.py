from Crypto import Random
from Crypto.Cipher import AES
import base64
import hashlib
import hmac
import logging
import struct
import pylibmc as memcache
from jidhash import secret_hash

"""
This module defines a number of storage backends for the 
anonymous jid -> real jid mapping. 

Currently the interface for a storage backend is: 

* set(key, val)
* get(key)  : returns None if key is not present
* delete(key)
"""


log = logging.getLogger(__name__)

MEMCACHE_SECTION = "memcache"
LOCAL_SECTION = "local_storage"

class NoStorage(object):
    """
    this is a storage backend that does nothing
    """
    
    def get(self, key):
        return None
        
    def set(self, key, value):
        pass
        
    def delete(self, key):
        pass

class LocalStorage(dict):
    """
    this is a storage backend that 
    stores things in a local 
    in-memory dict.
    """
    
    def set(self, key, value):
        self[key] = value

    def delete(self, key):
        del self[key]

class MemcacheStorage(object):
    """
    this is a storage backend that stores values in a 
    distributed memcache cluster.
    """
    
    def __init__(self, master_client):
        """
        :param master_client: this memcache client configuration will be cloned
            for pooled connections
        """
        self.pool = memcache.ThreadMappedPool(master_client)
        
    def set(self, key, value):
        with self.pool.reserve() as mc:
            return mc.set(self._pack_key(key), self._pack_val(value))
        
    def get(self, key):
        with self.pool.reserve() as mc:
            val = mc.get(self._pack_key(key))
            if val is None:
                return None
            return self._unpack_val(val)
    
    def delete(self, key):
        with self.pool.reserve() as mc:
            mc.delete(self._pack_key(key))
    
    def _pack_key(self, key):
        if key is None:
            return None
        return key.encode('utf-8')
        
    def _pack_val(self, val):
        if val is None: 
            return None
        return base64.b64encode(val)
        
    def _unpack_val(self, val):
        if val is None:
            return None 
        return base64.b64decode(val)
        
class NonEnumerableStorage(object):
    """
    This storage wraps a storage but takes steps to make the 
    keys and values used provide as little extra information
    as possible if comprimised.

    The idea is to make it possible to do the things
    the service must do:
    
        * look up the real jid of a known anonymous jid
    
        * validate the association between a known 
          anonymous jid and a known real jid.

    And hard to do much else, especially:
      
        * enumerate anonymous jids

        * enumerate real jids

    To accomplish this:
        
        * keys are secret_hashed in the same fashion 
          as the anonymized jid names.  (Thus they are 
          not enumerable by looking at the keys in the
          store)

        * values are encrypted using a key based on the 
          secret and the anonymous jid. (Thus they are
          not enumerable knowing only the values in the 
          store and the secret.) Specifically they are 
          combined using HMAC-SHA256 of the secret and 
          lookup-key
    
    It is worth restating that if the storage is accessible and
    the key is known, any particular real jid can be comprimised
    if the corresponding anonymous jid is known by other means. 
    This encryption mainly exists to thwart enumeration by 
    access to the store and secret -- to fully comprimise the 
    store, anonymous jids must also be enumerated by external
    means.
    """
    
    def __init__(self, storage, secret):
        """
        create an NonEnumerableStorage from another store
        
        :param storage: the actual storage to store the data in
        :param secret: a secret value as generated by :meth new_storage_secret:
        """
        self.storage = storage
        self.secret = base64.b64decode(secret)

        
    def set(self, key, value):
        return self.storage.set(self._hash_key(key), self._encrypt(key, value))

    def get(self, key):
        val = self.storage.get(self._hash_key(key))
        if val is None:
            return None
        return self._decrypt(key, val)

    def delete(self, key):
        return self.storage.delete(self._hash_key(key))
            
    def _hash_key(self, key):
        return secret_hash(key, self.secret)
        
    def _encrypt(self, key, val):
        # the encrypted value is the concatenation of the 
        # initialization vector and the ciphertext
        iv = new_iv()
        c = self._create_cipher(key, iv).encrypt(self._pad(val))
        return iv + c

    def _decrypt(self, key, val):
        # the initialization vector is extracted as the first 
        # AES.block_size bytes of the value.
        iv = val[0:AES.block_size]
        c = val[AES.block_size:]
        return self._unpad(self._create_cipher(key, iv).decrypt(c))

    def _pad(self, val):
        # PKCS7
        pad_bytes = AES.block_size - (len(val) % AES.block_size)
        padding = struct.pack('b', pad_bytes) * pad_bytes
        return val + padding
        
    def _unpad(self, val):
        # PKCS7
        pad_bytes = struct.unpack('b', val[-1])[0]
        return val[:-pad_bytes]
    
    def _create_cipher(self, salt, iv):
        aes_key = combine_key(self.secret, salt)
        return AES.new(aes_key, AES.MODE_CBC, iv)

def combine_key(secret, salt):
    """
    folds together a secret and a salt value into 
    a new aes key.  The secret and salt are combined
    using HMAC-SHA256.
    """
    # combine salt and secret using hmac + truncation
    h = hmac.new(secret, salt, digestmod=hashlib.sha256)
    return h.digest()

def new_iv():
    return Random.get_random_bytes(AES.block_size)

    
def build_storage(config, opts):
    """
    builds the storage backend configured in the 
    ConfigParser object given. 

    :param config: ConfigParser object containing configuration info
    """

    if config.has_section(MEMCACHE_SECTION):
        section = MEMCACHE_SECTION
        storage = build_memcache(config, opts)
        
    elif config.has_section(LOCAL_SECTION):
        section = LOCAL_SECTION
        storage = build_local(config, opts)
    
    else:
        log.warn("No storage backend configured. running in local memory only.")
        section = None
        storage = LocalStorage()
    
    if section is not None and config.has_option(section, "encrypt"):
        storage = NonEnumerableStorage(storage, config.get(section, "encrypt"))
        
    return storage

def no_storage():
    """
    creates a dummy storage backend that does nothing
    """
    return NoStorage()


def build_local(config):
    return LocalStorage()

def build_memcache(config, opts):
    """
    creates a memcache based storage backend 
    depending on the configuration given. 

    options mimic those of pylibmc Client 
    constructor (with behaviors alongside main 
    options)
    """
    cfg = {
        'behaviors': {},
    }

    section = MEMCACHE_SECTION
    if not config.has_option(section, "servers"):
        die('Missing option "%s" in [%s] section of %s' % (key, section, opts.config_file))

    # list config
    cfg['servers'] = [x.strip() for x in config.get(section, "servers").split(",") if x.strip()]

    # boolean config
    if config.has_option(section, "binary") and asbool(config.getboolean(section, "binary")) == True:
        cfg['binary'] = True

    # string config
    for key in ["username", "password"]:
        if config.has_option(section, key): 
            cfg[key] = config.get(section, key)

    # string behaviors
    for key in ["hash", "distribution", "ketama_hash"]: 
        if config.has_option(section, key): 
            cfg['behaviors'][key] = config.get(section, key)

    # boolean behaviors
    for key in ["ketama", "ketama_weighted", "buffer_requests", "cache_lookups", 
                "no_block", "tcp_nodelay", "cas", "verify_keys"]: 
        if config.has_option(section, key):
            cfg['behaviors'][key] = config.getboolean(section, key)

    # integer behaviors
    for key in ["connect_timeout", "receive_timeout", "send_timeout",
                "num_replicas", "remove_failed"]:
        if config.has_option(section, key):
            cfg['behaviors'][key] = int(config.getint(section, key))

    mc = memcache.Client(**cfg)
    storage = MemcacheStorage(mc)

    return storage