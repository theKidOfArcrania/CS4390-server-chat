#!/usr/bin/env python3

import socket
import socket_enc
import json
import sys
from base64 import b64encode
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from Crypto.Random import get_random_bytes

TCP_IP = '127.0.0.1'
TCP_PORT = int(sys.argv[1]) #5005
BUFFER_SIZE = 1024

# hardcoded 16-byte key
key = b'\xa0k\x83<A\x02\xef\xfdf\xfd\xf4D<6&\xfc' 

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((TCP_IP, TCP_PORT))
es = socket_enc.EncSocket(s, key)
while True:
    # original input to be encrypted
    data = bytes(input(), "utf-8")
    es.send(data)
    data = es.recv(BUFFER_SIZE)
    
s.close()

