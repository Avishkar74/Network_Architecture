"""Single-process BLP file/calculator server using raw TCP sockets."""
from __future__ import annotations

import argparse
import mimetypes
import socket
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .protocol import (Frame, ProtocolError, Request, Response, TYPE_REQUEST,
                       VERSION, decode_request, encode_response, read_frame,
                       write_all)


def response(status: int, body: bytes | str = b"", **headers: str) -> Response:
    if isinstance(body, str):
        body = body.encode("utf-8")
    headers.setdefault("content-length", str(len(body)))
    return Response(status, headers, body)


def calculator(target: str) -> Response | None:
    parsed = urlsplit(target)
    operations = {"/add": lambda a, b: a + b, "/sub": lambda a, b: a - b,
                  "/mul": lambda a, b: a * b, "/div": lambda a, b: a / b}
    if parsed.path not in operations:
        return None
    query = parse_qs(parsed.query, keep_blank_values=True)
    if set(query) != {"a", "b"} or len(query["a"]) != 1 or len(query["b"]) != 1:
        return response(400, "bad calculator arguments\n", **{"content-type": "text/plain"})
    try:
        a, b = float(query["a"][0]), float(query["b"][0])
        if parsed.path == "/div" and b == 0:
            raise ValueError
        result = operations[parsed.path](a, b)
    except ValueError:
        return response(400, "bad calculator arguments\n", **{"content-type": "text/plain"})
    text = str(int(result)) if result == int(result) else str(result)
    return response(200, text + "\n", **{"content-type": "text/plain"})


def serve_request(request: Request, root: Path) -> Response:
    if request.method != "GET":
        return response(405, "method not allowed\n", **{"content-type": "text/plain"})
    calculated = calculator(request.target)
    if calculated is not None:
        return calculated
    parsed = urlsplit(request.target)
    if parsed.query or not parsed.path.startswith("/"):
        return response(400, "invalid file target\n", **{"content-type": "text/plain"})
    try:
        candidate = (root / parsed.path.lstrip("/")).resolve()
        candidate.relative_to(root)
    except ValueError:
        return response(400, "path traversal rejected\n", **{"content-type": "text/plain"})
    if not candidate.is_file():
        return response(404, "not found\n", **{"content-type": "text/plain"})
    body = candidate.read_bytes()
    content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
    return response(200, body, **{"content-type": content_type})


def handle_connection(conn: socket.socket, root: Path) -> None:
    """Process sequential request/response frames until the peer closes."""
    while True:
        try:
            frame = read_frame(conn)
            if frame is None:
                return
            # A known header and payload lets us skip an unknown type safely.
            if frame.frame_type != TYPE_REQUEST:
                continue
            if frame.version != VERSION:
                write_all(conn, encode_response(response(400, "unsupported version\n"), frame.request_id))
                continue
            try:
                req = decode_request(frame)
                reply = serve_request(req, root)
            except ProtocolError as exc:
                reply = response(400, f"malformed request: {exc}\n", **{"content-type": "text/plain"})
            write_all(conn, encode_response(reply, frame.request_id))
        except ProtocolError:
            # The header was not trustworthy enough to determine synchronization.
            return
        except (ConnectionError, OSError):
            return


def serve(root: Path, port: int, host: str = "127.0.0.1", ready=None, stop=None) -> None:
    root = root.resolve()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((host, port))
        listener.listen()
        listener.settimeout(0.2)
        if ready is not None:
            ready.set()
        while stop is None or not stop.is_set():
            try:
                conn, _ = listener.accept()
            except socket.timeout:
                continue
            with conn:
                handle_connection(conn, root)


def main() -> None:
    parser = argparse.ArgumentParser(description="BLP file and calculator server")
    parser.add_argument("root", type=Path)
    parser.add_argument("port", type=int)
    args = parser.parse_args()
    if not args.root.is_dir() or not 1 <= args.port <= 65535:
        parser.error("root must be a directory and port must be 1..65535")
    print(f"bserve listening on 127.0.0.1:{args.port}; root={args.root.resolve()}")
    try:
        serve(args.root, args.port)
    except KeyboardInterrupt:
        print("\nstopped")
