import socket_ext, struct

from binascii import hexlify
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

BLOCK_SIZE = 16

class EncSocket(object):
    def __init__(self, sock, key):
        """ Initializes an encrypt socket """
        self._sock = sock
        self._buff = b''
        self._key = key

    @property
    def sock(self):
        """ Returns the underlying socket """
        return self._sock

    def _recv_block(self):
        """ Helper private method for reading one entire encrypted block """


        # Read in the size
        size = struct.unpack('<I', self._sock.recvn(4))[0]

        # Read IV
        iv = self._sock.recvn(AES.block_size)

        # Decrypt data
        cipher = AES.new(self._key, AES.MODE_CBC, iv)
        edata = self._sock.recvn(size)
        return unpad(cipher.decrypt(edata), AES.block_size)

    def recv(self, size):
        """ Receive up to `size` bytes.  """

        if size < 0:
            raise ValueError()

        data = self._recv_block() if len(self._buff) == 0 else self._buff

        # Cut off first size bytes that we can read
        size = min(size, len(data))
        ret = data[:size]
        self._buff = data[size:]
        return ret

    def recvn(self, size):
        """ Receives exactly `size` bytes. """

        if size < 0:
            raise ValueError()

        ret = b''
        while len(ret) < size:
            ret += self.recv(size - len(ret))

        return ret

    def send(self, data):
        """ Send a encrypted data chunk. """

        cipher = AES.new(self._key, AES.MODE_CBC)
        edata = cipher.encrypt(pad(data, AES.block_size))
        
        payload = struct.pack('<I', len(edata)) + cipher.iv + edata
        self._sock.sendall(payload)


