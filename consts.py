

import coloredlogs, logging

# Install colored logs on our logger.
log = logging.getLogger('server-chat')
coloredlogs.install(level='DEBUG', logger=log)

#server_ip = '104.131.79.111'
server_ip = '127.0.0.1'
server_port = 4242
conn_timeout = 5

ping_timeout = 5
server_activity_timeout = ping_timeout + 5
client_activity_timeout = server_activity_timeout + 5

def hash1():
    import hashlib
    return hashlib.md5()

def hash2():
    import hashlib
    return hashlib.sha256()
