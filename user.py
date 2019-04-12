import struct
from os import urandom


def u32(data):
    return struct.unpack('<I', data)[0]

class UserState(enum.IntEnum):
    OFFLINE, AUTH, CONNECTING, CHATTING = range(4)

class User:
    def __init__(self, cliID, secretKey):
        """ Initializes user """
        self.cliID = cliID
        self.secretKey = secretKey
        self.sessID = 0
        self.state = UserState.OFFLINE

    def disconnect(self):
        # TODO

    def get_auth(self):
        h_auth = hash1()
        h_auth.update(p32(u.sessID) + self.secretKey)
        return h_auth.digest()

    def get_key():
        h_key = hash2()
        h_key.update(p32(u.sessID) + self.secretKey)
        return h_key.digest()


    def init_sess(self):
        """ 
        Initializes a new session ID. It also silently discards previous session
        information.

        This session ID is different from the session ID used to identify a
        particular chat session. (That is computed from the hash of both
        client's session IDs).
        """

        self.sessID = u32(urandom(4))

