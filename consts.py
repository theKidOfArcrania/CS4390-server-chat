import logging

# Install colored logs on our logger.
log = logging.getLogger('server-chat')

def install_handler(logger):
    import coloredlogs

    coloredlogs.install(level='DEBUG', logger=logger)

    fh = logging.FileHandler('access.log')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(coloredlogs.DEFAULT_LOG_FORMAT))
    logger.addHandler(fh)


install_handler(log)


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
            self.ip = sys.argv[1]
            self.port = int(sys.argv[2])

server = ServerConsts()
parse_args = server.parse_args
conn_timeout = 5

ping_timeout = 55
server_activity_timeout = ping_timeout + 5
client_activity_timeout = server_activity_timeout + 5

def hash1():
    import hashlib
    return hashlib.md5()

def hash2():
    import hashlib
    return hashlib.sha256()

