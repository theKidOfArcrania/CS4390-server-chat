from consts import * 
from socket import *
from transaction import *
import struct, traceback, logging as log, enum, sys, threading
import user 
from user import UserState
import threading
import time
import sys

tt = TransactionType

resp_cond = threading.Condition()
hist_cnt = 0

class Pinger(object):
    def __init__(self, user):
        self.__user = user
        self.__timer = None
        self.__cancelling = False

    def __do_ping(self):
        if self.__cancelling:
            return;
        try:
            self.__user.send_transaction(Transaction(type=tt.PING, message=b'1234567890'))
            self.__timer = threading.Timer(ping_timeout, self.__do_ping)
            self.__timer.daemon = True
            self.__timer.start()
        except:
            pass

    def start(self):
        if self.__timer:
            return
        self.__cancelling = False
        self.__do_ping()

    def stop(self):
        self.__cancelling = True
        if self.__timer:
            self.__timer.cancel()
            self.__timer = None

def p32(num):
    return struct.pack('<I', num)

def u32(data):
    return struct.unpack('<I', data)[0]

def main():
    parse_args()

    while True:
        client_main()

prev_line = None
def client_main():
    global prev_line

    # "Log on" first
    while True:
        if prev_line != None:
            line = prev_line
            prev_line = None
        else:
            menu_prompt(True)
            line = input()
        if line.lower() == 'log on':
            break
        print('Please type log on')
    
    print("""
/******************************\\
|                              |
|   Welcome to LetsChat 0.9    |
|                              |
\\******************************/
There are a few temp user accounts that you can use:
  ID:    ####
  Pass:  user####

Where you replace #### with number between 1001 and 1010.
""")

    sock = socket(AF_INET, SOCK_DGRAM)
    sock.settimeout(conn_timeout)

    # Connect to server
    code = 0
    while code != 1: 
        u = user.User(*prompt_creds())
        send_udp(sock, Transaction(type = tt.HELLO, cliID = u.cliID))
        try:
            while True:
                data, _ = sock.recvfrom(1024)
                code = handle_udp(sock, u, data)
                if code != 0:
                    break
        except timeout:
            print('Received server timeout or user is already logged on.')

    sock.close()

    # Initialize pinger
    p = Pinger(u)
    u.pinger = p

    # Now receive transactions from TCP connection
    print('Connected to server!\n\nType "help/Help" to see available commands.')
    
    t1 = threading.Thread(target=listen, daemon=True, args=(u,))
    t1.start()
    u.sessID = 0
    u.state = UserState.CONNECTED

    sys.stdout.write('> ')
    sys.stdout.flush()
    while True:
        if u.state == UserState.CHATTING:
            chat_prompt()
        elif u.state == UserState.OFFLINE:
            break
        else:
            menu_prompt()
        
        inp = input()

        if u.state == UserState.OFFLINE:
            prev_line = inp
            p.stop()
            break
        elif u.state == UserState.CHATTING:
            clear_upline()
            chatting(u, inp)
        else:
            menu(u, inp)
            time.sleep(.05)

def wait_resp(u):
    with resp_cond:
        if not resp_cond.wait(5):
            u.disconnect()
            print('Server timeout!')


def menu(u, userInput):
    global hist_cnt

    userInput = userInput.lower()
    if userInput == 'log off' or userInput == 'logoff':
        u.disconnect()
        print('Bye...')
        return
    
    try:
        args = userInput.split()
        cmd = args[0]
        cid = int(args[1])
    except:
        if userInput == 'help':
            print('''Available commands are:
chat [userID#]
history [userID#]
logoff''')
        else:
            print ("Please enter a valid command or type help")
        return

    if cmd == 'chat':
        if cid == u.cliID:
            print('Cannot chat with self!')
            return
        u.send_transaction(Transaction(type=tt.CHAT_REQUEST, cliID=cid))
        wait_resp(u)
    elif cmd == "history":
        hist_cnt = 0
        u.send_transaction(Transaction(type=tt.HISTORY_REQ, cliID=cid))
        wait_resp(u)
        if u.state != UserState.OFFLINE and hist_cnt == 0:
            print('No chat history from this user...')
    else:
        print ("Please enter a valid command or type help")


def chatting(u, userInput):
    msg = bytes(userInput, 'utf8')

    if userInput.lower() == "end chat":
        u.send_transaction(Transaction(type=tt.END_REQUEST, sessID=u.sessID))
        print('Chat Ended')
        u.pinger.stop()
        u.state = UserState.CONNECTED
        menu_prompt()
    else:
        trans = Transaction(type=tt.CHAT, message=msg, cliID=u.cliID, 
                sessID=u.sessID)
        u.send_transaction(trans)
        print_chat(trans)

def getpass(prompt='Password: '):
    import termios
    if not sys.stdin.isatty():
        print('Not running on a terminal... bye!')
        exit(1)

    ttyin = sys.stdin
    ttyout = sys.stdout if sys.stdout.isatty() else ttyin

    fd = ttyin.fileno()
    old = termios.tcgetattr(fd)
    new = old[::]
    new[3] = new[3] & ~(termios.ECHO | termios.ICANON)  # lflags
    try:
        termios.tcsetattr(fd, termios.TCSADRAIN, new)
        
        ttyout.write(prompt)
        ttyout.flush()
        passwd = b''
        while True:
            c = ttyin.buffer.read(1)
            if not c:
                raise EOFError()
            elif c == b'\n':
                break
            elif c == b'\x7f': # Backspace
                if len(passwd) > 0:
                    passwd = passwd[:-1]
                    ttyout.write('\x1b[D\x1b[K')
                    ttyout.flush()

            else:
                passwd += c
                ttyout.write('*')
                ttyout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        print('')
    return passwd

def prompt_creds():
    while True:
        try:
            userID = int(input('Please enter your user ID: '))
            break
        except KeyboardInterrupt:
            quit()
        except:
            print('Not a valid user id...')
            pass

    pwd = getpass()
    return userID, pwd
    
def clear_upline():
    sys.stdout.write('\x1B[1A')
    clear_line()

def clear_line():
    sys.stdout.write('\r\x1b[2K')
    sys.stdout.flush()

def menu_prompt(top=False):
    clear_line()
    sys.stdout.write('> ' if top else '~ ')
    sys.stdout.flush()

def chat_prompt():
    clear_line()
    sys.stdout.write('chat> ')
    sys.stdout.flush()

def print_chat(trans):
    assert trans.type == tt.CHAT
    clear_line()
    print(f'{trans.cliID}: {trans.message.decode("utf8")}')

def send_udp(sock, trans):
    sock.sendto(trans.to_bytes(), (server.ip, server.port))

def handle_tcp(u, transaction):
    global hist_cnt

    if transaction.type == tt.UNREACHABLE:
        print('User Unavailable')
        with resp_cond:
            resp_cond.notify_all()
    elif transaction.type == tt.CHAT_STARTED:
        u.pinger.start()
        clear_line()
        print(f'Chat Started!\nSession ID: {transaction.sessID}')
        chat_prompt()
        u.state = UserState.CHATTING
        u.sessID = transaction.sessID
        with resp_cond:
            resp_cond.notify_all()
    elif transaction.type == tt.END_NOTIF:
        u.pinger.stop()
        clear_line()
        u.state = UserState.CONNECTED

        print('Chat Ended')
        menu_prompt()
    elif transaction.type == tt.CHAT:
        print_chat(transaction)
        chat_prompt()
    elif transaction.type == tt.HISTORY_RESP:
        t = transaction
        if t.cliID == 0:
            with resp_cond:
                resp_cond.notify_all()
        else:
            hist_cnt += 1
            print(f'<{t.sessID}> <from: {t.cliID}>: {t.message.decode("utf8")}')

def handle_udp(sock, u, data):
    leng = u32(data[:4])
    if len(data) < 4:
        log.error('Datagram is too small.')
        return 0
    if len(data) < leng:
        log.error('Malformed datagram.')
        return 0
    elif len(data) > leng:
        log.warning('Extraneous data at end of packet')

    t = Transaction.from_bytes(data[:leng])
    if t.type == tt.CHALLENGE:
        # do i need to check anything?
        u.sessID = u32(t.message)
        send_udp(sock, Transaction(type = tt.RESPONSE, cliID=u.cliID, message = u.get_auth()))
    elif t.type == tt.AUTH_SUCCESS:
        u.init_connection(t)
        return 1 # finished with udp
    elif t.type == tt. AUTH_FAIL:
        print("Authentication failed\n")
        return -1

    return 0

def listen(u):
    while True:
        try:
            trans = u.recv_transaction()
            if u.state == UserState.OFFLINE:
                break
            handle_tcp(u, trans)
        except:
            if u.state == UserState.OFFLINE:
                break
            clear_line()
            u.disconnect()
            print('Received server timeout.')
            menu_prompt(True)
            break

if __name__ == '__main__':
    main()
