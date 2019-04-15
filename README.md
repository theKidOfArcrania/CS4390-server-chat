# CS4390-server-chat

This is a server-based chat written in Python 3 for our CS4390 Networks project. 

This features a CLI for initiating chats with other clients with AES encryption.
It also contains a chat history (stored server-side) between two clients.

## Building/Running

Setting up virtual environment and installing requirements:

```sh
$ python -m venv venv
$ source venv/bin/activate
$ pip3 install -r requirements.txt
```

To run the server:
```sh
$ python3 server.py
```

To run the client:
```sh
$ python3 client.py
```

## License

TODO
