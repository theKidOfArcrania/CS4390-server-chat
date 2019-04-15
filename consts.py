server_ip = '127.0.0.1'
server_port = 4242
conn_timeout = 5

ping_timeout = 55
server_activity_timeout = ping_timeout + 5
client_activity_timeout = server_activity_timeout + 5

def hash1():
    import hashlib
    return hashlib.md5()

def hash2():
    import hashlib
    return hashlib.sha256()
