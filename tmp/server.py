#!/usr/bin/env python

import socket, thread

def accept_client(conn, addr):
    print('Connection address:', addr)
    while 1:
        data = conn.recv(BUFFER_SIZE)
        if not data: break
        print("received data:", data)
        conn.send(data)  # echo
    conn.close()

TCP_IP = '127.0.0.1'
TCP_PORT = 5005
BUFFER_SIZE = 20  # Normally 1024, but we want fast response

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((TCP_IP, TCP_PORT))
s.listen(1)

while True:
    thread.start_new_thread(accept_client, s.accept())
