from __future__ import annotations

import socket
import threading
import unittest
from pathlib import Path

from app.protocol import (Frame, ProtocolError, Request, TYPE_REQUEST,
                          decode_response, encode_frame, encode_request,
                          read_frame, write_all)
from app.server import handle_connection

ROOT = Path(__file__).resolve().parents[1] / "www"


class BLPTests(unittest.TestCase):
    def start_connection(self):
        client, server = socket.socketpair()
        def run_server():
            try:
                handle_connection(server, ROOT)
            finally:
                server.close()
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        return client, server, thread

    def request(self, sock, target, request_id=1, method="GET"):
        write_all(sock, encode_request(Request(method, target, {}), request_id))
        frame = read_frame(sock)
        self.assertIsNotNone(frame)
        return decode_response(frame)

    def test_file_and_calculator_routes(self):
        client, server, thread = self.start_connection()
        with client:
            self.assertEqual(self.request(client, "/index.html").status, 200)
            self.assertEqual(self.request(client, "/add?a=2&b=3", 2).body, b"5\n")
            self.assertEqual(self.request(client, "/sub?a=10&b=4", 3).body, b"6\n")
            self.assertEqual(self.request(client, "/mul?a=6&b=7", 4).body, b"42\n")
            self.assertEqual(self.request(client, "/div?a=1&b=0", 5).status, 400)
            self.assertEqual(self.request(client, "/missing.html", 6).status, 404)
        thread.join(1)

    def test_six_frames_one_tcp_connection_and_unknown_skip(self):
        client, server, thread = self.start_connection()
        with client:
            # Coalesce six request frames plus an unknown type in one send.
            wire = b"".join(encode_request(Request("GET", f"/add?a={i}&b=1", {}), i) for i in range(1, 4))
            wire += encode_frame(Frame(99, 88, 0, b"future extension"))
            wire += b"".join(encode_request(Request("GET", f"/mul?a={i}&b=2", {}), i) for i in range(4, 7))
            write_all(client, wire)
            replies = [decode_response(read_frame(client)) for _ in range(6)]
            self.assertEqual([r.status for r in replies], [200] * 6)
            self.assertEqual([r.body for r in replies], [b"2\n", b"3\n", b"4\n", b"8\n", b"10\n", b"12\n"])
        thread.join(1)

    def test_frame_can_arrive_in_small_pieces(self):
        client, server, thread = self.start_connection()
        wire = encode_request(Request("GET", "/index.html", {}), 9)
        with client:
            # Header and payload are intentionally fragmented across many writes.
            for byte in wire:
                write_all(client, bytes([byte]))
            reply = decode_response(read_frame(client))
            self.assertEqual(reply.status, 200)
        thread.join(1)

    def test_invalid_version_yields_400_and_next_frame_stays_synced(self):
        client, server, thread = self.start_connection()
        with client:
            bad = bytearray(encode_request(Request("GET", "/index.html", {}), 7))
            bad[2] = 2  # version byte
            write_all(client, bytes(bad) + encode_request(Request("GET", "/add?a=1&b=1", {}), 8))
            self.assertEqual(decode_response(read_frame(client)).status, 400)
            self.assertEqual(decode_response(read_frame(client)).body, b"2\n")
        thread.join(1)

    def test_malformed_and_oversized_headers_close_connection(self):
        client, server, thread = self.start_connection()
        with client:
            malformed = bytearray(20)
            malformed[:2] = b"NO"
            write_all(client, bytes(malformed))
            self.assertEqual(client.recv(1), b"")
        thread.join(1)

        left, right = socket.socketpair()
        with left, right:
            oversized = encode_frame(Frame(TYPE_REQUEST, 1, 0, b"x"))[:16] + (1048577).to_bytes(4, "big")
            write_all(left, oversized)
            with self.assertRaises(ProtocolError):
                read_frame(right)

    def test_protocol_rejects_truncated_request_payload(self):
        left, right = socket.socketpair()
        with left, right:
            # Declares a 4-byte payload but supplies only 2 bytes, then closes.
            header = encode_frame(Frame(TYPE_REQUEST, 1, 0, b"abcd"))[:20]
            left.sendall(header + b"ab")
            left.shutdown(socket.SHUT_WR)
            with self.assertRaises(ProtocolError):
                read_frame(right)

    def test_path_traversal_and_method_are_rejected(self):
        client, server, thread = self.start_connection()
        with client:
            self.assertEqual(self.request(client, "/../../secret", 1).status, 400)
            self.assertEqual(self.request(client, "/index.html", 2, "POST").status, 405)
        thread.join(1)
