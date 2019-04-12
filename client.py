from consts import * # server_ip, server_port
from socket import *
from transaction import *
import struct, traceback, logging as log, enum
import user

tt = TransactionType

def p32(num):
    return struct.pack('<I', num)

def u32(data):
    return struct.unpack('<I', data)[0]

def main():
    global sock
    global u

    sock = socket(AF_INET, SOCK_DGRAM)
        
    u = user.User(1234, b"password")    # temporary client_id and password
    
    send_udp(Transaction(type = tt.HELLO, cliID = u.cliID))


    while True:
        data, _ = sock.recvfrom(1024)
        if handle_udp(data):
            break

def send_udp(trans):
    sock.sendto(trans.to_bytes(), (server_ip, server_port))

def handle_udp(data):
    leng = u32(data[:4])
    if len(data) < 4:
        log.error('Datagram is too small.')
        return
    if len(data) < leng:
        log.error('Malformed datagram.')
        return
    elif len(data) > leng:
        log.warning('Extraneous data at end of packet')

    t = Transaction.from_bytes(data[:leng])
    if t.type == tt.CHALLENGE:
        # do i need to check anything?
        u.sessID = u32(t.message)
        send_udp(Transaction(type = tt.RESPONSE, cliID=u.cliID, message = u.get_auth()))
    elif t.type == tt.AUTH_SUCCESS:
        return True # finished with udp
    elif t.type == tt. AUTH_FAIL:
        print("Authentication failed")
        return True

main()
