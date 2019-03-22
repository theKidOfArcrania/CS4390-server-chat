from transaction import *
from consts import * # contains server_ip, server_port
from socket import *
from os import urandom
import struct, traceback, logging as log, enum

tt = TransactionType

def p32(num):
    return struct.pack('<I', num)

def u32(data):
    return struct.unpack('<I', data)[0]

class UserState(enum.IntEnum):
    OFFLINE, AUTH, CONNECTING, CHATTING = range(4)

class User:
    def __init__(self, cliID, secretKey):
        """ Initializes user """
        self.cliID = cliID
        self.secretKey = secretKey
        self.sessID = 0
        self.state = UserState.OFFLINE

    def disconnect(self):
        # TODO

    def get_auth(self):
        h_auth = hash1()
        h_auth.update(p32(u.sessID) + self.secretKey)
        return h_auth.digest()

    def get_key():
        h_key = hash2()
        h_key.update(p32(u.sessID) + self.secretKey)
        return h_key.digest()


    def init_sess(self):
        """ 
        Initializes a new session ID. It also silently discards previous session
        information.

        This session ID is different from the session ID used to identify a
        particular chat session. (That is computed from the hash of both
        client's session IDs).
        """

        self.sessID = u32(urandom(4))


users = {}

def main():
    """ Entrypoint for server """
    global sock

    sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
    sock.bind((server_ip, server_port))

    while True:
        data, addr = sock.recvfrom(1024)
        try:
            handle_udp(data, addr)
        except:
           print(traceback.format_exc()) 

def send_udp(trans, addr):
    sock.sendto(trans.to_bytes(), addr)

def handle_udp(data, addr):
    """ Handles a UDP request """

    if len(data) < 4:
        log.error('Datagram is too small')
        return
    leng = struct.unpack('<I', data[:4])
    if len(data) < leng:
        log.error('Malformed datagram.')
        return
    elif len(data) > leng:
        log.warning('Extraneous data at end of packet')

    t = Transaction.from_bytes(data[:leng])
    if t.type == tt.HELLO:
        if t.cliID not in users:
            log.error('User id {} does not exist'.format(t.cliID))
            return
        u = users[t.cliID]
        if u.state != UserState.OFFLINE:
            log.warning('Previous session is silently discarded!')
            u.disconnect()
            return

        u.init_sess()
        send_udp(Transaction(type=tt.CHALLENGE, data=p32(u.sessID)))
        u.state = UserState.AUTH
    elif t.type == tt.REPSONSE:
        if u.state != UserState.AUTH:
            log.error('Expected user {} to be in AUTH, but is in {}.'.format( \
                    u.cliID, u.state.name))
            return

        if t.message != u.get_auth():
            log.warning('Invalid authentication for user {}.'.format(u.cliID))
            u.state = UserState.OFFLINE
            send_udp(Transaction(type=tt.AUTH_FAIL))
        else:
            data = # TODO
            send_udp(Transaction(type=tt.AUTH_SUCCESS, message=data))
            u.state = UserState.CONNECTING
            # Listen for TCP conns
        
        
        

        
        


