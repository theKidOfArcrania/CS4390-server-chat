from user import User, UserState
from os import urandom
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import traceback, logging as log, enum, threading, struct

from transaction import Transaction, TransactionType as tt
from consts import * # contains server_ip, server_port
from socket import *

class TcpServerHandler(threading.Thread):
    def __init__(self, user):
        threading.Thread.__init__(self, daemon=True)

        self.__user = user

    def run(self):
        try:
            self._run_noexc()
        except:
            print(traceback.format_exc())
        finally:
            self.__user.disconnect()

    def _run_noexc(self):
        u = self.__user

        # Receive connect message
        while True:
            u.accept_conn()

            t = u.recv_transaction()
            if t.type == tt.CONNECT:
                if t.message == u.cookie:
                    log.info('Received valid CONNECT from client')
                    break
                else:
                    log.warning('Received malformed CONNECT from client')
            else:
                log.warning(f'Received {t.type.name} instead of CONNECT')
        
        # Now loop for each transaction
        u.connected()
        while True:
            t = u.recv_transaction()
            log.info('Received {t.type.name} transaction')
            try:
                handle_transaction(u, t) #d, whoosh
            except:
                print(traceback.format_exc())

users = {123: User(123, b'muybankaccount'), 1234: User(1234, b'password')}

log.root.setLevel(log.DEBUG)

def main():
    """ Entrypoint for server """
    global sock

    # TODO: load users/ chat history from file.

    sock = socket(AF_INET, SOCK_DGRAM, 0)
    sock.bind((server_ip, server_port))

    while True:
        data, addr = sock.recvfrom(1024)
        try:
            handle_udp(data, addr)
        except:
           print(traceback.format_exc()) 

def send_udp(trans, addr):
    sock.sendto(trans.to_bytes(), addr)

def p32(num):
    return struct.pack('<I', num)

def u32(data):
    return struct.unpack('<I', data)[0]

def handle_udp(data, addr):
    """ Handles a UDP request """

    if len(data) < 4:
        log.error('Datagram is too small')
        return
    leng = u32(data[:4])
    if len(data) < leng:
        log.error('Malformed datagram.')
        return
    elif len(data) > leng:
        log.warning('Extraneous data at end of packet')

    t = Transaction.from_bytes(data[:leng])
    if t.type == tt.HELLO:
        log.info(f'Received HELLO from ID {t.cliID}')
        if t.cliID not in users:
            #TODO: maybe create invalid user, and go on "as normal", so that
            # we cannot figure out that this is invalid user ID
            log.error('User id {} does not exist'.format(t.cliID))
            return
        u = users[t.cliID]
        if u.state > UserState.CONNECTING:
            log.warning('Attempt HELLO on connected user!')
            return
        elif u.state != UserState.OFFLINE:
            log.warning('Previous session is silently discarded!')
            u.disconnect()

        u.init_sess()
        send_udp(Transaction(type=tt.CHALLENGE, message=p32(u.sessID)), addr)
        u.state = UserState.AUTH
    elif t.type == tt.RESPONSE:
        log.info(f'Received RESPONSE from ID {t.cliID}')
        if t.cliID not in users:
            log.error('User id {} does not exist'.format(t.cliID))
            return
        u = users[t.cliID]
        if u.state != UserState.AUTH:
            log.error('Expected user {} to be in AUTH, but is in {}.'.format( \
                    u.cliID, u.state.name))
            return

        if t.message != u.get_auth():
            log.warning('Invalid authentication for user {}.'.format(u.cliID))
            u.state = UserState.OFFLINE
            send_udp(Transaction(type=tt.AUTH_FAIL), addr)
        else:
            trans = u.init_connection()
            hdlr = TcpServerHandler(u)
            hdlr.start()

            send_udp(trans, addr)
            u.hdlr = hdlr
            u.state = UserState.CONNECTING
    else:
        log.error(f'Invalid message type: "{t.type.name}"')

    

def handle_transaction(user, trans):
    """ Handles a TCP transaction object on the server end. """
    #TODO
    pass
    # use recv_transaction to receive a Transaction object

if __name__ == '__main__':
    main()
