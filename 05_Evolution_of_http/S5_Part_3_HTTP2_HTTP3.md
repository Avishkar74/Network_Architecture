# Part 3: HTTP/2 and HTTP/3 - The Protocol Overhaul

## 3.1 HTTP/2: From SPDY to RFC 7540

### The Journey

| Date | Event | Significance |
|------|-------|--------------|
| Nov 2009 | SPDY announced | "up to 55% faster" on top 25 sites |
| 2010-2014 | Chrome, Firefox, nginx, Twitter, Facebook ship SPDY | Google runs both ends; measures production |
| Feb 2015 | Google announces SPDY retirement | >25% Chrome resources on HTTP/2 vs <5% SPDY |
| May 2015 | RFC 7540 (HTTP/2) + RFC 7541 (HPACK) | SPDY with edges filed off |
| May 2016 | SPDY removed from Chrome 51 | 6.5 years: experiment → obsolete |
| Jun 2022 | RFC 9113 obsoletes 7540 | deprecates priorities, removes h2c Upgrade dance |

**Why HTTP/2, not HTTP/2.0?**
```
RFC 2616 (HTTP/1.1) created confusion:
  "Is a 1.x server required to support 1.0?"
  "What about 1.2?"
  
Solution: No minor versions in HTTP/2
  Next version = new number + new wire format
  No HTTP/2.1 will ever exist
```

---

## 3.2 HTTP/2 Frame Structure

### The 9-Byte Header

```
[Length (24 bits)] [Type (8 bits)] [Flags (8 bits)] [R (1 bit)] [Stream ID (31 bits)]
 [  Frame payload (0 to 2^24-1 bytes)  ]
```

**What it buys**:
- Length in fixed place, fixed size (no ambiguity)
- Stream ID (31 bits) on every frame (multiplexing)
- Request smuggling becomes unrepresentable

**Stream ID allocation**:
```
Client-initiated: ODD (1, 3, 5, 7, ...)
Server-initiated: EVEN (2, 4, 6, 8, ...)

No coordination needed
"Your" streams and "my" streams have different ranges
```

**Stream 0**: Connection-level control (SETTINGS, PING, GOAWAY)

### Example: Real HTTP/2 Connection Preface

```
Client sends preface:
PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n

Hex: 50 52 49 20 2a 20 48 54 54 50 2f 32 2e 30 0d 0a 0d 0a 53 4d 0d 0a 0d 0a
     (exactly 24 bytes)

Why "PRISM"?
  It was 2013. RFC doesn't officially say.
  But it's a joke that stuck.

If an HTTP/1.1 server receives this:
  Method: PRI
  Version: HTTP/2.0
  → 501 Not Implemented (fails cleanly)
```

---

## 3.3 The Ten Frame Types

| Type | Name | Purpose | Replaced |
|------|------|---------|----------|
| 0x00 | DATA | Body in chunks ≤ MAX_FRAME_SIZE | Content-Length / chunked |
| 0x01 | HEADERS | Opens stream; carries HPACK block | Request line + headers |
| 0x02 | PRIORITY | Deprecated (RFC 9113 → RFC 9218) | — |
| 0x03 | RST_STREAM | Cancel ONE stream | Close TCP (kills everything) |
| 0x04 | SETTINGS | Announce limits (both directions) | Nothing (no way to say before) |
| 0x05 | PUSH_PROMISE | Server push (deprecated by reality) | Nothing (didn't exist) |
| 0x06 | PING | Round-trip time; keep awake | Nothing |
| 0x07 | GOAWAY | "Last stream I'll process" + drain | Connection: close |
| 0x08 | WINDOW_UPDATE | Flow control (stream + connection) | TCP's window (single level) |
| 0x09 | CONTINUATION | Header block > one frame | Nothing (and 2024 DoS) |

**Default settings**:
```
HEADER_TABLE_SIZE: 4,096
INITIAL_WINDOW_SIZE: 65,535 (per stream)
MAX_FRAME_SIZE: 16,384
MAX_CONCURRENT_STREAMS: no default (minimum 100)
```

---

## 3.4 HPACK: Header Compression (RFC 7541)

### Three Mechanisms

**1. Static Table** (61 fixed entries):
```
Index 2 = ":method: GET"
Send: 0x82 (one byte)
Cost: 0 bytes

Index 1 = ":authority"
Send: 0x86 (one byte) + authority value

Same GET request = same bytes every time
```

**2. Dynamic Table** (per connection):
```
First request:
  Cookie: session=abc123...def456
  → Added to connection's dynamic table at index 62
  → Costs 300 bytes

Second request:
  Cookie: session=abc123...def456
  → Lookup finds it at index 62
  → Send: one byte (62)
  → Costs 1 byte
```

**3. Huffman Encoding** (per string):
```
Character frequency from real headers:
  "e" = 5 bits (common)
  "X" = 8 bits (rare)

Only used if it actually shrinks the string
(otherwise, plain ASCII is shorter)
```

### The Numbers

**Same header set, three ways**:
```
HTTP/1.1 text:        174 bytes

HPACK, first time:     79 bytes (55% reduction)
HPACK, second time:     6 bytes (97% reduction!)

Six one-byte indices for six header fields
```

### CRIME Attack & HPACK Defense

**The vulnerability** (CRIME, 2012):

Attacker controls part of request; observes compressed size
```
GET /?guess=a Cookie: session=SECRET
  → Compressed size: 412 bytes (no "a" match in SECRET)

GET /?guess=S Cookie: session=SECRET
  → Compressed size: 411 bytes (found "S", one byte saved!)
  
Attacker: "Correct! Secret starts with S"
Repeat per character → recover entire secret by size
```

**HPACK's structural defense**:

1. **Fixed Huffman table**: Built from corpus, published in Appendix B, never adapts to current data
   - Attacker text and secret text can't meet in dynamic dictionary

2. **Dynamic table is exact-match index**: Only lookups, no substring matching
   - Guessing prefix of cookie wins nothing

3. **Mark fields "never indexed"**: Some headers flagged as sensitive
   ```
   authorization: (never indexed)
   set-cookie: (never indexed)
   ```

**Defense against CRIME**: There's no shared adaptive dictionary between attacker-controlled data and secrets.

---

## 3.5 Multiplexing: Stream IDs

### Same Six Files, One Connection

**HTTP/1.1 pipelined**:
```
/big.txt?delay=2.0  2003.4 ms  ← Blocks everyone
/style.css          2003.6 ms  ← Waiting
/app.js             2003.8 ms  ← Waiting
/logo.png           2004.1 ms  ← Waiting
/icon.png           2004.2 ms  ← Waiting
/hero.png           2004.4 ms  ← Waiting

Responses must arrive in order
```

**HTTP/2 same connection**:
```
stream 3  /style.css     4.9 ms   ← Immediate
stream 7  /logo.png      5.7 ms   ← Immediate
stream 9  /icon.png      6.9 ms   ← Immediate
stream 5  /app.js        6.9 ms   ← Immediate
stream 11 /hero.png      7.8 ms   ← Immediate
stream 1  /big.txt      2005.9 ms ← Just this one

Out of order, because each frame says who it's for
400× faster
```

**How it works**:
```
Client sends:
  HEADERS stream=1 GET /big.txt
  HEADERS stream=3 GET /style.css
  HEADERS stream=5 GET /app.js
  HEADERS stream=7 GET /logo.png

Server responds (any order):
  DATA stream=3 (style.css body)
  DATA stream=5 (app.js body)
  DATA stream=7 (logo.png body)
  DATA stream=1 (big.txt body)  ← Still slow, but doesn't block others
```

---

## 3.6 A Common Bug (Inline Request Handling)

### The Mistake

```python
# What I wrote first
for event in conn.receive_data(data):
    if isinstance(event, RequestReceived):
        self.serve(event.stream_id, ...)  # Blocks here!
```

**Result**: Requests processed sequentially despite multiplexing
```
stream 1 /big.txt?delay=2     2005.6 ms
stream 3 /style.css           2005.7 ms  ← Still waiting!
stream 5 /app.js              2005.7 ms  ← Still waiting!
...
```

Same as HTTP/1.1 numbers = defeated multiplexing

### The Fix

```python
# Thread per stream
threading.Thread(target=self.safe_serve,
    args=(event.stream_id, ...),
    daemon=True).start()
```

**Result**: True multiplexing
```
stream 3 /style.css     4.9 ms
stream 7 /logo.png      5.7 ms
stream 9 /icon.png      6.9 ms
stream 5 /app.js        6.9 ms
stream 11 /hero.png     7.8 ms
stream 1 /big.txt      2005.9 ms
```

**Lesson**: You will see this pattern again:
- Worker pool + database connection (blocked by lock)
- Blocking call inside coroutine (defeats async)
- gRPC handler holding global mutex (serializes parallel work)
- Goroutines waiting on single channel (no concurrency)

Protocol gives permission. You serialize the work yourself.

---

## 3.7 Server Push's Death

### What the RFC Says

**RFC 7540 (May 2015)**: Still standard
**RFC 9113 (Jun 2022)**: Still standard

Search for "deprecat" in RFC 9113: Only two hits (PRIORITY and h2c Upgrade)
**Not server push.**

### What Implementers Did

**Chrome 106 (Sep 2022)**: Removed server push
```
1.25% of HTTP/2 sites used it
Later: 0.7%

Reason: "no clear net performance gain,
         and in many cases, regressions"
```

### The Fundamental Problem

Server doesn't know what's in your cache.

```
Server: "I think you'll want style.css"
Server pushes: style.css (100 KB)

But you already have it in cache from yesterday!
Result:
  - 100 KB wasted bandwidth
  - Competes with other requests on same connection
  - Congestion window shared (slower download of what you need)
  - Nothing better than not sending it at all
```

### The Replacement: 103 Early Hints (RFC 8297)

```
Instead of pushing: HTTP/1.1 103 Early Hints
Link: </style.css>; rel=preload; as=style

Server says: "You'll want this"
Client checks: "Do I have it cached?"
Client decides: "I need it" or "I have it"
```

**Key principle**: When one side has knowledge and the other has state
- Inform (103 Early Hints) instead of act (push)
- Let decision-maker (client) decide

---

## 3.8 HTTP/2's One Unsolvable Problem

### Head-of-Line Blocking in TCP

```
RFC 9114 §1.1:
"Because multiplexing is not visible to TCP's loss recovery,
 a lost or reordered packet causes all active transactions
 to experience a stall regardless of whether that
 transaction was directly impacted."
```

**The measurement**:
```
Stall one stream at byte 3000 for 300 ms
(packet holding stream 1 data is lost)

Through the stall:
  /style.css  4.7 ms  ← Fast (no data behind gap)
  
Behind the gap (even though they don't need the lost data):
  /app.js    306.3 ms  ← Stalled waiting for TCP ordering
  /logo.png  306.4 ms
  /hero.png  308.9 ms

Different run = different set of blocked streams
(depending on which requests have buffered data behind the gap)
```

### Why It Happens

TCP: Ordered byte stream
```
Packet with bytes 3000-4000 lost
Kernel won't deliver bytes 4000+ until 3000+ arrive
Even though later streams don't need bytes 3000-4000
```

HTTP/2 can't fix this (TCP limitation)
HTTP/3 (over QUIC) can fix it (streams independent)

---

## 3.9 QUIC & HTTP/3: A New Transport

### Why UDP?

**The obvious answer**: Take protocol number 253, build proper transport (like SCTP)

**Why it fails**:
```
SCTP = standardized 2000
But: Every NAT, firewall, CGNAT, corporate proxy, hotel router
     drops what it doesn't recognize

Result: SCTP works internally; useless on public internet
```

**Why UDP**:
```
UDP = already exists everywhere
But: It's not a good foundation
It's just a hole that already exists
```

### Encryption: Not Just Privacy

```
RFC 8999 §7:
"Middleboxes observe traits of a version
 and assume other versions with similar traits
 have the same semantics"

Result: Anything readable becomes dependency
        Then you can never change it

Example: TCP options became unusable
         (middleboxes depended on them)
```

**QUIC's solution**: Encrypt packet numbers and most headers
- Privacy: yes
- Changeability: yes (middleboxes can't read it, can't depend on it)
- Userspace: yes (changes ship with app, not kernel)

---

## 3.10 QUIC Handshake: 1 RTT vs 2 RTT

### TCP + TLS 1.3 + HTTP/2 (Cold connection)

```
SYN → (client hello inside)
← SYN/ACK (ALPN "h2" negotiated)
ACK → (TLS Finished)
       Client data goes here
       
3 RTT before first GET sent
+ server processing
= 456.6 ms for GET response (3.0 RTT measured)
```

### QUIC + HTTP/3 (Cold connection, 1-RTT)

```
Initial packet → QUIC CRYPTO frame (TLS ClientHello inside)
← Handshake packet (TLS ServerHello inside)
Client data → TLS Finished + GET
← HTTP/3 response

2 RTT before response
= 319.8 ms (2.1 RTT measured)

No transport handshake THEN crypto handshake
One handshake, both happen together
```

### 0-RTT: The Tradeoff

**Measured**:
```
TCP + TLS 1.3 + h2 (new conn):   456.6 ms (3.0 RTT)
QUIC + h3 (1-RTT):                319.8 ms (2.1 RTT)
QUIC + h3 (0-RTT, resuming):      161.7 ms (1.1 RTT)
```

**The Price**: Replay vulnerability
```
RFC 9001 §4.6:
"TLS early data comes with exposure to replay attack
...these protections are imperfect"

Reason: Single-use ticket cache
        Server farm has many servers
        Attacker sends same early data to different server
        Both process it (replay)
```

**The Rule**: 0-RTT only for idempotent requests
```
GET:  Safe (gets same result twice)
HEAD: Safe
POST: NOT SAFE (might charge twice)

Cloudflare rule:
  Only GET and HEAD allowed
  Set Early-Data header
  Client can refuse with 425 Too Early
```

---

## 3.11 Connection IDs: Mobility

### TCP's Problem

Connection = (src IP, src port, dst IP, dst port)

```
Walk out of coffee shop
  wifi → LTE
  Your IP changes
  ↓
  Every TCP connection dies
  
Same with NAT rebind (after idle):
  Your external port changes
  ↓
  Every TCP connection dies
  
Video buffers, download restarts, websocket reconnects
```

### QUIC's Solution

```
QUIC Connection ID (§5.1):
"Primary function: ensure changes in addressing
 at lower layers (UDP, IP) don't cause packets
 to be delivered to wrong endpoint"

New address, same connection ID
Path validated (proof-of-return)
Connection continues
```

**Abuse prevention**:
```
Don't reuse same ID (trackable identifier)
Endpoints issue pool of IDs
Rotate IDs
External observer can't correlate connections over time
```

**Principle**: Identity belongs at layer that owns semantics
```
TCP conflated addressing (IP:port) with identity
→ Inherited all mobility problems

QUIC separated them
→ Can change address, keep identity
```

---

## 3.12 QPACK: Headers Without HoL Blocking

### HPACK's Problem (RFC 9204)

```
HPACK dynamic table is shared mutable state
"Field number 67" only means something
if you've already processed every insertion
that made 67 mean that

On TCP: Total ordering (free)
On QUIC: Out-of-order delivery (problem!)

Stream 12 tries to reference dynamic entry 67
But entry 67 not inserted yet (stream 8 delayed)
Result: Stall stream 12
```

### QPACK's Solution

Take mutable state off request streams:

```
Encoder stream (0x02):
  Encoder → Decoder: table insertions

Decoder stream (0x03):
  Decoder → Encoder: "I've seen these"

Encoder only references entries it knows are safe
```

Default settings:
```
QPACK_BLOCKED_STREAMS: 0 (can't block)
QPACK_MAX_TABLE_CAPACITY: 0 (no dynamic table)
Static table: 99 entries (vs HPACK's 61)
```

**Lesson**: Shared mutable state + out-of-order delivery don't mix
Relax ordering guarantee → find what was depending on it

