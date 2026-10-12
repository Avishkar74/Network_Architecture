# Session 5 Cheatsheet - HTTP Evolution

## Timeline
| Year | Version | Key Feature | Problem It Solved |
|------|---------|-------------|-------------------|
| 1996 | HTTP/1.0 | One request per connection | Nothing (first web protocol) |
| 1997 | HTTP/1.1 | Persistence default | Slow page loads (24 RTTs) |
| 2015 | HTTP/2 | Multiplexing (stream IDs) | Head-of-line blocking |
| 2022 | HTTP/3 | QUIC transport | TCP HoL blocking + 3 RTT handshake |

## HTTP/1.0 Basics
- One request, one response, close
- No Host header (one IP = one site)
- Keep-alive non-standard (unreliable)
- Caching: Last-Modified (timestamp, weak)

## HTTP/1.1 Fixes
- Host header (virtual hosting)
- ETag (identity-based cache validation)
- Range (video scrubbing, resumable downloads)
- Chunked encoding (stream without length)
- Persistence is default

## HTTP/1.1 Problems
| Problem | Measurement | Cause |
|---------|-------------|-------|
| Head-of-line blocking | 2003ms vs 3ms | No request ID |
| Header bloat | 97.5% repeats | No header compression |
| Too many connections | 6 per origin | Browsers ignore RFC "2" |
| Request smuggling | One byte, two reads | Ambiguous framing |
| Nagle + ACK latency | 40ms per request | TCP algorithms collide |

## HTTP/2 Solutions
- **Stream ID** (31 bits): Every frame labeled
- **HPACK compression**: 97% reduction on repeat headers
- **Multiplexing**: Responses out of order
- **Connection preface**: "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n" (24 bytes)

## HTTP/2 Frame Header
```
[Length: 24 bits][Type: 8][Flags: 8][Reserved: 1][Stream ID: 31]
```
- No ambiguity (length is explicit)
- Request smuggling impossible

## HPACK Compression
1. **Static table** (61 entries): ":method: GET" = 0x82
2. **Dynamic table** (per connection): Previous values indexed
3. **Huffman** (per string): Only if shrinks

Result:
- First request: 174B → 79B (55%)
- Second request: 174B → 6B (97%)

## HTTP/2 Multiplexing
| Setup | Response Times |
|-------|-----------------|
| HTTP/1.1 pipelined (blocked) | 2003, 2003, 2003, 2003, 2003, 2003 |
| HTTP/2 multiplexed | 5, 6, 7, 8, 9, 2005 |
| Speedup | **400×** |

## HTTP/3 Improvements
- **Connection ID**: Survives network change (wifi→LTE)
- **1-RTT handshake** vs TCP's 3 RTT
- **0-RTT resuming**: 1 RTT (but replay risk)
- **QUIC streams**: Independent loss (no TCP ordering)

## Why UDP?
- SCTP (2000) is better but blocked by middleboxes
- UDP already allowed (is "the hole that exists")
- Encrypt headers to prevent middlebox dependency

## Current Adoption (2026)
- HTTP/1.1: 15% (legacy, embedded)
- HTTP/2: 70%
- HTTP/3: 15%
- 3-5% block all UDP (fallback to TCP)

## Four Design Patterns

**1. Multiplexing needs identity**
- HTTP/1.1: No ID → order is ID → ordering mandatory
- HTTP/2+: 31-bit ID → order independent

**2. Every fix is the next problem**
- Persistence → Pipelining → HoL blocking
- HTTP/2 fix → TCP HoL visible
- QUIC fix → HPACK broken → QPACK fixes

**3. Semantics ≠ Encoding**
- RFC 9110: What HTTP means (all versions)
- RFC 9112/9113/9114: How to write it (version-specific)
- Upgrade without changing app

**4. Reality beats spec**
- 302: Browsers made it GET → RFC added 307
- Connections: RFC "2" → browsers "6" → RFC deleted it
- Push: Never deprecated, quietly removed (0.7%)
- QUIC: Blocked → use UDP anyway

## Key Formulas

**Head-of-line blocking cost**:
```
Pipelined response time = max(request1, request2, ..., requestN)
Multiplexed response time = request_time (individual)
```

**Header compression ratio**:
```
First request: ~55% (static table + dynamic table setup)
Repeat request: ~97% (all indices)
```

**Handshake round trips**:
```
TCP + TLS 1.3: 3 RTT (before GET sent)
QUIC 1-RTT: 2 RTT (GET sent in flight)
QUIC 0-RTT: 1 RTT (GET sent immediately)
```

## Definitions

| Term | Meaning |
|------|---------|
| **ETag** | Content hash (fingerprint, not timestamp) |
| **Weak ETag** | W/"…" (semantically equivalent, not identical) |
| **Range** | bytes=100-199 (partial content) |
| **206** | Partial Content (range response) |
| **416** | Range Not Satisfiable (file smaller than requested) |
| **Keep-alive** | Connection: keep-alive (HTTP/1.0 extension) |
| **Chunked** | Transfer-Encoding: chunked (no Content-Length) |
| **ALPN** | Protocol negotiation inside TLS handshake |
| **Alt-Svc** | Advertise alternative protocols via header |
| **HPACK** | Header compression (RFC 7541) |
| **Stream ID** | Identifier for request/response pair |
| **Frame** | 9-byte header + payload (HTTP/2) |
| **QPACK** | HPACK without head-of-line blocking |
| **0-RTT** | Early data in TLS resumption |

## Mnemonics

**HTTP/1.0 problem**:
- **C**lose: Closes after every response

**HTTP/1.1 fix**:
- **P**ersistence: Keeps connection open

**HTTP/2 fix**:
- **M**ultiplexing: Stream IDs allow out-of-order

**HTTP/3 fix**:
- **Q**UIC: Independent streams (no TCP ordering)

## Common Mistakes

| Mistake | Reality |
|---------|---------|
| "HTTP/1.1 has HTTP/2 performance" | No, HoL blocking limits to sequential |
| "Gzip makes HTTP fast" | No, headers 97.5% repeats (gzip only helps bodies) |
| "HTTP/2 needs binary" | No, binary is consequence; identifiers are point |
| "Server push makes pages faster" | No, 0.7% use it; wastes bandwidth if item cached |
| "RFC says 2 connections" | No, RFC deleted that; browsers use 6 |
| "Connection preface is HTTP/2" | No, it's handshake before HTTP/2 starts |
| "Stream ID can be 32 bits" | No, 31 bits (1 reserved) |
| "HPACK uses adaptive Huffman" | No, fixed table (unchanging) |
| "QUIC is just UDP" | No, it's custom protocol (happens to run on UDP) |
| "0-RTT is always safe" | No, replay risk (only idempotent requests) |

## For Exam: Write Down

**Connection preface** (exactly):
```
PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n
```

**HTTP/2 frame header format**:
```
[24-bit length][8-bit type][8-bit flags][1-bit reserved][31-bit stream ID]
```

**Stream ID allocation**:
```
Client-initiated: ODD (1, 3, 5, ...)
Server-initiated: EVEN (2, 4, 6, ...)
Connection level: 0 (SETTINGS, PING, GOAWAY)
```

**HPACK compression stages**:
```
1. Static table (0x82 for GET)
2. Dynamic table (per-connection reuse)
3. Huffman encoding (if shrinks)
```

**HTTP version timeline**:
```
1.0 (1996) → 1.1 (1997, 2616 in 1999) → 2 (2015) → 3 (2022)
```

## Last-Minute Facts

- 24 objects @ 200ms RTT on HTTP/1.0 = 9.6 seconds
- HTTP/2 makes it 400× faster (same network)
- 97.5% of upload on page load is repeated headers
- One lost TCP packet stalls all HTTP/2 streams
- QUIC fixes it: only affected stream delays
- 0-RTT saves 295ms on resumed connections
- No HTTP/2.1 will exist (went to 3, not 2.1)
- 418 I'm a teapot is reserved forever (was joke)
- Server push is dead: 0.7% usage despite RFC support
- UDP fallback is automatic, not negotiated

