# Session 5 Revision Notes - HTTP Evolution

## HTTP/1.0 (May 1996)

**Model**: One request, one response, close
- TCP handshake → Send request → Get response → FIN
- 24-object page = 24 TCP handshakes + 24 RTTs = 9.6 seconds

**No Host header** → One IP = One website → 1/3 IPv4 for HTTP alone

**Caching**: Timestamp-based (Last-Modified, If-Modified-Since)
- Problems: No sub-second precision, clock drift, mtime ≠ identity

**Keep-alive** (non-standard, unreliable)
- Some servers honored it, some ignored, some crashed

## HTTP/1.1 Early (RFC 2068, Jan 1997)

**Persistence default**: Keep-alive unless Connection: close

**Host header** (the fix): One IP, thousands of sites now possible
- Same pattern: When transport layer's address inadequate, put name in message

**ETag** (fingerprint): SHA256 instead of timestamp
- Strong: byte-for-byte identical (for Range)
- Weak: semantically equivalent (for compression)

**Range requests**: bytes=100-199 → 206 Partial Content
- Video scrubbing, resumable downloads, data lake queries

**Chunked encoding**: Send body without knowing length
- Same pattern as FastCGI records: length-prefix + empty delimiter

**Accept-***: Content negotiation (encoding, language, etc)
- Vary header: Cache key instruction

## HTTP/1.1 Today (RFC 2616 → 7230-7235 → 9110-9114)

**The split (2014)**: 6230-7235 split RFC 2616 by audience
- Caching, routing, auth separate documents

**The semantic split (2022)**: RFC 9110/9111 (semantics) vs 9112/9113/9114 (wire format)
- GET means same in all versions; only bytes change

**Token character rules**: Why JWT is base64url
- Must survive: Authorization header, URL, cookie, form, JSON
- Intersection of all alphabets = 64 characters

## HTTP/1.1 Problems

**Head-of-line blocking**: One slow response delays all behind it
- 2003ms vs 3ms for same file (pipelined vs parallel)
- Root cause: No request ID; order is the only identifier

**Header bloat**: 97.5% of upload is repeats
- 805B headers/request × 80 = 62KB repeats, 1.6KB unique
- Solution: Compression (not gzip, HPACK)

**Connection limits**: RFC said "2", browsers shipped "6", websites hacked "18" with domain sharding
- RFC 7230 deleted the sentence (conceded to reality)

**Request smuggling**: One stream, two interpretations
- Content-Length: 6 vs Transfer-Encoding: chunked
- Attacker posts request CDN never saw

**Nagle + Delayed ACK bug**: 40ms latency on persistent connections
- write(header); write(body) → Nagle holds body, ACK delayed
- Solution: TCP_NODELAY

## HTTP/2 (RFC 7540, 2015)

**From SPDY** (2009-2015): "55% faster" → standardized → SPDY retired 2016

**Frame header** (9 bytes): [Length 24][Type 8][Flags 8][R 1][Stream ID 31]
- Length + Stream ID = no ambiguity, multiplexing possible

**Stream IDs**: ODD (client), EVEN (server), no coordination
- Each frame says who it's for → responses can be out of order

**Ten frame types**: DATA, HEADERS, PRIORITY, RST_STREAM, SETTINGS, PUSH_PROMISE, PING, GOAWAY, WINDOW_UPDATE, CONTINUATION

**HPACK** (RFC 7541):
- Static table (61 entries, like ":method: GET" = 0x82)
- Dynamic table (per connection, reuses previous values)
- Huffman encoding (per string, if shrinks)
- Same 6-byte header set → first 79B, second 6B (97% reduction)

**CRIME defense**: Fixed Huffman table (no adaptive), exact-match only, never-indexed flag

**Multiplexing**: Same 6 files, one connection
- HTTP/1.1 pipelined: 2003ms (all blocked by slowest)
- HTTP/2 streams: 5-7ms (only slowest one slow)
- 400× faster

**Server push**: Never deprecated in RFC, dead in practice (0.7% usage)
- Problem: Doesn't know cache (pushes duplicates)
- Replacement: 103 Early Hints (let client decide)

**Connection preface**: "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n" (24 bytes, was "PRISM" joke)

**TCP head-of-line blocking**: One lost packet stalls all streams
- HTTP/2 can't fix (TCP limitation)
- Streams lose data, others must wait for TCP ordering

## HTTP/3 (RFC 9114, 2022)

**QUIC transport**: UDP-based because middleboxes block unknown protocols
- SCTP (2000) = good, but blocked everywhere
- UDP = not good, but already allowed

**Why encryption**: Changeability
- Middleboxes depend on anything readable
- Encrypt headers → can't depend → can change

**Handshake**: 2 RTT (1-RTT) vs 3 RTT (TCP+TLS)
- Initial packet carries TLS ClientHello
- No separate transport handshake

**0-RTT**: 1 RTT (resuming)
- Cost: Replay vulnerability (same early data to different servers)
- Rule: Idempotent only (GET/HEAD, not POST)

**Connection IDs**: Identity independent of addressing
- Network change (wifi→LTE) = address changes, connection survives
- TCP problem: address IS identity
- QUIC fix: rotate IDs (don't track)

**QPACK** (RFC 9204): No HoL blocking in headers
- Problem: HPACK dynamic table assumes ordering
- Solution: Separate encoder/decoder streams
- Encoder only references known entries

## Current Adoption (2026)

- HTTP/1.1: 15% (embedded, internal, legacy)
- HTTP/2: 70%
- HTTP/3: 15%
- No cutover; very long tail

3-5% of networks block UDP → HTTP/3 falls back to TCP
95.3% of Google clients can use QUIC

## Four Design Patterns

**Pattern 1: Multiplexing needs identity**
- TCP ports, SS7 ids, FastCGI ids, HTTP stream ids
- Missing ID → order mandatory → head-of-line blocking

**Pattern 2: Every fix is the next problem**
- Persistence → Pipelining → HoL blocking
- HTTP/2 fix → TCP HoL visible
- QUIC fix → HPACK broken → QPACK fixes

**Pattern 3: Semantics ≠ Encoding**
- RFC 9110 (what HTTP means, all versions)
- RFC 9112/9113/9114 (how to write it down, version-specific)
- GET unchanged since 1996; wire format changed 3 times

**Pattern 4: Reality beats spec**
- 302: Browsers made it GET, RFC added 307
- Connections: RFC said 2, browsers used 6, RFC deleted it
- 418 Teapot: Easter egg that stuck (reserved forever)
- Push: Never deprecated, quietly removed
- QUIC: UDP blocked, so use UDP (only option)

## Key Numbers

- **HTTP/1.0**: 1945 (May)
- **HTTP/1.1**: 1997 (Jan), 2616 (Jun 1999)
- **HTTP/2**: 2015 (Feb), 9113 (Jun 2022)
- **HTTP/3**: 2022 (Jun)
- **SPDY**: 2009-2016 (7 years, then absorbed into HTTP/2)
- **24 bytes**: Connection preface length
- **9 bytes**: HTTP/2 frame header
- **31 bits**: HTTP/2 stream ID capacity
- **97.5%**: Header repeats in 80-request page
- **2.8%**: Gzip compression ratio on text
- **3 RTT**: TCP + TLS 1.3 + HTTP/2 cold
- **2 RTT**: QUIC + HTTP/3 cold (1-RTT)
- **1 RTT**: QUIC 0-RTT resuming
- **400×**: Faster (multiplexing vs pipelined)
- **62,720 bytes**: Repeated headers in 80-request page

## Red Flags for Exam

1. "HTTP/1.0" = "close after response"
2. "Host header" = "enables virtual hosts on single IP"
3. "ETag" = "fingerprint, not timestamp"
4. "Range" = "enables video scrubbing + resumable downloads"
5. "Keep-alive" = "not in HTTP/1.0; default in HTTP/1.1"
6. "Head-of-line blocking" = "one slow response delays all others (pipelined)"
7. "No request ID" = "order becomes identifier"
8. "Request smuggling" = "different frame interpretation"
9. "HTTP/2 stream ID" = "31 bits; ODD=client, EVEN=server"
10. "HPACK dynamic table" = "per connection; second request 97% cheaper"
11. "CRIME" = "compressed size leaks secret"
12. "Server push" = "never deprecated, completely dead (0.7%)"
13. "QUIC connection ID" = "survives network change"
14. "0-RTT" = "only idempotent; replay vulnerable"
15. "RFC 9110/9111" = "semantics (all versions), not wire format"
16. "Deployed reality" = "beats specification"
17. "302" = "browsers made it GET; RFC added 307"
18. "4 RTT" = "no, wrong number; check TCP+TLS"
19. "QPACK" = "separate streams, no HoL blocking"
20. "Connection preface" = "PRI*HTTP/2.0... (24 bytes)"

