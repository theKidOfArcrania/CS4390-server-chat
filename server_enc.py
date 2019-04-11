#!/usr/bin/env python

import socket, socket_enc, _thread, sys
import json
from base64 import b64decode
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# hardcoded key
key = b'\xa0k\x83<A\x02\xef\xfdf\xfd\xf4D<6&\xfc'

def accept_client(conn, addr):
    es = socket_enc.EncSocket(conn, key)
    print('Connection address:', addr)
    while 1:
        try:  
            print("Received: ", es.recv(BUFFER_SIZE))
        except (ValueError, KeyError) as e:                #exception handling
            raise
            print("Incorrect decryption")     
        es.send(b"hi")
    conn.close()
    print("Connection " + str(addr) + " closed")

TCP_IP = '127.0.0.1'
TCP_PORT = int(sys.argv[1])
BUFFER_SIZE = 1024

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((TCP_IP, TCP_PORT))
s.listen(1)

while True:
    _thread.start_new_thread(accept_client, s.accept())
