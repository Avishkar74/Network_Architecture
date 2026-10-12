# Part 2: HTTP/1.1 Problems & The Cost of Design Choices

## 2.1 Head-of-Line Blocking

### The Problem Demonstrated

**Scenario**: 6 asset page with 150ms RTT. One file has 2-second delay.

**HTTP/1.1 Pipelined** (all requests sent together, one connection):
```
GET /style.css
GET /app.js
GET /logo.png
GET /icon.png
GET /hero.png
GET /big.txt?delay=2.0

Results:
/style.css  2003.6 ms  ← Should be instant, but waiting
/app.js     2003.8 ms  ← Should be instant, but waiting
/logo.png   2004.1 ms  ← Should be instant, but waiting
/icon.png   2004.2 ms  ← Should be instant, but waiting
/hero.png   2004.4 ms  ← Should be instant, but waiting
/big.txt    2003.4 ms  ← Actually delayed 2 seconds

EVERY response is delayed by the slowest one
```

**Why?**: Order is the only identifier. Responses must arrive in request order.

**TCP with one connection per request** (no pipelining):
```
/big.txt?delay=2.0  2006.0 ms  ← Waits 2 seconds
/style.css          3.2 ms     ← Served immediately!
/app.js             5.7 ms     ← Served immediately!
/logo.png           6.1 ms     ← Served immediately!
/icon.png           6.9 ms     ← Served immediately!
/hero.png           7.2 ms     ← Served immediately!

Only the slow request is slow. Others are instant.
```

**Pipelining makes it worse!** (one connection is shared, must wait for order)

### Root Cause: No Request Identifier

```c
// HTTP/1.1 response
HTTP/1.1 200 OK
Content-Type: text/html
Content-Length: 500

...body...

// Question: Which request is this answering?
// Answer: The one we're counting on
```

**Client knows only because it counted**:
```python
requests_sent = 0
for response in connection:
    request_number = requests_sent++
    process(response, request_number)
```

**Order becomes mandatory** because order is the only identifier.

### Other Protocols Did It Right

| Protocol | Has ID? | Where | Example |
|----------|---------|-------|---------|
| **TCP** | Yes | port numbers (SYN sequence) | Session 2 |
| **SS7/TCAP** | Yes | transaction id in every message | SMS, call setup |
| **FastCGI** | Yes | requestId in record header | nginx → php-fpm (Session 3) |
| **HTTP/1.1** | No | (implied by order) | ← The problem |
| **HTTP/2** | Yes | 31-bit stream id in frame | ← The fix |
| **HTTP/3** | Yes | 31-bit stream id in frame | ← The fix |

---

## 2.2 Header Bloat and Compression

### The Math

**Single request, typical headers**:
```
GET /path HTTP/1.1
Host: example.com
User-Agent: Mozilla/5.0 (X11; Linux x86_64) ...
Accept: text/html,application/xhtml+xml,...
Accept-Encoding: gzip, deflate, br
Accept-Language: en-US,en;q=0.9
Sec-Fetch-Dest: document
Sec-Fetch-Mode: navigate
Sec-Fetch-Site: none
Cookie: session=abc123def456...; tracking=xyz...
...

Total: ~805 bytes just in headers
```

**One page, 80 requests**:
```
80 requests × 805 bytes = 64,320 bytes

New information (paths):
  /path1
  /path2
  /path3
  ...
  /path80
  
Total new bytes: ~1,600 bytes (2.5%)

Repeated bytes (headers):
  Host: example.com (80 times)
  User-Agent (80 times)
  Accept: (80 times)
  Cookies (80 times)
  
Total repeated bytes: ~62,720 bytes (97.5%)
```

**On 1 Mbit uplink**:
```
64,320 bytes at 1 Mbit/s = 0.51 seconds

That's 0.51 seconds of upload before
a single byte of application data
moves, while the user watches.
```

### Why Not Just Gzip?

**The obvious answer**: Compress headers like bodies

```
HTTP/1.1 response with gzip:
Content-Encoding: gzip
Content-Length: 5,763  (original 202,000)
```

**But wait**: Content-Encoding compresses the BODY only.

HTTP/1.1 never had a mechanism to compress headers.

---

## 2.3 Connection Count Limits (RFC 2068 §14.31)

### The Rule

```
"SHOULD NOT maintain more than 2 connections
to any server or proxy"
```

**Browser reality by 2008**:
```
Spec says: 2 connections per origin
Browsers ship: 6 connections per origin
Websites work around it: Domain sharding (18 total)
```

### Why Domain Sharding?

```
example.com        → connection 1, 2, 3, 4, 5, 6
img1.example.com   → connection 7, 8, 9, 10, 11, 12
img2.example.com   → connection 13, 14, 15, 16, 17, 18

Same server! But DNS alias tricks browser
```

**Wall-time measurements** (6 assets, 150ms RTT):

| Mode | Connections | Bytes | Requests | Wall Time |
|------|-------------|-------|----------|-----------|
| HTTP/1.0 (close) | 6 | 4,867 | 12 RTT | 1,369 ms |
| HTTP/1.1 keepalive (1 conn) | 1 | 5,095 | 7 RTT | 985 ms |
| Parallel 2 (RFC says) | 2 | 5,095 | 4 RTT | 607 ms |
| Parallel 6 (browsers) | 6 | 5,095 | 2 RTT | 608 ms |
| Pipelined (1 batch) | 1 | 5,095 | 2 RTT | 303 ms |

**The best row nobody shipped**: Pipelined (one connection, all requests sent together)
- Why? Complex to implement, head-of-line blocking still exists

**RFC 7230 (2014)**: Removed the "SHOULD NOT maintain more than 2" sentence
- The spec conceded to deployed reality
- 6 connections had already won

---

## 2.4 Request Smuggling Attack

### The Setup

One byte stream, two readings, one attack.

```
POST /echo HTTP/1.1
Host: site-a.local
Content-Length: 6
Transfer-Encoding: chunked

0
GET /admin HTTP/1.1
Host: site-a.local
```

**Reading with Content-Length**:
```
Read 6 bytes after headers:
  0\r\n\r\nG

Result: ONE request (body is "0\r\n\r\nG")
```

**Reading with Transfer-Encoding**:
```
Parse chunks:
  0 = chunk size (end of stream)
  After "0", next line is new request

Result: TWO requests
  1. POST /echo (0 bytes body)
  2. GET /admin (never sent by client)
```

### The Attack

Place a CDN that uses Content-Length in front of origin that uses Transfer-Encoding:

```
CDN (uses Content-Length):
  Sees: POST /echo (body 6 bytes)
  Forwards to origin

Origin (uses Transfer-Encoding):
  Sees: POST /echo (body empty)
  Plus: GET /admin (request from nowhere!)
  
Result: Origin processes GET /admin
        Origin sends response to GET /admin
        
CDN sees: Response to POST /echo
          Response to GET /admin (extra response!)
          
Next client routed to same connection:
  Reads extra response meant for /admin
  = client gets data they didn't request
```

**Why HTTP/2 fixed it**:
```
Frame header: [Length (24 bits)] [Type (8 bits)] [Flags (8 bits)] [Stream ID (31 bits)]

Length is in FIXED place, FIXED size, no second opinion.
No "interpret this differently" possible.
```

---

## 2.5 Framing Ambiguity

### Postel's Law (1989)

```
"Be liberal in what you accept and
 conservative in what you send"
```

**RFC 2616 §4.4 (1999)**:
```
"If a message is received with
 both Transfer-Encoding AND Content-Length,
 the latter MUST be ignored."

Recover. Do not reject.
```

This was good engineering in 1999.

**RFC 9112 §6.3 (2022, 23 years later)**:
```
"A server MAY reject a request
 containing both … or process
 in accordance with Transfer-Encoding alone.
 
 Regardless, the server MUST close
 the connection after responding."
```

**Why the change?**

In 1999: Two programs talking to each other
In 2022: Chain of 5 (client → CDN → load balancer → reverse proxy → origin)

One program being liberal, another being liberal = they agree on different interpretations = disaster.

**New rule**: 
- Rejection is now allowed
- Recovery is now optional
- Either way, destroy the connection (prevent exploitation)

---

## 2.6 TCP Nagle + Delayed ACK Bug

### The Algorithms

**Nagle's Algorithm** (RFC 896, 1984):
```
"Do not send a small segment while
 an earlier one is unacknowledged"

Goal: Reduce number of small TCP packets
Cost: Adds latency when sending small chunks
```

**Delayed ACK** (RFC 1122):
```
"Do not acknowledge immediately;
 wait up to 40ms to piggyback ACK"
 
Goal: Reduce ACK overhead
Cost: Adds latency when waiting for piggyback
```

### The Collision

**HTTP/1.1 pipelined, write(header); write(body)**:
```
write(head)
  → Goes out immediately (unacked)

write(body)
  → Nagle holds it (waiting for ACK)

Client side:
  → Receives ACK, nothing to send back

Server side:
  → Delayed ACK waits up to 40ms for data to piggyback on
  → (but waiting for ACK, so no data to send)

Result: 40ms delay for every request after the first!
```

**Measurements** (on loopback, single write vs separate):
```
Separate write(head); write(body):
  /style.css   0.9 ms    (first, no delay)
  /app.js     41.5 ms    ← Delayed ACK
  /logo.png   44.0 ms    ← Delayed ACK
  /icon.png   43.9 ms    ← Delayed ACK
  /hero.png   44.0 ms    ← Delayed ACK
  Total: 174.3 ms

One write (coalesce):
  Total: 3.2 ms
  
Difference: 54× slower for same request!
```

**Why it only appears on persistent connections**:
```
HTTP/1.0 (close): write() triggers close, forces flush
HTTP/1.1 (keep-alive): write() returns, no forced flush
```

### The Fix

```c
TCP_NODELAY = 1  // Disable Nagle's algorithm
```

Both nginx and Apache set this:
```nginx
# In nginx source:
setsockopt(s, IPPROTO_TCP, TCP_NODELAY, ...)
```

**Lesson**: Your protocol sits on a protocol with its own opinions. Know them.

---

## 2.7 Summary: The Bill for HTTP/1.1

| Problem | Measured | Root Cause | Fixed By |
|---------|----------|-----------|----------|
| **Head-of-line blocking** | 2003 ms vs 3 ms for same file | No request identifier; order is ID | HTTP/2 stream IDs |
| **Header bloat** | 97.5% of upload is repeats | Headers never compressed | HTTP/2 HPACK |
| **Too many connections** | 6 per origin, 18 with hacks | RFC said "2", browsers ignored | HTTP/2 multiplexing |
| **Ambiguous framing** | One byte stream, two readings | No fixed-size frame header | HTTP/2 frame headers |
| **TCP round trips** | 3 RTT before first byte | TCP handshake + TLS handshake | HTTP/3 QUIC (2 RTT) |
| **TCP head-of-line** | One lost packet stalls everything | TCP guarantees in-order delivery | HTTP/3 QUIC (stream IDs) |

**What people say**: "HTTP is slow because it's text"
**What we measured**: "Gzip at 2.8%; text is not the problem"
**What was actually slow**: Headers (repeated) + framing (no lengths, no IDs) + TCP (one ordered pipe)

**Insight**: HTTP/2 is not "HTTP but binary"
It's "HTTP but with lengths and IDs"
Binary is the consequence, not the cause.

