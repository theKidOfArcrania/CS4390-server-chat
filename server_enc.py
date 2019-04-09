#!/usr/bin/env python

import socket, _thread
import json
from base64 import b64decode
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# hardcoded key
key = b'\xa0k\x83<A\x02\xef\xfdf\xfd\xf4D<6&\xfc'

def accept_client(conn, addr):
    print('Connection address:', addr)
    while 1:
        data = conn.recv(BUFFER_SIZE)
        if not data: break        
        try:  
           b64 = json.loads(data)                          #json data, iv and ct
           iv = b64decode(b64['iv'])
           ct = b64decode(b64['ciphertext'])

           cipher = AES.new(key, AES.MODE_CBC, iv)         #decrypt
           pt = unpad(cipher.decrypt(ct), AES.block_size)

           print("The message was: ", pt)                  #print it

        except (ValueError, KeyError) as e:                #exception handling
           print("Incorrect decryption")     
        conn.send(data)  # echo
    conn.close()
    print("Connection " + str(addr) + " closed")

TCP_IP = '127.0.0.1'
TCP_PORT = 5005
BUFFER_SIZE = 1024

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((TCP_IP, TCP_PORT))
s.listen(1)

while True:
    _thread.start_new_thread(accept_client, s.accept())
