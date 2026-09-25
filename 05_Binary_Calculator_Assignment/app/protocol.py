"""Binary Line Protocol (BLP/1) framing and payload encoding.

The intentionally small functions here expose every framing operation used by
the client and server.  They never assume a single recv() returns a frame.
"""
from __future__ import annotations

import socket
import struct
from dataclasses import dataclass
from typing import Optional

MAGIC = b"BL"
VERSION = 1
HEADER_FORMAT = "!2sBBHHIHHI"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 20 bytes
MAX_PAYLOAD = 1024 * 1024

TYPE_REQUEST = 1
TYPE_RESPONSE = 2
STATUS_NONE = 0


class ProtocolError(ValueError):
    """A complete frame is invalid, or a peer ended it prematurely."""


@dataclass(frozen=True)
class Frame:
    frame_type: int
    request_id: int
    status: int
    payload: bytes
    flags: int = 0
    version: int = VERSION


@dataclass(frozen=True)
class Request:
    method: str
    target: str
    headers: dict[str, str]


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict[str, str]
    body: bytes


def read_exact(sock: socket.socket, size: int) -> Optional[bytes]:
    """Return exactly size bytes; None means clean EOF before a new frame."""
    chunks = bytearray()
    while len(chunks) < size:
        part = sock.recv(size - len(chunks))
        if not part:
            if not chunks:
                return None
            raise ProtocolError("connection closed in the middle of a frame")
        chunks.extend(part)
    return bytes(chunks)


def write_all(sock: socket.socket, data: bytes) -> None:
    """Keep calling send until every byte is accepted by the OS."""
    view = memoryview(data)
    while view:
        sent = sock.send(view)
        if sent == 0:
            raise ConnectionError("socket closed during write")
        view = view[sent:]


def encode_frame(frame: Frame) -> bytes:
    if frame.version != VERSION:
        raise ProtocolError("this implementation only writes version 1")
    if not 0 <= frame.flags <= 0xFFFF or not 0 <= frame.request_id <= 0xFFFFFFFF:
        raise ProtocolError("flags or request id is outside its field width")
    if not 0 <= frame.status <= 999 or len(frame.payload) > MAX_PAYLOAD:
        raise ProtocolError("invalid status or payload length")
    header = struct.pack(HEADER_FORMAT, MAGIC, frame.version, frame.frame_type,
                         frame.flags, HEADER_SIZE, frame.request_id,
                         frame.status, 0, len(frame.payload))
    return header + frame.payload


def read_frame(sock: socket.socket) -> Optional[Frame]:
    """Read one length-delimited frame without consuming bytes of the next."""
    raw_header = read_exact(sock, HEADER_SIZE)
    if raw_header is None:
        return None
    magic, version, frame_type, flags, header_len, request_id, status, reserved, payload_len = struct.unpack(HEADER_FORMAT, raw_header)
    if magic != MAGIC or header_len != HEADER_SIZE or reserved != 0:
        raise ProtocolError("malformed BLP header")
    if payload_len > MAX_PAYLOAD:
        raise ProtocolError("payload length exceeds 1 MiB limit")
    payload = read_exact(sock, payload_len)
    if payload is None:  # payload_len is zero cannot produce this case
        payload = b""
    return Frame(frame_type, request_id, status, payload, flags, version)


def _encode_headers(headers: dict[str, str]) -> bytes:
    if len(headers) > 255:
        raise ProtocolError("at most 255 headers are allowed")
    output = bytearray([len(headers)])
    for name, value in headers.items():
        name_bytes = name.encode("ascii")
        value_bytes = value.encode("utf-8")
        if not name_bytes or len(name_bytes) > 255 or len(value_bytes) > 65535:
            raise ProtocolError("invalid header length")
        output.extend(struct.pack("!B", len(name_bytes)))
        output.extend(name_bytes)
        output.extend(struct.pack("!H", len(value_bytes)))
        output.extend(value_bytes)
    return bytes(output)


def _decode_headers(payload: bytes, offset: int) -> tuple[dict[str, str], int]:
    if offset >= len(payload):
        raise ProtocolError("missing header count")
    count = payload[offset]
    offset += 1
    headers: dict[str, str] = {}
    for _ in range(count):
        if offset >= len(payload):
            raise ProtocolError("truncated header name length")
        name_len = payload[offset]
        offset += 1
        if name_len == 0 or offset + name_len + 2 > len(payload):
            raise ProtocolError("invalid header name")
        try:
            name = payload[offset:offset + name_len].decode("ascii")
        except UnicodeDecodeError as exc:
            raise ProtocolError("header names must be ASCII") from exc
        offset += name_len
        value_len = struct.unpack_from("!H", payload, offset)[0]
        offset += 2
        if offset + value_len > len(payload):
            raise ProtocolError("truncated header value")
        try:
            value = payload[offset:offset + value_len].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ProtocolError("header values must be UTF-8") from exc
        offset += value_len
        if name.lower() in headers:
            raise ProtocolError("duplicate header")
        headers[name.lower()] = value
    return headers, offset


def encode_request(request: Request, request_id: int) -> bytes:
    method = request.method.encode("ascii")
    target = request.target.encode("utf-8")
    if not method or len(method) > 31 or len(target) > 65535:
        raise ProtocolError("invalid method or target length")
    payload = struct.pack("!B", len(method)) + method + struct.pack("!H", len(target)) + target + _encode_headers(request.headers)
    return encode_frame(Frame(TYPE_REQUEST, request_id, STATUS_NONE, payload))


def decode_request(frame: Frame) -> Request:
    if frame.version != VERSION or frame.frame_type != TYPE_REQUEST or frame.status != STATUS_NONE or frame.flags != 0:
        raise ProtocolError("not a valid BLP request frame")
    p = frame.payload
    if not p:
        raise ProtocolError("request has no method")
    method_len = p[0]
    offset = 1
    if method_len == 0 or offset + method_len + 2 > len(p):
        raise ProtocolError("invalid method field")
    try:
        method = p[offset:offset + method_len].decode("ascii")
    except UnicodeDecodeError as exc:
        raise ProtocolError("method must be ASCII") from exc
    offset += method_len
    target_len = struct.unpack_from("!H", p, offset)[0]
    offset += 2
    if target_len == 0 or offset + target_len > len(p):
        raise ProtocolError("invalid target field")
    try:
        target = p[offset:offset + target_len].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProtocolError("target must be UTF-8") from exc
    offset += target_len
    headers, offset = _decode_headers(p, offset)
    if offset != len(p):
        raise ProtocolError("extra bytes after request")
    return Request(method, target, headers)


def encode_response(response: Response, request_id: int) -> bytes:
    if not 100 <= response.status <= 599:
        raise ProtocolError("response status must be 100..599")
    return encode_frame(Frame(TYPE_RESPONSE, request_id, response.status,
                              _encode_headers(response.headers) + response.body))


def decode_response(frame: Frame) -> Response:
    if frame.version != VERSION or frame.frame_type != TYPE_RESPONSE or frame.flags != 0:
        raise ProtocolError("not a valid BLP response frame")
    if not 100 <= frame.status <= 599:
        raise ProtocolError("invalid response status")
    headers, offset = _decode_headers(frame.payload, 0)
    return Response(frame.status, headers, frame.payload[offset:])


def hexdump(data: bytes) -> str:
    lines = []
    for offset in range(0, len(data), 16):
        row = data[offset:offset + 16]
        hexes = " ".join(f"{byte:02X}" for byte in row)
        ascii_part = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in row)
        lines.append(f"{offset:04X}: {hexes:<47}  {ascii_part}")
    return "\n".join(lines)
