# Binary Line Protocol, version 1 (BLP/1)

## 1. Purpose

BLP/1 is a minimal binary request/response protocol designed to teach
application-level framing over TCP. It supports `GET` requests for static files
and four arithmetic routes (`/add`, `/sub`, `/mul`, `/div`).

## 2. Connection model

- Transport: TCP, single connection per client session.
- The client opens the connection, sends one or more request frames in sequence,
  and closes the connection when finished.
- The server keeps the connection open after each valid frame and responds in
  arrival order.
- The server closes the connection only on EOF from the client or an
  unrecoverable protocol error (bad magic, invalid header length, invalid
  reserved field, payload exceeding 1 MiB).
- An unknown frame type is silently skipped; no response is sent.

## 3. Frame format

Every message is a **frame** consisting of a fixed 20-byte header followed by a
variable-length payload. Total frame size = `20 + Payload Length`.

All multi-byte integers are **unsigned big-endian** (network byte order).

### 3.1 Frame header — 20 bytes

| Offset | Size (bytes) | Field | Valid values |
|---:|---:|---|---|
| 0 | 2 | Magic | Literal ASCII `BL` = `42 4C` |
| 2 | 1 | Version | `1` |
| 3 | 1 | Type | `1` = Request; `2` = Response; other = unknown extension |
| 4 | 2 | Flags | `0` (reserved for future use) |
| 6 | 2 | Header Length | `20` (allows future header extension) |
| 8 | 4 | Request ID | Any `u32`; response echoes the request's value |
| 12 | 2 | Status | Request: `0`; Response: HTTP-style code `100`–`599` |
| 14 | 2 | Reserved | `0` |
| 16 | 4 | Payload Length | `0`–`1,048,576` (bytes of payload after this header) |

### 3.2 Framing rule

A receiver reads exactly 20 bytes to obtain the header, extracts `Payload
Length`, then reads exactly that many additional bytes. It must not read beyond
the declared length.

### 3.3 Unknown frame type handling

When `Type` is not `1` or `2`, the receiver **MUST** consume exactly `Payload
Length` bytes (already read by the frame parser) and continue without sending
a response. This allows future frame types to coexist on the same connection.

### 3.4 Unrecoverable errors

The following conditions indicate that stream synchronization cannot be trusted;
the connection **MUST** be closed:

- `Magic` != `42 4C`
- `Header Length` != `20`
- `Reserved` != `0`
- `Payload Length` > `1,048,576`
- EOF received in the middle of a header or payload

## 4. Payload formats

### 4.1 Shared: header block

Both request and response payloads include a counted list of name/value headers:

```
Header Count   : u8          (0–255 headers)
repeat Header Count:
  Name Length  : u8          (1–255; non-zero)
  Name         : ASCII bytes  (Name Length bytes)
  Value Length : u16
  Value        : UTF-8 bytes  (Value Length bytes)
```

Header names are case-insensitive. Duplicate names (after lower-casing) are
invalid and result in a 400 response.

### 4.2 Request payload

```
Method Length  : u8          (1–31)
Method         : ASCII bytes  (Method Length bytes)
Target Length  : u16          (1–65535)
Target         : UTF-8 bytes  (Target Length bytes; must begin with '/')
[Header block as §4.1]
```

No request body is defined in v1.

### 4.3 Response payload

```
[Header block as §4.1]
Body           : remaining bytes (0 or more)
```

## 5. Status codes

| Code | Meaning | When used |
|---|---|---|
| 200 | OK | Successful file read or calculator result |
| 400 | Bad Request | Malformed frame, invalid request content, bad arguments, path traversal, division by zero, unsupported version |
| 404 | Not Found | Requested file does not exist under the web root |
| 405 | Method Not Allowed | Method other than `GET` |

## 6. Server behaviour

- Only `GET` is supported. Any other method → 405.
- Calculator routes: `/add`, `/sub`, `/mul`, `/div` with query parameters `a`
  and `b` (both required, both must be valid numbers; `/div` with `b=0` → 400).
- File routes: `GET /filename` resolves the path below the configured web root.
  Path traversal (any resolved path outside the root) → 400.
- Successful file responses include `content-type` and `content-length` headers.
- Unknown request content or version != 1 → 400.

## 7. Constraints

| Item | Limit |
|---|---|
| Maximum payload | 1,048,576 bytes (1 MiB) |
| Maximum headers per frame | 255 |
| Maximum header name | 255 bytes |
| Maximum header value | 65,535 bytes |
| Maximum method | 31 bytes |
| Maximum target | 65,535 bytes |

## 8. Example: annotated request frame

**Command:** `GET /index.html`, request ID 1, one header `host: localhost`

```
Offset  Hex bytes                                      Annotation
------  -----------------------------------------------  --------------------------------
0000:   42 4C                                          Magic = "BL"
0002:   01                                             Version = 1
0003:   01                                             Type = 1 (REQUEST)
0004:   00 00                                          Flags = 0
0006:   00 14                                          Header Length = 20
0008:   00 00 00 01                                    Request ID = 1
000C:   00 00                                          Status = 0 (request)
000E:   00 00                                          Reserved = 0
0010:   00 00 00 22                                    Payload Length = 34
---- payload (34 bytes) ----
0014:   03                                             Method Length = 3
0015:   47 45 54                                       Method = "GET"
0018:   00 0B                                          Target Length = 11
001A:   2F 69 6E 64 65 78 2E 68 74 6D 6C              Target = "/index.html"
0025:   01                                             Header Count = 1
0026:   04                                             Name Length = 4
0027:   68 6F 73 74                                    Name = "host"
002B:   00 09                                          Value Length = 9
002D:   6C 6F 63 61 6C 68 6F 73 74                    Value = "localhost"
```

Full hex as output by `bcurl -v`:

```
0000: 42 4C 01 01 00 00 00 14 00 00 00 01 00 00 00 00  BL..............
0010: 00 00 00 22 03 47 45 54 00 0B 2F 69 6E 64 65 78  ...".GET../index
0020: 2E 68 74 6D 6C 01 04 68 6F 73 74 00 09 6C 6F 63  .html..host..loc
0030: 61 6C 68 6F 73 74                                alhost
```

## 9. Example: annotated response frame

**Response to:** `GET /add?a=2&b=3`, request ID 1, body `5\n`

```
Offset  Hex bytes                                      Annotation
------  -----------------------------------------------  --------------------------------
0000:   42 4C                                          Magic = "BL"
0002:   01                                             Version = 1
0003:   02                                             Type = 2 (RESPONSE)
0004:   00 00                                          Flags = 0
0006:   00 14                                          Header Length = 20
0008:   00 00 00 01                                    Request ID = 1 (echoes request)
000C:   00 C8                                          Status = 200
000E:   00 00                                          Reserved = 0
0010:   00 00 00 2E                                    Payload Length = 46
---- payload (46 bytes) ----
0014:   02                                             Header Count = 2
0015:   0C                                             Name Length = 12
0016:   63 6F 6E 74 65 6E 74 2D 74 79 70 65            Name = "content-type"
0022:   00 0A                                          Value Length = 10
0024:   74 65 78 74 2F 70 6C 61 69 6E                  Value = "text/plain"
002E:   0E                                             Name Length = 14
002F:   63 6F 6E 74 65 6E 74 2D 6C 65 6E 67 74 68      Name = "content-length"
003D:   00 01                                          Value Length = 1
003F:   32                                             Value = "2"  (body is 2 bytes)
0040:   35 0A                                          Body = "5\n"
```

Full hex as output by `bcurl -v`:

```
0000: 42 4C 01 02 00 00 00 14 00 00 00 01 00 C8 00 00  BL..............
0010: 00 00 00 2E 02 0C 63 6F 6E 74 65 6E 74 2D 74 79  ......content-ty
0020: 70 65 00 0A 74 65 78 74 2F 70 6C 61 69 6E 0E 63  pe..text/plain.c
0030: 6F 6E 74 65 6E 74 2D 6C 65 6E 67 74 68 00 01 32  ontent-length..2
0040: 35 0A                                            5.
```

## 10. Versioning

The Header Length field allows a v2 implementation to extend the header beyond
20 bytes. A v1 receiver that cannot parse the extended header should close the
connection. The Type field allows new frame types; v1 receivers skip unknown
types cleanly using the Payload Length. Maximum payload size is bounded to
prevent resource exhaustion.
