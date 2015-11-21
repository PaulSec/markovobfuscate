import asyncore
import socket
import struct
from markovobfuscate.obfuscation import MarkovKeyState


class LocalProxy(asyncore.dispatcher):
    """Listens for new client connections and creates new ToClient
    objects for each one."""

    def __init__(self, markov, localHost, localPort, mtunnelHost, mtunnelPort):
        """Creates the socket, binds to clientPort"""
        asyncore.dispatcher.__init__(self)
        self.markov = markov
        self.clientPort = localPort
        self.host = localHost
        self.mtunnel_host = mtunnelHost
        self.mtunnel_port = mtunnelPort
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind((self.host, self.clientPort))
        self.listen(5)

    def handle_accept(self):
        """Handles new client connections"""
        conn, addr = self.accept()
        print addr, "connected."
        return LocalProxy.SendToClient(self.markov, conn, self.mtunnel_host, self.mtunnel_port)

    def handle_close(self):
        self.close()
        print "Local socket closed"

    def run(self):
        print "Local server running..."
        self.listen(5)

    def die(self, error):
        print "Error: %s" % error
        print "Forcing shutdown..."
        self.handle_close()

    class SendToClient(asyncore.dispatcher_with_send):
        def __init__(self, markov, sock, remote_server, remote_port):
            self.markov = markov
            asyncore.dispatcher_with_send.__init__(self, sock)
            msock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            msock.connect((remote_server, remote_port))
            self.msock = LocalProxy.ToMTunnelServer(markov, self, msock)

        def handle_read(self):
            data = self.recv(1024)
            data = self.markov.obfuscate_string(data) + "\n"
            self.msock.send(data)

        def handle_close(self):
            print "Closing client socket..."
            self.close()

    class ToMTunnelServer(asyncore.dispatcher_with_send):
        def __init__(self, markov, sock, oSock):
            self.read_buffer = ''
            self.markov = markov
            asyncore.dispatcher_with_send.__init__(self, oSock)
            self.client = sock

        def handle_read(self):
            data = self.recv(1024)
            self.read_buffer += data
            while "\n" in self.read_buffer:
                data = self.read_buffer[:self.read_buffer.find("\n")]
                self.read_buffer = self.read_buffer[self.read_buffer.find("\n") + 1:]
                if len(data) > 0:
                    data = self.markov.deobfuscate_string(data)
                    self.client.send(data)

        def handle_close(self):
            print "Closing MTunnel socket..."
            self.close()


class MTunnelServer(asyncore.dispatcher):
    """Listens for new client connections and creates new ToClient
    objects for each one."""

    def __init__(self, markov, localHost, localPort):
        """Creates the socket, binds to clientPort"""
        self.markov = markov
        asyncore.dispatcher.__init__(self)
        self.clientPort = localPort
        self.host = localHost
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind((self.host, self.clientPort))
        self.listen(5)

    def handle_accept(self):
        """Handles new client connections"""
        conn, addr = self.accept()
        print addr, "connected."
        return MTunnelServer.MSendToClient(self.markov, conn)

    def handle_close(self):
        self.close()
        print "Local socket closed"

    def run(self):
        print "Local server running..."
        self.listen(5)

    def die(self, error):
        print "Error: %s" % error
        print "Forcing shutdown..."
        self.handle_close()

    class MSendToClient(asyncore.dispatcher_with_send):
        def __init__(self, markov, sock):
            self.read_buffer = ''
            self.markov = markov
            #self.msock = MTunnelServer.ToRemoteServer(markov, self, msock)
            self.msock = None
            self.state = 0
            asyncore.dispatcher_with_send.__init__(self, sock)

        def handle_read(self):
            data = self.recv(1024)
            self.read_buffer += data
            while "\n" in self.read_buffer:
                data = self.read_buffer[:self.read_buffer.find("\n")]
                self.read_buffer = self.read_buffer[self.read_buffer.find("\n") + 1:]
                if len(data) > 0:
                    data = self.markov.deobfuscate_string(data)

                    if self.state == 0:
                        if len(data) > 2:
                            # All socks4 initial packets start with 4 and end with 0
                            if data[0] == "\x04" and data[-1] == "\x00":
                                # Socks4/4a
                                if len(data) >= 9:  # minimum for socks4
                                    if data[1] == "\x01":
                                        # Let's only support stream connections...
                                        port = struct.unpack("!H", data[2:4])[0]
                                        ip = data[4:8]

                                        # Get user string
                                        user = ""
                                        index = 8
                                        while data[index] != "\x00":
                                            user += data[index]
                                            index += 1

                                        if ip[0:3] == "\x00\x00\x00" and ip[3] != "\x00":
                                            # socks4a
                                            index += 1
                                            domain = ""

                                            while data[index] != "\x00":
                                                domain += data[index]
                                                index += 1

                                            try:
                                                ip = socket.gethostbyname(domain)
                                                msock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                                msock.connect((ip, port))
                                                self.msock = MTunnelServer.ToRemoteServer(self.markov, self, msock)
                                                self.send(self.markov.obfuscate_string("\x00\x5a" + struct.pack("!H", port) + socket.inet_aton(ip)) + "\n")
                                                self.state = 0x10
                                            except socket.error:
                                                self.send(self.markov.obfuscate_string("\x00\x5b" + struct.pack("!H", port) + socket.inet_aton(ip)) + "\n")

                                        else:
                                            # socks4
                                            try:
                                                ip = socket.inet_ntoa(ip)
                                                msock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                                msock.connect((ip, port))
                                                self.msock = MTunnelServer.ToRemoteServer(self.markov, self, msock)
                                                self.send(self.markov.obfuscate_string("\x00\x5a" + struct.pack("!H", port) + socket.inet_aton(ip)) + "\n")
                                                self.state = 0x10
                                            except socket.error:
                                                self.send(self.markov.obfuscate_string("\x00\x5b" + struct.pack("!H", port) + socket.inet_aton(ip)) + "\n")

                                pass
                            elif data[0] == 0x5:
                                # Socks5
                                pass
                        pass
                    elif self.state == 0x10:
                        self.msock.send(data)

        def handle_close(self):
            print "Closing client socket..."
            self.close()

    class ToRemoteServer(asyncore.dispatcher_with_send):
        def __init__(self, markov, sock, oSock):
            self.markov = markov
            asyncore.dispatcher_with_send.__init__(self, oSock)
            self.client = sock

        def handle_read(self):
            data = self.recv(1024)
            data = self.markov.obfuscate_string(data) + "\n"
            self.client.send(data)

        def handle_close(self):
            print "Closing MTunnel socket..."
            self.close()


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(
        prog=__file__,
        description="Identifies and extracts information from bots",
        version="%(prog)s v0.1 by Brian Wallace (@botnet_hunter)",
        epilog="%(prog)s v0.1 by Brian Wallace (@botnet_hunter)"
    )

    parser.add_argument('-s', '--server', default=False, required=False, action='store_true', help="Run as end server")
    parser.add_argument('-r', '--remote', default=None, type=str, action='append', help='Remote server to tunnel to')
    parser.add_argument('-p', '--port', default=9050, type=int, help='Port to listen on')

    args = parser.parse_args()

    # Regular expression to split our training files on
    split_regex = r'\n'

    # File/book to read for training the Markov model (will be read into memory)
    training_file = "datasets/ts_lyrics.lst"

    # Obfuscating Markov engine
    m = MarkovKeyState()

    # Read the shared key into memory
    with open(training_file, "r") as f:
        text = f.read()

    import re
    # Split learning data into sentences, in this case, based on periods.
    map(m.learn_sentence, re.split(split_regex, text))

    if args.server:
        # We are the terminating server
        print "Running as server"
        server = MTunnelServer(m, "127.0.0.1", 9999)
        asyncore.loop()
    else:
        # We are the local server
        server = LocalProxy(m, 'localhost', args.port, "127.0.0.1", 9999)
        asyncore.loop()
