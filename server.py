from user import User, UserState, InvalidUser
from os import urandom
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import traceback, enum, threading, struct, sys

from transaction import Transaction, TransactionType as tt
from consts import *
from socket import *

class TcpServerHandler(threading.Thread):
    def __init__(self, user):
        threading.Thread.__init__(self, daemon=True)

        self.__user = user

    def run(self):
        try:
            self._run_noexc()
        except ConnectionResetError:
            log.info(f'User {self.__user.cliID} has exited by connection reset.')
        except EOFError: 
            log.info(f'User {self.__user.cliID} has exited by client quit.')
        except timeout:
            log.info(f'User {self.__user.cliID} has exited by timeout.')
        except:
            log.error(traceback.format_exc())
        finally:
            if self.__user.state == UserState.CHATTING:
                end_chat(self.__user)
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
            
            try:
                handle_transaction(u, t) #d, whoosh
            except:
                log.error(traceback.format_exc())
            
            if t.type == tt.PING:
                u.send_transaction(Transaction(type=tt.PONG, message=t.message))
                continue

users = {1234: User(1234, b'password')} 
chatHistory = {}

for i in range(10):
    uid = i + 1001
    users[uid] = User(uid, bytes(f'user{uid}', 'utf8'))

def main():
    """ Entrypoint for server """
    global sock

    server.ip = '0.0.0.0'
    parse_args()

    # TODO: load users/ chat history from file.

    sock = socket(AF_INET, SOCK_DGRAM, 0)
    sock.bind((server.ip, server.port))

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
    log.debug(f'UDP(user {t.cliID}): Received {t.type.name} transaction')
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

def fetch_chat_history(userA, userB):
    global chatHistory
    
    userA = userA.cliID
    userB = userB.cliID

    if userA not in chatHistory:
        chatHistory[userA] = {}
    if userB not in chatHistory:
        chatHistory[userB] = {}

    if userB not in chatHistory[userA]:
        # Use aliasing to refer to either one
        hist = []
        chatHistory[userA][userB] = hist
        chatHistory[userB][userA] = hist
    else:
        hist = chatHistory[userA][userB]

    return hist

def find_other(user):
    for uid, u in users.items():
        if u.sessID == user.sessID and u != user:
            return u
    else:
        log.error(f'CHAT: (User {user.cliID}, Sess {user.sessID}): ' + \
                'Could not find other user')

def end_chat(user):
    other = find_other(user)

    user.state = UserState.CONNECTED
    user.sessID = 0

    if other:
        other.state = UserState.CONNECTED
        other.sessID = 0
        other.send_transaction(Transaction(type=tt.END_NOTIF,
            sessID=user.sessID))


def handle_transaction(user, trans):
    """ Handles a TCP transaction object on the server end. """
    if trans.type == tt.CHAT_REQUEST:
        if trans.cliID not in users:
            log.warning(f'User {trans.cliID} does not exist')
            user.send_transaction(Transaction(type=tt.UNREACHABLE, cliID=trans.cliID))
        elif users[trans.cliID].state != UserState.CONNECTED:
            user.send_transaction(Transaction(type=tt.UNREACHABLE, cliID=trans.cliID))
        else:
            user.init_sess()
            sessID = user.sessID
            users[trans.cliID].sessID = sessID
            user.sessID = sessID
            users[trans.cliID].state = UserState.CHATTING
            user.state = UserState.CHATTING
            user.send_transaction(Transaction(type=tt.CHAT_STARTED, 
                sessID=sessID, cliID=trans.cliID))
            users[trans.cliID].send_transaction(Transaction(type=tt.CHAT_STARTED, 
                sessID=sessID, cliID=trans.cliID))
            fetch_chat_history(user, users[trans.cliID])
    elif trans.type == tt.END_REQUEST:
        if user.sessID != trans.sessID:
            log.warning(f'CHAT: (User {trans.cliID}): Malformed session ID')
            return
        end_chat(user)
    elif trans.type == tt.CHAT:
        if user.sessID != trans.sessID:
            log.warning(f'CHAT: (User {trans.cliID}): Malformed session ID')
            return
        other = find_other(user)
        if other:
            other.send_transaction(Transaction(type=tt.CHAT, sessID=trans.sessID,
                message=trans.message, cliID=user.cliID))
            tempMessage = f"<{trans.sessID}>: {user.cliID}: {trans.message.decode('utf8')}"
            tempMessage = bytes(tempMessage, 'utf8')
            fetch_chat_history(user, other).append(tempMessage)
    elif trans.type == tt.HISTORY_REQ:
        hist = fetch_chat_history(user, users[trans.cliID])
        if hist:
            for y in hist:
                user.send_transaction(Transaction(type=tt.HISTORY_RESP,
                    cliID=user.cliID, message=y))
        else:
            user.send_transaction(Transaction(type=tt.HISTORY_RESP,
                cliID=user.cliID, message=b"No history found with this user"))

if __name__ == '__main__':
    main()


