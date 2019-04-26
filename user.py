import struct, enum, threading
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from os import urandom
from socket import *

from transaction import TransactionType as tt, Transaction
from socket_enc import EncSocket
from consts import *

class UserState(enum.IntEnum):
    OFFLINE, AUTH, CONNECTING, CONNECTED, CHATTING = range(5)

class User(object):
    @staticmethod
    def new_sess_id():
        """ Obtains a new session ID """
        return u32(urandom(4))

    def __init__(self, cliID, secretKey):
        """ Initializes user """
        self.cliID = cliID
        self.secretKey = secretKey
        self.sessID = 0
        self.state = UserState.OFFLINE

        self.__sbind = None
        self.__conn = None

    @property
    def cookie(self):
        return self.__cookie

    def accept_conn(self):
        """ Server only: accepts a potential client connection. """

        if not self.__sbind:
            raise ValueError('Not in listening state!')

        conn = self.__conn
        if conn:
            conn.reset()

        conn, _ = self.__sbind.accept()
        conn.settimeout(server_activity_timeout)
        self.__conn = EncSocket(conn, self.get_key())

    def connected(self):
        """ Server only: marks this user as "connected". This means that the
        server will NOT accept anymore connections. """

        if not self.__sbind:
            raise ValueError('Not in listening state!')

        self.__sbind.close()
        self.__sbind = None
        self.sessID = 0
        self.state = UserState.CONNECTED
        self.send_transaction(Transaction(type=tt.CONNECTED))


    def recv_transaction(self):
        """ Receives a transaction object from the opened socket, if any"""
        if not self.__conn:
            raise ValueError('User is not connected yet!')

        first = self.__conn.recvn(4)
        t = Transaction.from_bytes(first + self.__conn.recvn(u32(first) - 4))
        return t

    def send_transaction(self, trans):
        """ Sends a transaction object to the opened socket, if any """
        if not self.__conn:
            raise ValueError('User is not connected yet!')

        self.__conn.send(trans.to_bytes())

    def init_connection(self, recv=None):
        """ Initializes connection between client and server. This code is
        called from both the server AND the client.         

        To differenciate between the two, the client will pass an additional
        parameter specifying the data that it received (i.e. the AUTH_SUCCESS
        transaction), and the server will pass no parameters.

        On the client end, this code will read the received transaction, and
        initialize a new TCP connection sending the cookie value received from
        this transaction.

        On the server end, this code will bind a new TCP connection and generate
        a new cookie value. This will also RETURNS a Transaction object that
        SHOULD BE sent on the UDP socket afterwards (i.e. the AUTH_SUCCESS).
        """

        # Don't need CBC as cookie is random enough!
        cipher = AES.new(self.get_key(), AES.MODE_ECB)
        conn = socket(AF_INET, SOCK_STREAM)
        fmt = struct.Struct('<8sH')

        if recv:
            # Client-end
            if recv.type != tt.AUTH_SUCCESS:
                raise ValueError(f'Invalid transaction type: {recv.type.name}')
            
            data = unpad(cipher.decrypt(recv.message), AES.block_size)
            cookie, port = fmt.unpack(data)
            conn.connect((server.ip, port))
            conn.settimeout(client_activity_timeout)

            ret = None
            conn = EncSocket(conn, self.get_key())
            self.__conn = conn
            sbind = None

            self.send_transaction(Transaction(type=tt.CONNECT, message=cookie))
            t = self.recv_transaction()
            if t.type != tt.CONNECTED:
                conn.reset()
                raise RuntimeError('Connection malformed/failed')
        else:
            # Server-end
            cookie = urandom(8)
            conn.bind((server.ip, 0))
            conn.listen(5)
            data = fmt.pack(cookie, conn.getsockname()[1])
            edata = cipher.encrypt(pad(data, AES.block_size))

            ret = Transaction(type=tt.AUTH_SUCCESS, message=edata)
            sbind = conn
            conn = None

        self.__cookie = cookie
        self.__sbind = sbind
        self.__conn = conn
        return ret

    def disconnect(self):
        """ Disconnects the client from current chat (if still connected) and
        sets user to OFFLINE, cleaning up any resources used."""
        self.__cookie = None
        self.sessID = 0

        if self.__sbind:
            self.__sbind.close()
            self.__sbind = None

        if self.__conn:
            self.__conn.close()
            self.__conn = None

        self.state = UserState.OFFLINE


    def get_auth(self):
        h_auth = hash1()
        h_auth.update(p32(self.sessID) + self.secretKey)
        return h_auth.digest()

    def get_key(self):
        h_key = hash2()
        h_key.update(p32(self.sessID) + self.secretKey)
        return h_key.digest()[:AES.block_size]

    def init_sess(self):
        """ 
        Initializes a new session ID. It also silently discards previous session
        information.
        """

        self.sessID = u32(urandom(4))

class InvalidUser(User):
    def __init__(self, cliID):
        """ Initializes an "invalid" user that cannot login """
        User.__init__(self, cliID, b'')

    def accept_conn(self):
        raise ValueError('Invalid user!')

    def connected(self):
        raise ValueError('Invalid user!')

    def init_connecion(self):
        raise ValueError('Invalid user!')

    def recv_transaction(self):
        raise ValueError('Invalid user!')
    
    def send_transaction(self):
        raise ValueError('Invalid user!')

    def get_auth(self):
        return b'Invalid!'

    def get_key(self):
        return b'Invalid!'

def p32(data):
    return struct.pack('<I', data)

def u32(data):
    return struct.unpack('<I', data)[0]

