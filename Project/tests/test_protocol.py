#!/usr/bin/env python3
"""Black-box integration tests for the NAFP/1 TCP protocol."""

import os
import socket
import struct
import subprocess
import tempfile
import threading
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 19337


def make_frame(frame_type, payload=b"", version=1, flags=0):
    """Create one complete protocol frame."""
    return struct.pack("!BBHI", version, frame_type, flags, len(payload)) + payload


def receive_exact(sock, size):
    """Read precisely size bytes or raise if the peer disconnects early."""
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise EOFError("connection closed before frame completed")
        data += chunk
    return data


def receive_response(sock):
    header = receive_exact(sock, 8)
    version, frame_type, flags, length = struct.unpack("!BBHI", header)
    payload = receive_exact(sock, length)
    assert (version, frame_type, flags) == (1, 2, 0)

    status, header_count = struct.unpack("!HH", payload[:4])
    offset = 4
    for _ in range(header_count):
        name_id = payload[offset]
        offset += 1
        if name_id == 255:
            name_length = payload[offset]
            offset += 1 + name_length
        value_length = struct.unpack("!H", payload[offset : offset + 2])[0]
        offset += 2 + value_length
    return status, payload[offset:]


class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary_directory = tempfile.TemporaryDirectory()
        cls.web_root = os.path.join(cls.temporary_directory.name, "www")
        os.mkdir(cls.web_root)
        os.mkdir(os.path.join(cls.web_root, "deep"))

        test_files = [
            ("index.html", b"INDEX"),
            ("empty", b""),
            ("large", b"A" * 200000),
            ("deep/x", b"NESTED"),
        ]
        for relative_name, content in test_files:
            with open(os.path.join(cls.web_root, relative_name), "wb") as output:
                output.write(content)

        cls.server = subprocess.Popen([os.path.join(ROOT, "bserve"), cls.web_root, str(PORT)])
        for _ in range(40):
            try:
                socket.create_connection(("127.0.0.1", PORT), 0.1).close()
                break
            except OSError:
                time.sleep(0.05)
        else:
            raise RuntimeError("server did not start")

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        cls.server.wait()
        cls.temporary_directory.cleanup()

    def connect(self):
        return socket.create_connection(("127.0.0.1", PORT))

    def request(self, sock, path):
        sock.sendall(make_frame(1, path.encode()))
        return receive_response(sock)

    def test_file_responses(self):
        with self.connect() as sock:
            self.assertEqual(self.request(sock, "/index.html"), (200, b"INDEX"))
            self.assertEqual(self.request(sock, "/empty"), (200, b""))
            self.assertEqual(self.request(sock, "/deep/x"), (200, b"NESTED"))
            self.assertEqual(len(self.request(sock, "/large")[1]), 200000)
            self.assertEqual(self.request(sock, "/missing")[0], 404)

    def test_persistent_unknown_and_fragmented_frames(self):
        with self.connect() as sock:
            combined = make_frame(99, b"ignored") + make_frame(1, b"/index.html")
            for byte in combined:
                sock.sendall(bytes([byte]))

            self.assertEqual(receive_response(sock), (200, b"INDEX"))
            self.assertEqual(self.request(sock, "/deep/x"), (200, b"NESTED"))

    def test_invalid_requests(self):
        for invalid_path in ("/../secret", "relative", "/a/../b", "/bad\\x"):
            with self.connect() as sock:
                self.assertEqual(self.request(sock, invalid_path)[0], 400)

        with self.connect() as sock:
            sock.sendall(make_frame(1, b"", flags=1))
            self.assertEqual(receive_response(sock)[0], 400)

        with self.connect() as sock:
            sock.sendall(make_frame(1, b"/index.html", version=9))
            self.assertEqual(receive_response(sock)[0], 400)

    def test_client_output_and_exit_code(self):
        success = subprocess.run(
            [os.path.join(ROOT, "bcurl"), "-v", f"127.0.0.1:{PORT}/index.html"],
            capture_output=True,
        )
        missing = subprocess.run(
            [os.path.join(ROOT, "bcurl"), f"127.0.0.1:{PORT}/missing"],
            capture_output=True,
        )

        self.assertEqual((success.returncode, success.stdout), (0, b"INDEX"))
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn(b"01 01 00 00", success.stderr)
        self.assertIn(b"< RESPONSE FRAME", success.stderr)

    def test_client_skips_unknown_frame_on_same_connection(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            listener.settimeout(3)
            port = listener.getsockname()[1]
            requests = []
            errors = []

            def reply():
                try:
                    with listener.accept()[0] as peer:
                        peer.settimeout(3)
                        raw_header = receive_exact(peer, 8)
                        _, _, _, length = struct.unpack("!BBHI", raw_header)
                        requests.append(receive_exact(peer, length))
                        payload = struct.pack("!HH", 200, 0) + b"EXTENSION OK"
                        # Send two extensions and a response one byte at a time.
                        frames = (make_frame(99, b"future") + make_frame(100) +
                                  make_frame(2, payload))
                        for byte in frames:
                            peer.sendall(bytes([byte]))
                        self.assertEqual(peer.recv(1), b"")
                except Exception as exc:
                    errors.append(exc)

            worker = threading.Thread(target=reply)
            worker.start()
            result = subprocess.run(
                [os.path.join(ROOT, "bcurl"), "-v", f"127.0.0.1:{port}/index.html"],
                capture_output=True, timeout=5,
            )
            worker.join(5)
            self.assertFalse(worker.is_alive())
            self.assertEqual(errors, [])
            self.assertEqual(requests, [b"/index.html"])
            self.assertEqual((result.returncode, result.stdout), (0, b"EXTENSION OK"))
            self.assertEqual(result.stderr.count(b"< SKIPPED FRAME"), 2)
            self.assertEqual(result.stderr.count(b"< RESPONSE FRAME"), 1)
            # A second connection would still be pending on this listening socket.
            listener.settimeout(0.1)
            with self.assertRaises(socket.timeout):
                listener.accept()

    def test_disconnect_and_oversized_header(self):
        sock = self.connect()
        sock.sendall(b"\x01\x01")
        sock.close()
        time.sleep(0.03)

        with self.connect() as sock:
            oversized_length = 16 * 1024 * 1024 + 1
            sock.sendall(struct.pack("!BBHI", 1, 1, 0, oversized_length))
            self.assertEqual(receive_response(sock)[0], 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
