# Extends the socket class by implementing a few new methods
# Just do `import socket_ext` and you socket should be updated!

from socket import *
import struct

def recvn(sock, size):
    """ 
    Receives EXACTLY <size> bytes. If this cannot be done, this method will
    raise EOFError exception.
    """

    res = b''
    while size > 0:
        data = sock.recv(size)
        if data == b'':
            raise EOFError()
        size -= len(data)
        res += data
    return res

socket.recvn = recvn

# Send RST packet
def reset(sock):
    sock.setsockopt(SOL_SOCKET, SO_LINGER, struct.pack('ii', 1, 0))
    sock.close()
socket.reset = reset
