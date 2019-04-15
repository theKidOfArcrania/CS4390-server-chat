from user import User, UserState, InvalidUser
from os import urandom
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import traceback, enum, threading, struct

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
        except EOFError: 
            log.info(f'User {self.__user.cliID} has exited by client quit.')
        except timeout:
            log.info(f'User {self.__user.cliID} has exited by timeout.')
        except:
            log.error(traceback.format_exc())
        finally:
            self.__user.disconnect()

    def _run_noexc(self):
        u = self.__user

        # Receive connect message
        while True:
            u.accept_conn()

            try:
                t = u.recv_transaction()
                if t.type == tt.CONNECT:
                    if t.message == u.cookie:
                        log.info(f'CONNECT(user {u.cliID}): validated!')
                        break
                    else:
                        log.warning(f'CONNECT(user {u.cliID}): Invalid cookie!')
                else:
                    log.warning(f'CONNECT(user {u.cliID}): Received {t.type.name}'+
                            ' instead of CONNECT')
            except:
                log.error(traceback.format_exc())
        
        # Now loop for each transaction
        u.connected()
        while True:
            t = u.recv_transaction()
            log.debug(f'TCP(user {u.cliID}): Received {t.type.name} transaction')
            
            if t.type == tt.PING:
                u.send_transaction(Transaction(type=tt.PONG, message=t.message))
                continue

            try:
                handle_transaction(u, t) #d, whoosh
            except:
                log.error(traceback.format_exc())

users = {123: User(123, b'muybankaccount'), 1234: User(1234, b'password')}

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
           log.error(traceback.format_exc()) 

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
    log.debug(f'UCP(user {t.cliID}): Received {t.type.name} transaction')
    if t.type == tt.HELLO:
        if t.cliID not in users:
            # Create "dummy" invalid user, so that client does not differentiate
            # between bad user ID and bad password
            log.warning('HELLO: User id {} does not exist'.format(t.cliID))
            users[t.cliID] = InvalidUser(t.cliID)

        u = users[t.cliID]
        if u.state > UserState.CONNECTING:
            log.warning('HELLO: Attempt HELLO on connected user!')
            return
        elif u.state != UserState.OFFLINE:
            log.warning('HELLO: Previous session is silently discarded!')
            u.disconnect()

        u.init_sess()
        send_udp(Transaction(type=tt.CHALLENGE, message=p32(u.sessID)), addr)
        u.state = UserState.AUTH
    elif t.type == tt.RESPONSE:
        if t.cliID not in users:
            log.warning(f'RESPONSE: User id {t.cliID} does not exist')
            return
        u = users[t.cliID]
        if u.state != UserState.AUTH:
            log.warning(f'RESPONSE: Expected user {u.cliID} to be in AUTH, ' +
                    f'but is in {u.state.name}.')
            return

        if t.message != u.get_auth():
            log.warning(f'RESPONSE: Invalid authentication for user {u.cliID}.')
            u.state = UserState.OFFLINE
            send_udp(Transaction(type=tt.AUTH_FAIL), addr)
            if type(u) is InvalidUser:
                del users[t.cliID]
        else:
            trans = u.init_connection()
            hdlr = TcpServerHandler(u)
            hdlr.start()

            send_udp(trans, addr)
            u.hdlr = hdlr
            u.state = UserState.CONNECTING

    else:
        log.error(f'UDP: Invalid message type: "{t.type.name}"')

    

def handle_transaction(user, trans):
    """ Handles a TCP transaction object on the server end. """
    #TODO
    pass
    # use recv_transaction to receive a Transaction object

if __name__ == '__main__':
    main()
