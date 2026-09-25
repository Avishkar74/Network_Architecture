"""One-request BLP command-line client."""
from __future__ import annotations

import argparse
import socket
import sys

from .protocol import (ProtocolError, Request, decode_response, encode_frame,
                       encode_request, hexdump, read_frame, write_all)


def parse_destination(value: str) -> tuple[str, int, str]:
    if "/" not in value or ":" not in value.split("/", 1)[0]:
        raise ValueError("destination must be host:port/path")
    authority, path_tail = value.split("/", 1)
    host, port_text = authority.rsplit(":", 1)
    port = int(port_text)
    if not host or not 1 <= port <= 65535:
        raise ValueError("invalid host or port")
    return host, port, "/" + path_tail


def main() -> None:
    parser = argparse.ArgumentParser(description="BLP client")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("destination")
    args = parser.parse_args()
    try:
        host, port, target = parse_destination(args.destination)
        request_bytes = encode_request(Request("GET", target, {"host": host}), 1)
        # Exactly one socket/connect call for this invocation.
        with socket.create_connection((host, port)) as sock:
            if args.verbose:
                print("request frame:\n" + hexdump(request_bytes), file=sys.stderr)
            write_all(sock, request_bytes)
            frame = read_frame(sock)
        if frame is None:
            raise ProtocolError("server closed without a response")
        raw_response = encode_frame(frame)
        reply = decode_response(frame)
        if args.verbose:
            print("response frame:\n" + hexdump(raw_response), file=sys.stderr)
            print(f"status: {reply.status}", file=sys.stderr)
        sys.stdout.buffer.write(reply.body)
        raise SystemExit(0 if reply.status < 400 else 1)
    except (ValueError, OSError, ProtocolError) as exc:
        print(f"bcurl: {exc}", file=sys.stderr)
        raise SystemExit(2)
