##
# Copyright (c) 2013 Yury Selivanov
# License: Apache 2.0
##
"""Greensocket (non-blocking) for Tornado.

Use ``grenado.socket`` in the same way as you would use stdlib's
``socket.socket`` in ``grenado.task`` tasks or coroutines invoked
from them.
"""
import tornado.ioloop
from tornado.iostream import IOStream
import greenlet
import asyncio
from socket import error, SOCK_STREAM
from socket import socket as std_socket

from . import yield_from
from . import GreenUnixSelectorLoop


def _wait_callback(func, args, kwargs):


class socket(object):

    def __init__(self, *args, _from_sock=None, **kwargs):
        if _from_sock:
            self._sock = _from_sock
        else:
            self._sock = std_socket(*args, **kwargs)
        self._sock.setblocking(False)
        self._loop = tornado.ioloop.IOLoop.current()
        #assert isinstance(self._loop, GreenUnixSelectorLoop), \
        #    'GreenUnixSelectorLoop event loop is required'

    @classmethod
    def from_socket(cls, sock):
        return cls(_from_sock=sock)

    @property
    def family(self):
        return self._sock.family

    @property
    def type(self):
        return self._sock.type

    @property
    def proto(self):
        return self._sock.proto

    def _proxy(attr):
        def proxy(self, *args, **kwargs):
            meth = getattr(self._sock, attr)
            return meth(*args, **kwargs)

        proxy.__name__ = attr
        proxy.__qualname__ = attr
        proxy.__doc__ = getattr(getattr(std_socket, attr), '__doc__', None)
        return proxy

    def _copydoc(func):
        func.__doc__ = getattr(
            getattr(std_socket, func.__name__), '__doc__', None)
        return func

    @_copydoc
    def setblocking(self, flag):
        if flag:
            raise error('grenado.socket does not support blocking mode')

    @_copydoc
    def recv(self, nbytes):
        fut = self._loop.sock_recv(self._sock, nbytes)
        yield_from(fut)
        return fut.result()

    @_copydoc
    def connect(self, addr):
        fut = self._loop.sock_connect(self._sock, addr)
        yield_from(fut)
        return fut.result()

    @_copydoc
    def sendall(self, data, flags=0):
        assert not flags
        fut = self._loop.sock_sendall(self._sock, data)
        yield_from(fut)
        return fut.result()

    @_copydoc
    def send(self, data, flags=0):
        self.sendall(data, flags)
        return len(data)

    @_copydoc
    def accept(self):
        fut = self._loop.sock_accept(self._sock)
        yield_from(fut)
        sock, addr = fut.result()
        return self.__class__.from_socket(sock), addr

    __file = None

    @_copydoc
    def makefile(self, mode, *args, **kwargs):
        if mode not in ('rb', 'wb'):
            raise NotImplementedError
        if self.__file is None:
            stream = IOStream(self._sock)
            self.__file = StreamFile(stream)
        return self.__file

    bind = _proxy('bind')
    listen = _proxy('listen')
    getsockname = _proxy('getsockname')
    getpeername = _proxy('getpeername')
    gettimeout = _proxy('gettimeout')
    getsockopt = _proxy('getsockopt')
    setsockopt = _proxy('setsockopt')
    fileno = _proxy('fileno')
    detach = _proxy('detach')
    close = _proxy('close')
    shutdown = _proxy('shutdown')

    del _copydoc, _proxy


class StreamFile(object):
    def __init__(self, stream):
        self._stream = stream

    def read(self, size):
        fut = self._stream.read_bytes(size)

class ReadFile(object):

    def __init__(self, loop, sock):
        self._loop = loop
        self._sock = sock
        self._buf = bytearray()

    def read(self, size):
        while 1:
            if size <= len(self._buf):
                data = self._buf[:size]
                del self._buf[:size]
                return data

            gl = greenlet.getcurrent()
            while 1:
                try:
                    res = self._sock.read(max(size, 8000))
                    break
                except socket.error as e:
                    if e.errno in _ERRNO_WOULDBLOCK:
                        def handler(fd, event):
                            gl.switch()
                        self._loop.add_handler(self._sock.fileno(), handler, self._loop.READ)
            self._buf.extend(res)

    def close(self):
        pass


class WriteFile(object):

    def __init__(self, loop, sock):
        self._loop = loop
        self._sock = sock

    def write(self, data):
        fut = self._loop.sock_sendall(self._sock, data)
        yield_from(fut)
        return fut.result()

    def flush(self):
        pass

    def close(self):
        pass


def create_connection(address: tuple, timeout=None):
    loop = asyncio.get_event_loop()
    host, port = address

    rslt = yield_from(
        loop.getaddrinfo(host, port, family=0, type=SOCK_STREAM))

    for res in rslt:
        af, socktype, proto, canonname, sa = res
        sock = None

        try:
            sock = socket(af, socktype, proto)
            sock.connect(sa)
            return sock
        except ConnectionError:
            if sock:
                sock.close()

    raise error('unable to connect to {!r}'.format(address))
