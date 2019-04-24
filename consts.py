

import coloredlogs, logging

# Install colored logs on our logger.
log = logging.getLogger('server-chat')
coloredlogs.install(level='DEBUG', logger=log)

#server_ip = '104.131.79.111'
class ServerConsts(object):
    def __init__(self):
        self.ip = '127.0.0.1'
        self.port = 4242

    def parse_args(self):
        import sys
        if len(sys.argv) <= 1:
            pass
        elif len(sys.argv) != 3:
            print(f'Usage: python3 {sys.argv[0]} [IP PORT]')
            exit(1)
        else:
            print('hi')
            self.ip = sys.argv[1]
            self.port = int(sys.argv[2])

server = ServerConsts()
parse_args = server.parse_args
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

