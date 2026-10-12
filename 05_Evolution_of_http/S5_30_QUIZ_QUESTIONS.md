# Session 5: HTTP Evolution - 30 Quiz Questions

---

## PART 1: HTTP/1.0 FUNDAMENTALS (Q1-8)

### Q1: The 24-Object Page Problem

**Question**: A web page has 24 objects (HTML, CSS, JS, images). Using HTTP/1.0 over a network with 200ms RTT, calculate the minimum time to fully load the page. Show your work.

**Answer**: 
- Each object = 1 TCP handshake (1 RTT) + request/response (1 RTT) = 2 RTT
- 24 objects × 2 RTT × 200ms = 24 × 2 × 200 = 9,600 ms = **9.6 seconds**
- Plus: 24 separate congestion windows (each starts from slow start)
- Implication: This was unacceptable by mid-1990s; motivates HTTP/1.1

---

### Q2: No Host Header = One IP, One Website

**Question**: In 1996, without the Host header, how many IPv4 addresses would be needed to serve 1.1 billion websites?

**Answer**: 
- Without Host header: 1 IP address = 1 website
- 1.1 billion websites = 1.1 billion IP addresses
- Total IPv4 addresses: 2^32 = 4.3 billion
- Percentage consumed: 1.1B / 4.3B = ~25% of all IPv4 just for HTTP
- **Reality**: ~1/3 of all IPv4 would go to single-site servers (wasteful)
- **Solution**: Host header (RFC 2068, 1997) made the problem tractable

---

### Q3: Last-Modified Caching Problems

**Question**: List three problems with timestamp-based cache validation (Last-Modified / If-Modified-Since).

**Answer**: 
1. **No sub-second precision**: Two file writes in the same second look identical
   - Timestamp = Fri 12:00:00, Fri 12:00:00 (can't distinguish)
   - Cache returns stale copy

2. **Clock drift**: Your clock ≠ server clock ≠ proxy clock
   - Multiple parties disagree on "is it fresh?"
   - Spec must legislate for disagreement

3. **mtime ≠ content identity**: Rebuilding file changes mtime, not bytes
   - Same content, different timestamp
   - Cache thinks it's new; client redownloads identical file

---

### Q4: Connection Behavior in HTTP/1.0

**Question**: In HTTP/1.0, after sending the first request and receiving the response, the client tries to reuse the same TCP socket for a second request. What happens?

**Answer**: 
```python
s.sendall(b"GET /style.css HTTP/1.0\r\n\r\n")
r1 = recv_until_eof(s)  # Waits for server FIN

s.sendall(b"GET /app.js HTTP/1.0\r\n\r\n")
r2 = s.recv(4096)  # Returns b"" (empty)
```

- Server closes connection after sending response (per RFC 1945 §1.3)
- Socket is already closed (FIN received)
- Second send succeeds (data written to closed socket)
- Second recv returns empty (EOF = connection closed)
- Client gets no data; thinks connection is dead (must re-open)

---

### Q5: Keep-Alive in HTTP/1.0

**Question**: HTTP/1.0 had a "Connection: keep-alive" extension. Why was it unreliable?

**Answer**: 
- Non-standard extension (not in RFC 1945)
- Different implementations:
  - Some servers honored it ✓
  - Some servers ignored it ✗
  - Some servers crashed on it ✗
- No interoperability guarantee
- Documented in RFC 2068 §19.7.1 as compatibility note, not core feature
- Result: Developers couldn't rely on it; didn't use it
- This motivated HTTP/1.1's design: make persistence the default

---

### Q6: ETag vs Last-Modified

**Question**: Compare ETag-based validation to Last-Modified-based validation. Which is stronger? Why?

**Answer**: 

| Aspect | Last-Modified | ETag |
|--------|---------------|------|
| **What it is** | Timestamp | Content hash (SHA256) |
| **Precision** | 1 second | Perfect (full content) |
| **Identity** | No (mtime changes without content change) | Yes (same content = same ETag) |
| **Clock dependency** | Yes (vulnerable to drift) | No (computed) |
| **Validity check** | Is `now - mtime < TTL`? | Does hash match? |

**Stronger**: **ETag** (identity-based, not time-based)
- Handles rapid updates (sub-second)
- Immune to clock drift
- Distinguishes "rebuilt vs changed"

**Why both exist**:
- Last-Modified: Easy to compute, lightweight
- ETag: More accurate validation

---

### Q7: Range Requests - Three Use Cases

**Question**: Describe three real-world use cases for HTTP Range requests (RFC 2068 §14.35).

**Answer**: 

1. **Video Scrubbing**:
   - User clicks to 45-second mark in 2-hour video
   - Player calculates byte offset (0:45 ≈ offset 50MB)
   - Requests: Range: bytes=50000000-50001000
   - Server sends just that 1KB chunk
   - Player doesn't re-encode or resend whole video

2. **Resumable Downloads**:
   - Download 1GB file, dies at 60% (600MB received)
   - Restart with: Range: bytes=600000000-
   - Server continues from byte 600M
   - No need to resend 600MB; only 400MB remains

3. **Data Lake Queries** (Parquet, ZIP):
   - Directory/index is at END of file (last 1KB)
   - Read footer: Range: bytes=-1024
   - Parse footer to find column offsets
   - Read only columns needed: Range: bytes=1000000-1005000
   - Result: One file, fetch only relevant parts

---

### Q8: Chunked Encoding

**Question**: Why does HTTP/1.1 need chunked encoding (Transfer-Encoding: chunked)? When would you use it instead of Content-Length?

**Answer**: 
**When Content-Length can't be used**:
- Response body generated on-the-fly (streaming)
- Don't know total size beforehand
- Size determined during generation (compression, filters)

**Example**:
```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Transfer-Encoding: chunked

(no Content-Length)

55
event: message
data: {"type": "update", ...}

0  ← End-of-stream marker
```

**Pattern**: Same as FastCGI (Session 3)
- Each chunk: length-prefix (hex) + data + CRLF
- Empty chunk (0 bytes) signals end-of-stream
- Allows framing without knowing total size
- Modern use: Server-Sent Events (SSE), streaming JSON, gRPC trailers

---

## PART 2: HTTP/1.1 PROBLEMS (Q9-16)

### Q9: Head-of-Line Blocking Measurements

**Question**: A 6-asset page loads with one asset taking 2 seconds, others instant. Compare wall-clock time for:
1. HTTP/1.1 pipelined (one connection)
2. HTTP/1.1 keepalive (one connection, no pipelining)
3. Six separate connections

**Answer**: 

| Scenario | Wall Time | Why |
|----------|-----------|-----|
| Pipelined (1 conn, all sent) | ~2003ms | All responses ordered; must wait for slow one |
| Keepalive (1 conn, sequential) | ~985ms | Slow request gets its own round trip; others fast |
| Six connections (parallel) | ~600ms | All requests in parallel; slow doesn't block others |

**Best theoretical** (pipelined, no HoL blocking):
- Send all requests at t=0
- Get all responses out-of-order
- Wall time = slowest individual response (~2000ms)
- But HTTP/1.1 can't do this (order is the identifier)

---

### Q10: Request Smuggling Attack

**Question**: Explain how the following request can be interpreted as TWO requests by an origin server, even though the CDN reads it as ONE.

```
POST /echo HTTP/1.1
Host: site-a.local
Content-Length: 6
Transfer-Encoding: chunked

0
GET /admin HTTP/1.1
Host: site-a.local
```

**Answer**: 

**CDN reads (using Content-Length)**:
```
POST /echo
Body = next 6 bytes: "0\r\n\r\nG"
Complete after reading 6 bytes
Result: 1 request (body is "0\r\n\r\nG")
```

**Origin reads (using Transfer-Encoding)**:
```
Transfer-Encoding: chunked
Chunk size line: "0" (0 bytes = end of stream)
CRLF after "0"
Next request starts: "GET /admin HTTP/1.1"
Result: 2 requests
  1. POST /echo (0 bytes body)
  2. GET /admin (never sent by client!)
```

**The attack**:
- CDN forwards to origin
- Origin sees GET /admin (request CDN never validated)
- Origin responds to GET /admin
- Response sits in connection buffer
- Next client on same connection gets wrong response

**HTTP/2 prevents this**: Frame header has fixed-size length, no ambiguity

---

### Q11: Header Bloat Calculation

**Question**: One realistic HTTP/1.1 request uses ~805 bytes of headers. A page loads 80 assets, all from same domain, all with same headers.

Calculate:
1. Total header bytes sent
2. Unique header bytes (new information)
3. Repeated header bytes
4. Percentage repeated

**Answer**: 

| Item | Calculation | Result |
|------|-------------|--------|
| **Total headers** | 80 × 805 | 64,320 bytes |
| **Unique (paths)** | /path1, /path2, ... /path80 | ~1,600 bytes (2.5%) |
| **Repeated** | 64,320 - 1,600 | 62,720 bytes (97.5%) |

**Impact**:
- 1 Mbit uplink = 1 megabit per second
- 64,320 bytes = 514,560 bits ÷ 1M bits/s = **0.51 seconds**
- User watches spinner for 0.5 seconds before first byte of app data

---

### Q12: Postel's Law vs Request Smuggling

**Question**: RFC 2616 (1999) said: "Be liberal in what you accept. If both Transfer-Encoding and Content-Length, ignore the latter."

RFC 9112 (2022) says: "May reject or use Transfer-Encoding. Either way, close the connection."

Why did the rule change?

**Answer**: 

**1999**: Good engineering between two programs
```
Program A (lenient) + Program B (lenient) 
= they agree on interpretation
= safe
```

**2022**: Chain of 5 programs
```
Client → CDN → Load Balancer → Reverse Proxy → Origin

Two programs being lenient ≠ safe
Example: CDN uses Content-Length, Origin uses Transfer-Encoding
Result: Request smuggling attack (see Q10)
```

**New rule**:
1. Reject (safest)
2. Or process Transfer-Encoding only
3. Either way, close connection (prevent exploitation)

**Lesson**: Lenient parsing works for two parties, breaks chains

---

### Q13: Connection Limit Evolution

**Question**: Trace the evolution of "how many connections per origin":

1. What did RFC 2068 recommend?
2. What did browsers actually ship?
3. How did websites work around it?
4. What happened to the RFC?

**Answer**: 

1. **RFC 2068 (1997)**: "SHOULD NOT maintain more than 2 connections"
2. **Browsers (by 2008)**: Shipped 6 connections per origin
3. **Websites workaround**: Domain sharding to get 18
   - img1.example.com → 6 connections
   - img2.example.com → 6 connections
   - img3.example.com → 6 connections
   - Total: 18 (same server, different domains)
4. **RFC 7230 (2014)**: Deleted the sentence entirely
   - Spec conceded to deployed reality
   - Can't force billions of browsers to change

**Lesson**: Specification is conversation with deployed world, not declaration

---

### Q14: Nagle + Delayed ACK Collision

**Question**: On an HTTP/1.1 persistent connection, why does the second request have ~40ms latency when sending:
```python
write(header)
write(body)
```

But not when sending:
```python
write(header + body)
```

**Answer**: 

**Separate writes**:
```
write(header)
  → TCP sends immediately (header is data, not small segment)

write(body)
  → Nagle holds it (small segment, previous unacked? no)
  
Wait... ACK from client doesn't come immediately
  → Delayed ACK (RFC 1122): wait 40ms to piggyback

Server: waiting for ACK
Client: delayed ACK waiting for data to piggyback
  
Result: 40ms stall per request
```

**One write**:
```
write(header + body)
  → TCP combines, sends as one segment
  → No Nagle delay (one segment)
  → No delayed ACK issue (enough data to send)
  → Immediate response
```

**Why only persistent connections**:
- HTTP/1.0: close() forces flush
- HTTP/1.1: keepalive, no forced flush

**Real impact** (loopback measurement):
```
Separate:  0.9 + 41.5 + 44 + 43.9 + 44 = 174.3 ms
Combined:  3.2 ms
Difference: 54× slower for same requests!
```

**Fix**: Both nginx and Apache set TCP_NODELAY

---

### Q15: Request Smuggling Fix in HTTP/2

**Question**: HTTP/2's frame header makes request smuggling impossible. Explain why.

**Answer**: 

**HTTP/1.1 ambiguity**: Multiple interpretations of one byte stream
```
Content-Length: 6 → Read 6 bytes
Transfer-Encoding: chunked → Parse chunks (different result)
```

**HTTP/2 frame header**: No ambiguity
```
[Length: 24 bits (explicit)] [Type: 8 bits] [Flags: 8 bits] 
[Stream ID: 31 bits]
```

**Why it fixes smuggling**:
1. Length is in fixed place (bytes 0-2)
2. Length is fixed size (24 bits)
3. Type is explicit (DATA vs HEADERS vs other)
4. No second opinion (can't interpret differently)

**Result**: Only one way to read frame
- CDN and origin interpret identically
- Smuggling becomes unrepresentable

---

### Q16: The Bill for HTTP/1.1

**Question**: For each problem, name the measurement and the fix (HTTP/2 or HTTP/3).

| Problem | Measured | Fixed By |
|---------|----------|----------|
| Head-of-line blocking | ? | ? |
| Header bloat | ? | ? |
| Too many connections | ? | ? |
| Ambiguous framing | ? | ? |
| TCP round trips | ? | ? |

**Answer**: 

| Problem | Measured | Fixed By |
|---------|----------|----------|
| Head-of-line blocking | 2003ms vs 3ms (same file, pipelined vs parallel) | HTTP/2 stream IDs |
| Header bloat | 97.5% of upload is repeats | HTTP/2 HPACK compression |
| Too many connections | 6 per origin (RFC said 2, ignored) | HTTP/2 multiplexing (one connection) |
| Ambiguous framing | One byte stream, two interpretations (smuggling) | HTTP/2 frame headers (explicit length) |
| TCP round trips | 3 RTT before first byte (handshake + TLS) | HTTP/3 QUIC (2 RTT, 1-RTT) |
| TCP head-of-line blocking | One lost packet stalls all streams | HTTP/3 QUIC streams (independent) |

---

## PART 3: HTTP/2 & HTTP/3 (Q17-24)

### Q17: HTTP/2 Frame Header Explained

**Question**: Break down the 9-byte HTTP/2 frame header:
```
00 00 2a 04 00 00 00 00 00
```

Identify: Length, Type, Flags, Reserved, Stream ID

**Answer**: 

```
[Length]      [Type][Flags]     [R][Stream ID]
00 00 2a      04    00          00 00 00 00 00
```

Parsing:
- **Length** (24 bits): 0x00002a = 42 bytes
- **Type** (8 bits): 0x04 = SETTINGS
- **Flags** (8 bits): 0x00 = no flags
- **Reserved** (1 bit): 0
- **Stream ID** (31 bits): 0x00000000 = stream 0 (connection-level)

**Meaning**: SETTINGS frame (type 4), 42 bytes, on stream 0 (connection control)

---

### Q18: Stream ID Allocation

**Question**: In HTTP/2, stream IDs are allocated how?

- Client-initiated: ?
- Server-initiated: ?
- Connection-level: ?

Who needs coordination to avoid collisions?

**Answer**: 

- **Client-initiated**: ODD (1, 3, 5, 7, ...)
- **Server-initiated**: EVEN (2, 4, 6, 8, ...)
- **Connection-level**: 0 (SETTINGS, PING, GOAWAY, etc)

**Coordination needed**: **NONE**
- Each side has separate namespace
- Client always sends odd, server always sends even
- No negotiation, no race condition

**Benefit**: Decentralized allocation (scalable, no bottleneck)

---

### Q19: HPACK Compression Stages

**Question**: A second request to the same server includes these headers:
```
:method: GET
Host: example.com
User-Agent: Firefox
Cookie: session=abc123
```

Show how HPACK compresses them (on the second request):

**Answer**: 

1. **:method: GET**
   - Static table, index 2
   - Send: 0x82 (one byte)
   - Cost: **1 byte**

2. **Host: example.com**
   - First request: Host and value added to dynamic table at index 62
   - Second request: Lookup finds it
   - Send: 0xbf (one byte for index 62)
   - Cost: **1 byte**

3. **User-Agent: Firefox**
   - Previously seen, added to dynamic table
   - Send: index (one byte)
   - Cost: **1 byte**

4. **Cookie: session=abc123**
   - Previous value used; added to table
   - Send: index (one byte)
   - Cost: **1 byte**

**Total second request**:
- Headers in text: ~174 bytes
- HPACK compressed: **6 bytes** (4 indices)
- Reduction: **97%**

---

### Q20: CRIME Attack & HPACK Defense

**Question**: Explain the CRIME attack. How does HPACK defend against it?

**Answer**: 

**CRIME Attack** (Compression Ratio Info-leak Made Easy):
```
Attacker controls part of request (URL query)
Attacker can observe HTTP response size

GET /?guess=a HTTP/1.1
Cookie: session=SECRET...
→ Compressed size: 412 bytes (no match)

GET /?guess=S HTTP/1.1
Cookie: session=SECRET...
→ Compressed size: 411 bytes (found "S"!)

Attacker: "Correct! Secret starts with S"
Repeat per character → Recover entire secret
```

**HPACK Defense** (structural, not algorithmic):
1. **Fixed Huffman table**
   - Built from corpus, published in Appendix B
   - Never adapts to current data
   - Attacker text and secret never share encoding

2. **Exact-match index only**
   - Dynamic table stores [name: value] pairs
   - Guessing prefix of secret wins nothing
   - Only full-string matches get indexed

3. **Never-indexed flag**
   - Mark sensitive headers (authorization, set-cookie)
   - RFC 7541 §7.1: "never indexed"
   - These don't enter dynamic table

**Result**: No shared adaptive dictionary between attacker and secret

---

### Q21: Multiplexing: 400× Faster

**Question**: Same 6-asset page, 2-second delay on one asset.
- HTTP/1.1 pipelined: All blocked by slowest
- HTTP/2 multiplexed: Streams independent

Show wall times and calculate speedup.

**Answer**: 

**HTTP/1.1 Pipelined**:
```
/style.css   2003.6 ms  ← waiting for slow one
/app.js      2003.8 ms  ← waiting
/logo.png    2004.1 ms  ← waiting
/icon.png    2004.2 ms  ← waiting
/hero.png    2004.4 ms  ← waiting
/big.txt     2003.4 ms  (actually delayed 2 seconds)

Average: 2003.8 ms
```

**HTTP/2 Multiplexed**:
```
stream 3  /style.css   4.9 ms   ← instant
stream 7  /logo.png    5.7 ms   ← instant
stream 9  /icon.png    6.9 ms   ← instant
stream 5  /app.js      6.9 ms   ← instant
stream 11 /hero.png    7.8 ms   ← instant
stream 1  /big.txt   2005.9 ms  ← just this one

Average: 410 ms
```

**Speedup**: 2003.8 / 410 = **4.88× → approximately 400×** (or 5×)

---

### Q22: Server Push's Failure

**Question**: RFC 9113 (June 2022) says server push is "still standard". Yet Chrome removed it (Sep 2022). Explain the paradox.

**Answer**: 

**Still in RFC**:
- RFC 7540 (2015): Server push included
- RFC 9113 (2022): Server push retained (not deprecated)
- RFC 9114 (2022): Server push retained for HTTP/3

**Actually dead** (0.7% usage by 2024):

**The fundamental problem**:
```
Server doesn't know client's cache
Server: "I'll send style.css"
Server pushes: style.css (100 KB)

But client already has it from yesterday!
Result: 100 KB wasted, competes on congestion window
```

**Why not deprecated**:
```
Hard to deprecate backward-compat
Simpler to just remove quietly in implementations
RFC kept it "for compatibility", but nobody uses it
```

**The replacement** (RFC 8297, 103 Early Hints):
```
Instead: HTTP/1.1 103 Early Hints
Link: </style.css>; rel=preload

Server says: "You'll want this"
Client checks cache: "Do I have it?"
Client decides: "I need it" or "I have it"
```

**Principle**: Inform (let client decide), don't act (don't assume)

---

### Q23: HTTP/2 Bug I Hit First

**Question**: Building an HTTP/2 server, you handle incoming requests inline:

```python
for event in conn.receive_data(data):
    if isinstance(event, RequestReceived):
        self.serve(event.stream_id, ...)  # Blocks here!
```

What happens?

**Answer**: 

**Symptom**:
```
stream 1 /big.txt?delay=2   2005.6 ms
stream 3 /style.css         2005.7 ms  ← Should be instant!
stream 5 /app.js            2005.7 ms  ← Should be instant!
...
```

Same as HTTP/1.1 times!

**Why**:
```
Process stream 1 request
  self.serve(1, ...) blocks waiting for backend (2 seconds)
While stream 1 blocks, stream 3 waits in queue
When stream 1 finally completes, stream 3 begins
Result: Sequential processing = defeats multiplexing
```

**The fix**:
```python
# Thread per stream
threading.Thread(target=self.safe_serve,
    args=(event.stream_id, ...),
    daemon=True).start()
```

Result: True multiplexing (all threads running, responses come back immediately)

**Lesson**: You'll see this pattern everywhere:
- Worker pool holding database lock
- Blocking call inside async/await
- gRPC handler holding global mutex
- Goroutines waiting on single channel
- Transport gives permission, but you serialize yourself

---

### Q24: QUIC Head-of-Line Blocking Fix

**Question**: One stream loses a packet (300ms delay). Compare TCP vs QUIC.

**TCP (HTTP/2)**:
- Streams that lost data: ???
- Streams that didn't: ???
- Different per run: ???

**QUIC (HTTP/3)**:
- Streams that lost data: ???
- Streams that didn't: ???

**Answer**: 

**TCP (HTTP/2)**:
```
Run 1:
  /style.css  4.7 ms  (before gap)
  /app.js    306.3 ms ← stalled (data behind gap)
  /logo.png  306.4 ms ← stalled
  /hero.png  308.9 ms ← stalled
  
Run 2:
  /style.css  4.0 ms
  /icon.png   5.2 ms
  /logo.png  308.2 ms ← now stalled
  /big.txt   308.3 ms ← now stalled
  
Different set each run (depends on which had bytes behind gap)
```

**QUIC (HTTP/3)**:
```
18 datagrams really deleted (5% loss)

Delayed stream:
  /big.txt   78.2 ms  ← lost data, took time

Unaffected streams:
  /style.css  4.5 ms
  /app.js     5.4 ms
  /logo.png   6.7 ms
  /icon.png   7.8 ms
  /hero.png  11.0 ms
  
ONLY the stream that lost data delays
Others proceed immediately
```

**Why the difference**:
- TCP: One ordered byte stream; gap blocks everything behind it
- QUIC: Each stream independent; only affected stream delays

---

## PART 4: ADOPTION & PATTERNS (Q25-30)

### Q25: RFC Split Pattern

**Question**: RFC 2616 (HTTP/1.1) was a single monolithic document. RFC 2016 split it into 6 documents (RFC 7230-7235). What was the reason?

**Answer**: 

**Problem with monolithic RFC**:
- Caching experts, routing experts, auth experts, all in one document
- Caching change requires re-ratifying entire spec
- Everyone has to re-read the whole thing
- Different audiences have different needs

**Solution (microservices pattern)**:
```
RFC 7230: Routing (for proxies, CDNs, load balancers)
RFC 7231: Semantics (for app frameworks, GET/POST/status codes)
RFC 7232: Conditional Requests (for browsers, caches)
RFC 7233: Range Requests (for video, downloads)
RFC 7234: Caching (for CDNs)
RFC 7235: Authentication (for WWW-Authenticate)
```

**Benefit**:
- Caching update doesn't require re-ratifying GET
- Each group owns their spec
- Independent versioning

**Cost**:
- Fragmented (people still say "2616" meaning HTTP/1.1)
- Must read multiple documents

**Same year**: Microservices became buzzword (same concept, different scale)

---

### Q26: HTTP Semantics vs Encoding

**Question**: RFC 9110 vs RFC 9112/9113/9114. What's the difference? Why does it matter?

**Answer**: 

**RFC 9110**: HTTP Semantics (what HTTP means)
```
Methods: GET, POST, PUT, DELETE, ...
Status codes: 200, 404, 500, ...
Headers: Cache-Control, Authorization, Accept-*
Ranges, ETags, caching rules
Version-independent
Shared by HTTP/1.1, HTTP/2, HTTP/3
```

**RFC 9112/9113/9114**: Wire Format (how to write it)
```
RFC 9112: HTTP/1.1 text framing
RFC 9113: HTTP/2 binary frames, stream IDs
RFC 9114: HTTP/3 QUIC frames
Version-specific
Different encoding, same semantics
```

**Why it matters**:
```
Upgrade from 1.1 → 2 → 3
Application code doesn't change
GET is GET in all three
Middleware can speak different versions
```

**Without this seam**:
```
New wire format = rewrite entire application
E.g., would have needed new GET, new 200, new headers
```

**Lesson**: Every long-lived system needs semantics-encoding seam

---

### Q27: Deployed Reality Beats Specification - 302 Lost

**Question**: RFC 2068 (1997) defined 302 Found to "keep the method". 
RFC 2616 (1999) added 307 Temporary Redirect.

Why?

**Answer**: 

**RFC 2068 intention**:
```
POST /form
→ 302 Redirect
→ Client should POST to /result
```

**Browser reality** (all browsers):
```
POST /form
→ 302 Redirect
→ Browser turns POST into GET (wrong!)
```

**RFC 2616 options**:
1. Enforce specification (no)
2. Fix a billion browsers (impossible)
3. Add new code for intended behavior (yes)

**Solution**:
```
Renamed 302 to "Found" (documented existing behavior)
Added 307 Temporary Redirect (for people who meant original 302)

HTTP/1.1 306 Temporary Redirect
= "Really keep the method, I promise"
```

**Lesson**: Specification is conversation with deployed world, not declaration

---

### Q28: 418 I'm a Teapot

**Question**: Status 418 appears in RFC 9110 as "reserved forever". What's the story?

**Answer**: 

**Origin**:
- RFC 2324 (April 1, 1998): April Fool's joke
- "I'm a teapot. Short and stout. Here is my handle, here is my spout."
- Humorous HTTP status code for tea pots

**Evolution**:
```
1998: RFC published as joke
2000s: Too many people implemented as easter egg
2010s: Widely deployed as easter egg
2022: RFC 9110 §15.5.19:
  "Has been widely implemented as easter egg,
   and therefore is effectively consumed by this use.
   Reserved forever."
```

**Why reserved forever**:
```
Can't delete (breaks easter eggs)
Can't reuse (too many dependencies)
Only solution: Reserve it
```

**Lesson**: Deployed reality wins
Joke that became standard by accident

---

### Q29: QUIC on UDP - The Only Bad Choice

**Question**: Why does QUIC run on UDP instead of using a better protocol like SCTP?

**Answer**: 

**The obvious answer**:
```
UDP not good foundation
Invent proper transport (SCTP, 2000)
```

**Why it fails**:
```
SCTP: Good protocol, RFC standardized
Problem: Every NAT, firewall, CGNAT, corporate proxy, hotel router
         drops what it doesn't recognize
         
Result: SCTP works on internal networks
        Completely unusable on public internet
```

**The tradeoff**:
```
UDP not good foundation (too minimal)
But: It's the hole that already exists
     Permitted everywhere
     
QUIC on UDP = not ideal, but only option
```

**Why encryption**:
```
RFC 8999 §7:
"Middleboxes depend on traits they can observe"

Anything readable → becomes dependency
→ Can't change it

Example: TCP options became unchangeable
         (middleboxes depended on them)

QUIC solution: Encrypt headers
→ Middleboxes can't read
→ Can't depend
→ Can change
```

**Userspace advantage**:
```
TCP: Kernel, updates every decade
QUIC: Userspace, updates with app
```

---

### Q30: Zero Common

**Question**: HTTP/3 with 0-RTT resumption saves 295ms. What's the tradeoff?

**Answer**: 

**Measurement**:
```
TCP + TLS 1.3 + HTTP/2 (new):    456.6 ms (3.0 RTT)
QUIC + HTTP/3 (1-RTT):           319.8 ms (2.1 RTT)
QUIC + HTTP/3 (0-RTT, resumed):  161.7 ms (1.1 RTT)

Savings: 295 ms
```

**What is 0-RTT?**:
```
TLS resumption with early data
Client sends request in first flight
No waiting for server response before sending
Saves 1 RTT
```

**The tradeoff** (RFC 9001 §4.6):
```
"Exposure to replay attack
...these protections are imperfect"

Why imperfect:
  - Defense is single-use ticket cache
  - Server farm has N servers
  - Attacker sends same early data to different servers
  - Both process it (replay)
```

**The rule**:
```
Only for idempotent requests (no side effects)
GET: Safe (same result twice)
HEAD: Safe
POST: NOT SAFE (might charge card twice)

Cloudflare rule:
  Only GET and HEAD
  Set Early-Data header
  Client can refuse with 425 Too Early
```

**Trade-off analysis**:
```
Value: 295ms saved
Cost: Possible replay if request has side effects
Risk management: Only use for reads
```

---

## Answer Key Summary

| Q# | Topic | Key Concept |
|:--:|-------|-------------|
| 1 | HTTP/1.0 | 24 objects × 2 RTT × 200ms = 9.6s |
| 2 | No Host | ~1/3 of IPv4 wasted |
| 3 | Last-Modified | No precision, clock drift, mtime ≠ identity |
| 4 | Connection close | Server closes after response; socket dead |
| 5 | Keep-alive | Non-standard, unreliable (some crash) |
| 6 | ETag vs LM | ETag stronger (identity vs time) |
| 7 | Range | Video scrubbing, resumable downloads, data lake |
| 8 | Chunked | Stream without knowing length |
| 9 | HoL blocking | 2003ms pipelined vs 600ms parallel |
| 10 | Smuggling | One stream, two interpretations |
| 11 | Header bloat | 97.5% repeats; 0.51s upload on 1Mbit |
| 12 | Postel's law | Two programs safe; 5-program chain dangerous |
| 13 | Connections | RFC "2" → browsers "6" → RFC deleted |
| 14 | Nagle + ACK | 40ms delay; 54× slower |
| 15 | Smuggling fix | Frame header explicit; no ambiguity |
| 16 | The bill | HoL, bloat, connections, framing, RTTs |
| 17 | Frame header | Length[24] Type[8] Flags[8] R[1] StreamID[31] |
| 18 | Stream IDs | ODD=client, EVEN=server, 0=connection |
| 19 | HPACK | Static table → Dynamic table → Huffman |
| 20 | CRIME | Fixed Huffman, exact-match, never-indexed |
| 21 | Multiplexing | 2003ms → 410ms = 5× (or ~400×) |
| 22 | Push dead | Problem: doesn't know cache (duplicates) |
| 23 | My bug | Inline handling = sequential = no multiplexing |
| 24 | QUIC HoL | Only affected stream delays; others fly |
| 25 | RFC split | Monolith → 6 docs per audience |
| 26 | Semantics split | RFC 9110 (meaning) vs 9112/9113/9114 (encoding) |
| 27 | 302 lost | All browsers made it GET → RFC added 307 |
| 28 | 418 Teapot | Easter egg → reserved forever |
| 29 | QUIC UDP | SCTP blocked; UDP only option |
| 30 | 0-RTT | 295ms saved; replay risk (idempotent only) |

Good luck! 🚀
