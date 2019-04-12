from transaction import *
from consts import * # contains server_ip, server_port
from socket import *
from user import User, UserState
import traceback, logging as log, enum

tt = TransactionType

def p32(num):
    return struct.pack('<I', num)

def u32(data):
    return struct.unpack('<I', data)[0]

users = {1234: User(1234, b'password')}

log.root.setLevel(log.DEBUG)

def main():
    """ Entrypoint for server """
    global sock

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
            log.error('User id {} does not exist'.format(t.cliID))
            return
        u = users[t.cliID]
        if u.state != UserState.OFFLINE:
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
            data = b'blah' # TODO
            send_udp(Transaction(type=tt.AUTH_SUCCESS, message=data), addr)
            u.state = UserState.CONNECTING
            # Listen for TCP conns
    else:
        log.error(f'Invalid message type')

def recv_transaction(sock):
    first = u32(sock.recvn(4))
    t = Transaction.from_bytes(first + sock.recvn(u32(first) - 4))
    return t
    

def handle_tcp(sock, user):
    pass
    # use recv_transaction to receive a Transaction object

if __name__ == '__main__':
    main()
