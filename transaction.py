import struct

class StructDef(object):
    """ 
    Abstract class used to define a struct-like class that can easily be
    transformed to binary data.

    By default, little endian is used to pack/unpack struct definitions into
    binary data.

    NOTE THAT THESE STRUCTS ARE IMMUTABLE. That means once it is initialized,
    they cannot be modified. 

    =====================
    Subclassing StructDef
    =====================
    All subclasses must define a class variable named `_structdef`!

    This variable is a list of 2/3-tuples, (each defining the name, the struct
    type, and a default value if any). 

    For example, the following point class, which can be defined in C as:

        struct point {
            int x;
            int y;
        }

    Would be defined in a `_structdef` like this:

        _structdef = [('x', 'i', 0),
            ('y', 'i', 0)]

    In this case, both `x` and `y` are optional integer parameters, which
    default to 0 if not provided. 
    """

    def __init__(self, params):
        """ 
        Initializes from a set of parameters defined by a dict object.

        All the parameters in the struct-def must be provided by name unless the
        struct-def defines a default value. In that case, the default value will
        be used instead if not specified in the `params` argument.
        """

        sdef = type(self)._structdef

        copy = dict()
        names = []
        fmt = '<'
        for tup in sdef:
            name = tup[0]
            names.append(name)
            fmt += tup[1]

            if name in params:
                copy[name] = params[name]
            elif len(tup) > 2:
                copy[name] = tup[2]
            else:
                raise KeyError(name)

        self._params = copy
        self.__names__ = names
        self.__fmt__ = struct.Struct(fmt)

    def __getattr__(self, attr):
        """ 
        This allows us to access a particular struct field using the dot (.)
        operator.
        
        For example, accessing the `x` field, you could do
        `mystruct.params['x']` or more succinctly put as `mystruct.x`. 
        """
        return self._params[attr]

    @property
    def params(self):
        """ Returns a copy of the parameters used to initialize this struct"""
        return dict(self._params)

    def to_bytes(self):
        """ Converts this struct into a binary bytes form. """
        vals = []
        for n in self.__names__:
            vals.append(self._params[n])
        return self.__fmt__.pack(*vals)

    @classmethod
    def _from_bytes(cls, data):
        """ 
        This protected class method converts binary data into a dict object,
        which can later be passed directly into the constructor of the class.

        Note that most sub-classes *should* instead define a `from_bytes`
        function that will actually create an instance of that object instead.
        """

        # Build our names and struct format
        keys = []
        fmt = '<'
        for tup in cls._structdef:
            keys.append(tup[0]) 
            fmt += tup[1]

        # Unpack from struct
        values = struct.unpack(fmt, data)
        assert(len(keys) == len(values))

        # Put key/value pairs into dict
        params = {}
        for i in range(len(keys)):
            params[keys[i]] = values[i]
        return params


class TransactionType:
    ''' Represents the types of transactions that can take place '''
    HELLO        = 1
    CHALLENGE    = 2
    RESPONSE     = 3
    AUTH_SUCCESS = 4
    AUTH_FAIL    = 5
    CONNECT      = 6
    CONNECTED    = 7
    CHAT_REQUEST = 8
    CHAT_STARTED = 9
    UNREACHABLE  = 10
    END_REQUEST  = 11
    END_NOTIF    = 12
    CHAT         = 13
    HISTORY_REQ  = 14
    HISTORY_RESP = 15


class Transaction(StructDef):
    """ 
    This represents the protocol when exchanging a message:
    
    The following shows how each transaction object is laid out::

         <--- 32  bytes --->
        +-------------------+
        |       leng        |
        +-------------------+
        |  type   |  cliID  |
        +-------------------+
        |       sessID      |
        +-------------------+
        |                   |
        |      message      |
        |        ...        |
        |                   |
        +-------------------+ 

    Where:
        
    * **leng** is the size of the transaction object
    * **type** is the transaction type, which should be one of the constants
      defined in TransactionType.
    * **cliID** is the client ID that is being referred to, dependant on the
      transaction type being used. 
    * **sessID** refers to the session ID, which is also dependant to what
      transaction type being used.
    * **message** refers to a variable length body of the transaction.

    =============================
    Converting to and from binary
    =============================
    To convert a transaction struct into a binary data, simply do the
    following::

        >>> tt = TransactionType
        >>> t = Transaction(type=tt.HISTORY_REQ, cliID=0x1337)
        >>> data = t.to_bytes()
        >>> data
        b'\x0c\x00\x00\x00\x0e\x007\x13\x00\x00\x00\x00'
    
    And to covert from binary back to a Transaction object do this::

        >>> t = Transaction.from_bytes(data)

    """

    _structdef = (('leng', 'I', 0), 
            ('type', 'H'),
            ('cliID', 'H', 0),
            ('sessID', 'I', 0),
            ('message', '0s', b''))

    def __init__(self, **params):
        """ 
        Constructs a Transaction from some parameters.

        IT IS IMPORTANT TO NOTE that this takes keyword arguments, as compared
        to a dict object for parameters, so that we can define a transaction
        as::

            >>> t = Transaction(type=tt.HISTORY_REQ, cliID=0x1337)

        Rather than the more cumbersome::

            >>> t = Transaction(dict(type=tt.HISTORY_REQ, cliID=0x1337))

        NEVER provide the `leng` parameter, as this will always be computed by
        us! 
        """
        
        params['leng'] = len(params.get('message', b'')) + 12
        super().__init__(params)

    def to_bytes(self):
        """
        Overrides the StructDef version of `to_bytes` so that we can tack on our
        variable-length message.
        """

        return super().to_bytes() + self.message

    @staticmethod
    def from_bytes(data):
        """ 
        Converts binary data into a Transaction object 
        
        This will also do some checks on the length of the data
        """
        
        params = Transaction._from_bytes(data)
        if params['leng'] is not len(data):
            raise ValueError('Transaction length mismatch')
        
        return Transaction(**params)
