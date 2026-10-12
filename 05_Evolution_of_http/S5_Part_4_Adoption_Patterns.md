# Part 4: HTTP Protocol Adoption, Design Patterns & Key Takeaways

## 4.1 Discovery and Fallback (HTTP/3)

### How to Find HTTP/3 Support

| Mechanism | RFC | Date | How It Works | Cost |
|-----------|-----|------|-------------|------|
| **ALPN** | 7301 | Jul 2014 | Protocol inside TLS handshake ("h3") | Free (in existing handshake) |
| **Alt-Svc** | 7838 | Apr 2016 | Response header: `h3=":443"` | One full TCP+TLS connection |
| **HTTPS DNS RR** | 9460 | Nov 2023 | Record type 65 carries ALPN in DNS | Free (already doing lookup) |

### 3-5% Still Block UDP

```
RFC 9308 §2: Measurement studies show
  3–5% of networks block all UDP traffic
  
Why: Corporate firewall, carrier policy
Cost: These users get TCP (automatic fallback)
Risk: Fallback path is downgrade attack
```

**Google statistics**:
```
95.3% of clients can use QUIC
4.4% blocked by UDP or packet-size issues
0.3% other issues
```

### Downgrade Attacks

```
Any protocol with fallback = downgrade attack by construction

Example:
  Try h3 (UDP/QUIC)
  → Network blocks it
  → Fall back to h2 (TCP)
  
Attacker blocks all UDP traffic
  Your user downgrades
  Attacker can now intercept TCP (in some networks)
  
Only question: what fallback costs you
```

---

## 4.2 Current Adoption (2024-2026)

### By Request Volume

```
HTTP Archive Web Almanac 2024:
  HTTP/1.1:  ~15%
  HTTP/2:    ~70%
  HTTP/3:    ~15%
  
"By request" = every actual GET/POST
```

### By Homepage

```
HTTP Archive crawls homepages:
  HTTP/1.1:  21–22%
  HTTP/2:    70–71%
  HTTP/3:    7–9%
  
Real distinction: Homepages hit new paths
Different resources might use different versions
```

### W3Techs Numbers (Suspicious)

```
By website:
  HTTP/2:    34.6%
  HTTP/3:    40.3%
  
Problem: H/3 > H/2 means categories aren't mutually exclusive
Likely: H/3 stats include servers that support BOTH 2 and 3
Treat with suspicion
```

### The Tail: 15% Still HTTP/1.1 in 2026

**Eleven years after HTTP/2 shipped**

Why:
```
Internal services (corporate, no upgrade incentive)
Embedded devices (firmware update cycle = years)
Legacy load balancers (nobody wants to touch)
APIs behind gateways (intermediate proxies)
Old services (never migrated, still work)
```

**Real world**: No cutover. Very long tail.
Most engineering happens at version boundary, not inside one.

---

## 4.3 Design Patterns: The Recurring Shapes

### Pattern 1: Multiplexing Needs Identity

**Everywhere**:
```
TCP:        Port numbers (ephemeral, on handshake)
SS7/TCAP:   Transaction ID (in every message)
FastCGI:    Request ID (in header)
HTTP/1.1:   Order (implied, no field)
HTTP/2:     Stream ID (31 bits, every frame)
HTTP/3:     Stream ID (31 bits, every frame)
```

**The principle**:
```
If client must wait before sending next message
Check: Did you leave the identifier out?

Missing ID → client must queue by order → ordering mandatory
→ head-of-line blocking → next problem
```

### Pattern 2: Every Fix Is the Next Problem

```
HTTP/1.0:
  Problem: No persistence
  Fix: Keep-alive, persist connection
  
HTTP/1.1:
  Problem: One request per round trip (slow page loads)
  Solution: Pipelining (all requests at once)
  → Unintended consequence: head-of-line blocking
  
HTTP/2:
  Problem: Head-of-line blocking in HTTP
  Solution: Stream IDs, multiplexing
  → Unintended consequence: TCP head-of-line blocking visible
  
HTTP/3 (QUIC):
  Problem: TCP head-of-line blocking
  Solution: Stream IDs in transport
  → Unintended consequence: HPACK broke (shared mutable state)
  
QPACK:
  Problem: Mutable state + out-of-order delivery
  Solution: Separate encoder/decoder streams
  → No unintended consequence yet (too new)
```

**Insight**: There is no final version. Only sequence of trades.

Knowing which trade you're standing on is the skill.

---

## 4.4 Semantics vs Encoding

### The Seam That Matters

**RFC 9110-9114 (June 2022)**: The split that made versions independent

```
RFC 9110: HTTP Semantics
  Methods (GET, POST, PUT, DELETE)
  Status codes (200, 404, 500)
  Headers (Accept-*, Cache-Control)
  Ranges, ETags, authentication
  
  NOT version-specific
  Shared by HTTP/1.1, 2, and 3
  GET means same thing in all three
  
RFC 9111: HTTP Caching
  Shared by all versions
  Same cache key logic, same rules
  
RFC 9112: HTTP/1.1 Wire Format
  Text-based framing
  Version-specific ONLY
  
RFC 9113: HTTP/2 Wire Format
  Binary frames with stream IDs
  Version-specific ONLY
  
RFC 9114: HTTP/3 Wire Format
  QUIC-based framing
  Version-specific ONLY
```

### The Implication

```
You can upgrade from 1.1 → 2 → 3
Application code doesn't change

GET is GET in all three
Server can transparently upgrade without app knowing
Middleware can speak different versions to client and origin
```

### Every Long-Lived System Needs This Seam

```
Without it:
  New encoding = rewrite semantics
  
With it:
  New encoding = just another adapter
  Semantics stay stable
```

---

## 4.5 Deployed Reality Beats Specification

### 302 Lost to Browsers

**RFC 2068 (1997)**: 302 Found keeps the method
```
POST /form
→ 302 Redirect to /result
→ Client should POST to /result
```

**Reality** (every browser):
```
POST /form
→ 302 Redirect
→ Client turns POST into GET
→ Browsers all did this
```

**RFC 2616 couldn't fix browsers**, so:
- Renamed 302 to "Found"
- Wrote down what implementations do
- Added 307 Temporary Redirect for people who meant original 302

**Lesson**: It's easier to add a code than fix a billion clients.

### Connection Limit (2 vs 6)

**RFC 2068**: "SHOULD NOT maintain more than 2 connections"
**Browsers** (by 2008): Ship 6 per origin
**Websites**: Domain sharding to get 18
**RFC 7230 (2014)**: Deleted the sentence entirely
**Spec conceded** to deployed reality

### 418 I'm a Teapot (April Fool's)

```
RFC 2324 (April 1, 1998): Status 418

"I'm a teapot. Short and stout.
 Here is my handle, here is my spout."

Joke → Easter egg → Widely implemented
→ RFC 9110 §15.5.19:
  "Has been widely implemented as easter egg,
   and therefore is effectively consumed by this use.
   Reserved forever."

Not because useful. Because too many shipped.
```

### Server Push: Never Deprecated, Completely Dead

```
Still in RFC 9113 (2022)
Still in RFC 9114 (2022)

But Chrome removed it (106, Sep 2022)
And measurement shows: 0.7% of sites use it

Reason: Doesn't know what's cached (pushes duplicates)

Why RFC didn't deprecate:
  Too hard to deprecate backward-compat
  Better to just remove quietly in implementations
```

### QUIC Runs on UDP (Because Middleboxes Have a Veto)

```
Obviously, should invent new protocol (SCTP, 2000)
But: Middleboxes drop what they don't know

Solution: UDP (already allowed everywhere)
Cost: Not a good foundation
But: Only hole that exists

Lesson: Middleboxes have veto power
       Can't deploy what they block
       Must use what they allow
```

---

## 4.6 Four Big Ideas

### Idea 1: Multiplexing Needs Identity

When a client must wait before sending the next message, check whether you left the identifier out.

You've now seen this in:
- TCP ports (distinguish connections)
- SS7 transaction IDs (distinguish calls)
- FastCGI request IDs (distinguish requests)
- HTTP/2 stream IDs (distinguish streams)
- HTTP/3 stream IDs (distinguish streams)

Missing ID → order becomes the only identifier → ordering mandatory

---

### Idea 2: Every Fix Is the Next Problem

Persistence → Pipelining → Head-of-line blocking
HTTP/2 fixes → TCP head-of-line blocking visible
QUIC fixes → HPACK broken → QPACK fixes

No final version. Sequence of trades.

Know which one you're standing on.

---

### Idea 3: Semantics and Encoding Differ

RFC 9110 is what HTTP means.
RFC 9112, 9113, 9114 are three ways of writing it down.

GET hasn't changed since 1996.
Wire format has changed three times.

Every long-lived system needs this seam.
Without it, new encoding means rewriting your system.

---

### Idea 4: Deployed Reality Beats Specification

Browsers ignored 302 semantics → RFC added 307
Browsers used 6 connections → RFC deleted "SHOULD NOT"
Easter egg implemented → RFC reserved 418 forever
Push never deployed → RFC never deprecated
UDP blocked by middleboxes → Use UDP anyway (best bad choice)

Specification is conversation with deployed world, not declaration.

---

## 4.7 What You Will Build

### Assignment 1: HTTP/1.1 Calculator

```python
# Your server, your socket
s = socket.create_connection(("localhost", 8080))

# One socket, many requests
GET /add?a=2&b=3 → 200 5
GET /sub?a=10&b=4 → 200 6
GET /mul?a=6&b=7 → 200 42
GET /div?a=9&b=3 → 200 3
GET /div?a=1&b=0 → 400
GET /add?a=x&b=3 → 400
GET /pow?a=2&b=8 → 404
POST /add → 405
GET /add (no Host) → 400

assert socket.still_open: True
# One TCP handshake, 6 responses
```

**The hard part**: Consuming exactly Content-Length bytes, not one more
(byte n+1 belongs to next request)

### Assignment 2: Binary Protocol (HTTP/2-like)

```
Track 1: Your server
$ ./bserve ./www 9000
  Read binary request frame
  Map path to file
  Send frame with status + headers + bytes
  Keep connection open

Track 2: Your client
$ ./bcurl -v localhost:9000/index.html
  Build binary request frame
  Read response frame
  Hexdump (if -v)
  Exit non-zero on 4xx/5xx
  Never open second connection

The bit in the middle: You pick frame format
  (HTTP/2 chose 24/8/8/31 bytes)
```

**What you hand in**:
1. Two-page spec
2. Your program
3. Annotated hexdump of one request/response
4. "If you can't annotate your own bytes, spec isn't finished"

---

## 4.8 Measurement Realities

### What's Actually Slow

```
Text-based: Blame it gets is undeserved
Measured: gzip at 2.8% of original
Reality: Headers (repeated 97.5%) not text

Headers alone: 805 bytes per request
80 requests: 62KB of repeats, 1.6KB unique
```

### What Helps

| Solution | Problem | Measured Gain |
|----------|---------|--------------|
| Keep-alive | 1.0 connection vs 6 | 50% faster wall time |
| Pipelining | Head-of-line vs order-free | 300ms vs 2000ms (6× faster) |
| HTTP/2 multiplexing | Blocked clients vs flowing | 4.9ms vs 2005ms (400× faster) |
| QUIC connection ID | Network change restarts vs continues | Connection survives mobility |
| 0-RTT resumption | 2 RTT vs 1 RTT | 295ms saved at scale |

### The Wall-Time Benchmark

Six assets, 150ms RTT:

```
HTTP/1.0 (close):               1,369 ms
HTTP/1.1 (keepalive, 1 conn):     985 ms
Parallel 2 (spec says):           607 ms
Parallel 6 (browsers):            608 ms
Pipelined (best, nobody ships):   303 ms
HTTP/2 (multiplexed):           ~600 ms (same as parallel)
HTTP/3 (QUIC):                  ~400 ms (saved TCP RTTs)
```

The "pipelined" row shows the opportunity HTTP/1.1 could have had if clients sent all requests at once and servers handled them in parallel.

HTTP/2 achieved this with stream IDs.

---

## 4.9 Sessions 5-8 Context

This material (HTTP evolution) is context-setting for:

```
Session 6: Where did the state go?
  Sessions, sticky routing
  Stateless servers
  TLS termination
  Shared caches
  Connection pools
  
Session 7: CDNs (ab)use
  Caching strategies
  Cache hierarchy
  Purge semantics
  
Session 8: Streaming video at large scale
  DASH / HLS
  Bitrate adaptation
  Segment caching
  
Session 9-12: Scaling patterns
```

---

## 4.10 Key Historical Dates

| Date | Event | Why It Matters |
|------|-------|----------------|
| May 1996 | HTTP/1.0 (RFC 1945) | One request per connection |
| Jan 1997 | HTTP/1.1 (RFC 2068) | Persistence default; Host header |
| Jun 1999 | HTTP/1.1 finalized (RFC 2616) | ETag, Range, chunked encoding |
| Nov 2009 | SPDY announced | "55% faster" in real world |
| Feb 2015 | HTTP/2 (RFC 7540) | Multiplexing, HPACK, frame IDs |
| Nov 2023 | HTTPS DNS RR (RFC 9460) | H/3 discovery without TLS |
| Jun 2022 | HTTP/3 (RFC 9114) | QUIC transport, connection IDs |
| Today | 15% HTTP/1.1, 70% H/2, 15% H/3 | Long tail, no cutover |

---

## 4.11 The One Sentence Per Version

```
HTTP/1.0 (1996):
  "Request, response, close"
  
HTTP/1.1 (1997):
  "Persistence, persistence, persistence
   (but head-of-line blocking for it)"
   
HTTP/2 (2015):
  "Multiplexing via stream IDs
   (but TCP still ordered)"
   
HTTP/3 (2022):
  "True multiplexing via QUIC
   (replacing TCP's ordered delivery)"
```

Each version solved the previous version's problem and created new constraints to solve later.

