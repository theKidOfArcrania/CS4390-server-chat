from consts import * # server_ip, server_port
from socket import *
from transaction import *
import struct, traceback, logging as log, enum, sys, threading
import user

tt = TransactionType

class Pinger(object):
    def __init__(self, user):
        self.__user = user
        self.__timer = None

    def __do_ping(self):
        self.__timer = None
        self.start()
        self.__user.send_transaction(Transaction(type=tt.PING, message=b'1234567890'))

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
    print('Connected to server!\n')
    try:
        while True:
            trans = u.recv_transaction()
            print(f'Received {trans.type.name} transaction: {trans.message}')
            handle_tcp(trans)
    finally:
        p.stop()


def getpass(prompt='Password: '):
    import termios
    if not sys.stdin.isatty():
        print('Not running on a terminal... bye!')
        exit(1)
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    new = old[::]
    new[3] = new[3] & ~(termios.ECHO | termios.ICANON)  # lflags
    try:
        termios.tcsetattr(fd, termios.TCSADRAIN, new)
        
        sys.stdout.write(prompt)
        sys.stdout.flush()
        passwd = b''
        while True:
            c = sys.stdin.buffer.read(1)
            if not c:
                raise EOFError()
            elif c == b'\n':
                break
            else:
                passwd += c
                sys.stdout.write('*')
                sys.stdout.flush()
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
    

def send_udp(trans):
    sock.sendto(trans.to_bytes(), (server_ip, server_port))

def handle_tcp(transaction):
    global u
    # TODO:
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

main()
