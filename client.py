from consts import * 
from socket import *
from transaction import *
import struct, traceback, logging as log, enum, sys, threading
import user 
from user import UserState
import threading
import time

tt = TransactionType

class Pinger(object):
    def __init__(self, user):
        self.__user = user
        self.__timer = None

    def __do_ping(self):
        try:
            self.__timer = None
            self.__user.send_transaction(Transaction(type=tt.PING, message=b'1234567890'))
            self.start()
        except:
            pass

    def start(self):
        if self.__timer:
            return
        self.__timer = threading.Timer(ping_timeout, self.__do_ping)
        self.__timer.daemon = True
        self.__timer.start()

    def stop(self):
        if self.__timer:
            self.__timer.cancel()
            self.__timer = None

def p32(num):
    return struct.pack('<I', num)

def u32(data):
    return struct.unpack('<I', data)[0]

def main():
    global sock
    global u

    parse_args()

    sock = socket(AF_INET, SOCK_DGRAM)
    sock.settimeout(conn_timeout)

    
    print("""
/******************************\\
|                              |
|   Welcome to LetsChat 0.9    |
|                              |
\\******************************/
""")

    # Connect to server
    code = 0
    while code != 1: 
        u = user.User(*prompt_creds())
        send_udp(Transaction(type = tt.HELLO, cliID = u.cliID))
        try:
            while True:
                data, _ = sock.recvfrom(1024)
                code = handle_udp(data)
                if code != 0:
                    break
        except timeout:
            print('Received timeout on server!\n')


    # Initialize pinger
    p = Pinger(u)
    p.start()

    # Now receive transactions from TCP connection
    print('Connected to server!\n\nType "help/Help" to see available commands.')
    
    t1 = threading.Thread(target=listen, daemon=True)
    t1.start()
    clientSessionID = 0

    sys.stdout.write('> ')
    sys.stdout.flush()
    while True:
        if u.state == UserState.CHATTING:
            chat_prompt()
        else:
            menu_prompt()

        inp = input()

        if u.state == UserState.CHATTING:
            clear_upline()
            chatting(inp)
            time.sleep(.05)
        else:
            menu(inp)
            time.sleep(.05)
            sys.stdout.write('> ')
            sys.stdout.flush()
        #p.stop()

def menu(userInput):
    global u
    
    try:        
        a,b = userInput.split()
        b = int(b)
        if a == 'Chat' or a == "chat":
            if b == u.cliID:
                print('Cannot chat with self!')
                return
            u.send_transaction(Transaction(type=tt.CHAT_REQUEST, cliID=int(b)))
        elif a == "History" or a == "history":
            u.send_transaction(Transaction(type=tt.HISTORY_REQ, cliID=int(b)))
        else:
            print ("Please enter a valid command or type help")
    except:
        try:
            if userInput == 'help' or userInput == 'Help':
                print ("Available commands are:\nChat/chat [userID#]\nHistory/history [userID#]\n")
            else:
                print ("Please enter a valid command or type help")
        except:
            print ("Please enter a valid command or type help")

def chatting(userInput):
    global u
    msg = bytes(userInput, 'utf8')

    if userInput == "End Chat":
        u.send_transaction(Transaction(type=tt.END_REQUEST, sessID=clientSessionID))
    else:
        trans = Transaction(type=tt.CHAT, message=msg, cliID=u.cliID, 
                sessID=clientSessionID)
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

def menu_prompt():
    clear_line()
    sys.stdout.write('> ')
    sys.stdout.flush()

def chat_prompt():
    clear_line()
    sys.stdout.write('chat> ')
    sys.stdout.flush()

def print_chat(trans):
    assert trans.type == tt.CHAT
    clear_line()
    print(f'{trans.cliID}: {trans.message.decode("utf8")}')

def send_udp(trans):
    sock.sendto(trans.to_bytes(), (server.ip, server.port))

def handle_tcp(transaction):
    global u, chatID, clientSessionID
    
    if transaction.type == tt.UNREACHABLE:
        print('User Unavailable')
    elif transaction.type == tt.CHAT_STARTED:
        clear_line()
        print(f'Chat Started!\nSession ID: {transaction.sessID}')
        chat_prompt()
        u.state = UserState.CHATTING
        clientSessionID = transaction.sessID
    elif transaction.type == tt.END_NOTIF:
        clear_line()
        print('Chat Ended')
        u.state = UserState.CONNECTED
        menu_prompt()
    elif transaction.type == tt.CHAT:
        print_chat(transaction)
        chat_prompt()
    elif transaction.type == tt.HISTORY_RESP:
        print(transaction.message.decode("utf8"))

    pass

def handle_udp(data):
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
        send_udp(Transaction(type = tt.RESPONSE, cliID=u.cliID, message = u.get_auth()))
    elif t.type == tt.AUTH_SUCCESS:
        u.init_connection(t)
        return 1 # finished with udp
    elif t.type == tt. AUTH_FAIL:
        print("Authentication failed\n")
        return -1

    return 0

def listen():
    global u

    while True:
        try:
            trans = u.recv_transaction()
            #print(f'Received {trans.type.name} transaction: {trans.message}')
            handle_tcp(trans)
        except timeout:
            print('Received timeout on server!\n')

if __name__ == '__main__':
    main()
