#!/usr/bin/env python3

import socket
import json
import sys
from base64 import b64encode
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from Crypto.Random import get_random_bytes

TCP_IP = '127.0.0.1'
TCP_PORT = 5005
BUFFER_SIZE = 1024

# hardcoded 16-byte key
key = b'\xa0k\x83<A\x02\xef\xfdf\xfd\xf4D<6&\xfc' 

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((TCP_IP, TCP_PORT))
while True:
    # original input to be encrypted
    plaintext = bytes(input(), "utf-8")
    
    # create cipher, AES in CBC mode
    cipher = AES.new(key, AES.MODE_CBC)

    # stuff for encryption, create iv and ciphertext
    ct_bytes = cipher.encrypt(pad(plaintext, AES.block_size))
    iv = b64encode(cipher.iv).decode('utf-8')
    ct = b64encode(ct_bytes).decode('utf-8')

    # json result, send this
    result = json.dumps({"iv":iv, "ciphertext":ct})
  
    # send json result
    s.sendto(result.encode('utf-8'),(TCP_IP, TCP_PORT))
    
    data = s.recv(BUFFER_SIZE)
    
s.close()

