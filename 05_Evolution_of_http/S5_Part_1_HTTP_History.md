# Part 1: HTTP History - Evolution from 1.0 to 3

## 1.1 HTTP/1.0 (RFC 1945, May 1996)

### The Basic Principle

One request per connection. After server sends response, connection closes.

```
Client                              Server
  |                                   |
  |-------- TCP Connect --------------|
  |                                   |
  |---- GET / HTTP/1.0 Header --------|
  |                                   |
  |<------- HTTP/1.0 Response --------|
  |                                   |
  |-------- TCP FIN (Close) ----------|
```

### Protocol in One Slide

**Methods**: GET, HEAD, POST, PUT, DELETE, LINK, UNLINK (7 methods)
**Status codes**: 200, 201, 301, 302, 304, 400, 401, 403, 404, 500, 501, 502, 503
**Headers**: Allow, Authorization, Content-Length, Content-Type, Date, Expires, From, If-Modified-Since, Last-Modified, Location, Pragma, Referer, Server, User-Agent, WWW-Authenticate

**Key limitation**: No Host header (one IP = one website)

### The Massive Problem: No Connection Persistence

**24-object page, 200ms RTT**:
```
24 TCP handshakes × 200ms = 4.8 seconds
24 requests/responses × 200ms = 4.8 seconds
Total: 9.6 seconds

Plus: 24 separate congestion windows (each starts from scratch)
```

**Why it fails**:
```python
# First request
s.sendall(b"GET /style.css HTTP/1.0\r\n\r\n")
r1 = recv_until_eof(s)  # Waits for FIN (server closes)

# Second request on same socket
s.sendall(b"GET /app.js HTTP/1.0\r\n\r\n")
r2 = s.recv(4096)  # Returns empty bytes!
# Connection was already closed after first response
```

**The ask in HTTP/1.0**: "Connection: keep-alive" (non-standard extension)
- Some servers honored it
- Some ignored it
- Some crashed
- No guarantee

### Caching: Clock-Based, Not Identity-Based

```
GET request 1:
  Last-Modified: Fri, 04 Sep 2026 07:11:14 GMT

GET request 2 (with cache):
  If-Modified-Since: Fri, 04 Sep 2026 07:11:14 GMT
  
Response:
  HTTP/1.0 304 Not Modified (body removed, saves 202,000 bytes)
```

**Three problems with timestamp-based caching**:

1. **No sub-second precision**: Two writes in one second look identical
2. **Clock drift**: Your clock ≠ server clock ≠ proxy clock
3. **mtime is not identity**: Rebuilding file changes mtime but not bytes

**Result**: Cache validation was weak, timestamp-dependent, unreliable

### No Host Header

```
In 1996: ~1 billion websites
Without Host: One IP address per website
Would need 1/3 of all IPv4 addresses just for HTTP

RFC 1945 §3.2 status codes:
  200 OK
  201 Created
  202 Accepted
  204 No Content
  300 Multiple Choices
  301 Moved Permanently
  302 Moved Temporarily
  304 Not Modified
  400 Bad Request
  401 Unauthorized
  403 Forbidden
  404 Not Found
  500 Internal Server Error
  501 Not Implemented
  502 Bad Gateway
  503 Service Unavailable
```

---

## 1.2 Early HTTP/1.1 (RFC 2068, January 1997)

### The Fundamental Flip: Persistence Default

**HTTP/1.0**: Close connection (default), ask for keep-alive (maybe works)
**HTTP/1.1**: Keep connection alive (default), ask to close if needed

```nginx
Connection: close  # in HTTP/1.1, means "this one time, close it"
```

**Why this matters**:
```
HTTP/1.0 server: Did nothing = connections close
HTTP/1.1 server: Did nothing = connections stay open
Every "do nothing" implementation got the fast path
```

**Result**:
```
Three responses, one TCP handshake
GET / HTTP/1.1
  → 200 OK (connection stays open)
GET /style.css HTTP/1.1
  → 200 OK (connection stays open)
GET /app.js HTTP/1.1
  → 200 OK (connection closes only if requested)
```

### One Header Solves One IP = Many Sites Problem

**Host Header** (RFC 2068 §14.23):

```
GET / HTTP/1.1
Host: site-a.local
→ Returns <h1>site-a</h1>

GET / HTTP/1.1
Host: site-b.local
→ Returns <h1>site-b</h1>

Same IP, same port, same socket
```

**The pattern appears four times in 30 years**:

| Layer | Problem | Solution |
|-------|---------|----------|
| HTTP/1.0 | Four-tuple is address; one IP = one site | Host: header (in message) |
| TLS | Host encrypted; cert chosen first | SNI in ClientHello (in clear) |
| HTTP/2 | Headers compressed; unordered | :authority pseudo-header |
| Everywhere | Many logical destinations, one connection | Topic, routing key, host rule |

**The fundamental pattern**: When you can't use the transport layer's address, put the name in the message itself.

### ETag: Fingerprint, Not Clock

**Fingerprint approach**:
```
HEAD /big.txt HTTP/1.1
Host: site-a.local
→ ETag: "55274ac22c651b90"  (SHA256 of bytes, first 16 hex)

GET /big.txt HTTP/1.1
If-None-Match: "55274ac22c651b90"
→ HTTP/1.1 304 Not Modified (if bytes unchanged)
```

**Why better than Last-Modified**:
- Identity-based: Same bytes = same ETag (even if rebuilt)
- No clock drift: Computed, not stored
- Sub-second precision: Whole content hash

**Weak vs Strong ETags**:
```
W/"…"  (weak) = semantically equivalent, not byte-for-byte identical
       Used when exact match not needed (e.g., compression differs)

"…"    (strong) = byte-for-byte identical
       Required for Range requests
```

**If-Match**: Optimistic concurrency for writes
```
PUT /resource
If-Match: "old-etag"
→ Succeeds only if current ETag matches
→ Detects lost updates from concurrent changes
```

### Accept-* Headers and Vary

**Content negotiation**:
```
Accept-Encoding: identity
→ Content-Length: 202000

Accept-Encoding: gzip
→ Content-Length: 5763 (2.8% of original)

Accept-Encoding: deflate
→ Content-Length: 5751
```

**The breakthrough**: Text compresses. The issue was never "HTTP is text"; it was "headers weren't compressed" (yet).

**Vary Header** (cache-key instruction):
```
Vary: Accept-Encoding
  → Correct: Cache stores separate copies for identity/gzip/deflate

Vary: User-Agent
  → Wrong: Millions of keys, hit rate → 0

Vary: *
  → Caching off entirely
```

**Lesson**: Vary tells caches "this URL has multiple answers" and what creates the variation.

### Range Requests (RFC 2068 §14.35)

**One header enables three use cases**:

```
Range: bytes=100-199
→ HTTP/1.1 206 Partial Content
→ Content-Range: bytes 100-199/202000
→ Content-Length: 100
```

**Video scrubbing**:
```
Player: "I need bytes around 00:45 timestamp (offset 1000000)"
Range: bytes=1000000-1001000
→ Send just that chunk, not whole file
→ User scrubs, server doesn't re-encode
```

**Resumable downloads**:
```
Download died at 60% (600MB of 1GB)
Resume:
Range: bytes=600000000-
→ Continue from byte 600M, not restart
```

**Data lake queries** (Parquet, ZIP):
```
Directory is at END of file
Read last 1KB
→ Find column offsets
Range: bytes=<col_offset>-<col_end>
→ Fetch only columns needed
```

**416 Status Code** (added in RFC 2616):
```
Range: bytes=999999-
  → File is 202000 bytes (total file is smaller than you think)
  → HTTP/1.1 416 Range Not Satisfiable
  → Content-Range: bytes */202000
```

Separates "your syntax is wrong" from "that file is smaller than requested".

### Chunked Encoding (RFC 2068 §3.6.1)

**Problem**: Send body without knowing its length beforehand

```
HTTP/1.1 200 OK
Content-Type: text/css
Transfer-Encoding: chunked
(no Content-Length)

37
body{font-family:monospace;background:#111;color:#eee}
0
```

**How it works**:
- `37` = chunk size in hex (0x37 = 55 bytes)
- Body (55 bytes)
- `0` = end-of-stream marker (0 bytes)

**Pattern**: Same as FastCGI records (Session 3)
- Length-prefixed (efficient buffering)
- Delimited by empty chunk (protocol clarity)

**Modern use cases**:
- Server-sent events (SSE)
- Streaming JSON
- gRPC trailers
- Real-time logging

---

## 1.3 HTTP/1.1 Today (RFC 2616 → RFC 7230-7235 → RFC 9110-9114)

### More Methods Added

**PUT, DELETE**: Write and remove operations
```
PUT /resource
DELETE /resource

→ REST API foundations
```

**OPTIONS**: Ask what a server supports
```
OPTIONS /resource
→ Every CORS preflight request
```

**TRACE**: Echo request back (disabled everywhere, security issue)

### More Status Codes

```
303 See Other (redirect with GET)
305 Use Proxy
307 Temporary Redirect (keep method)
400+ client errors expanded
500+ server errors expanded
```

**Why 307 exists** (deployed reality beats spec):

RFC 2068 said: 302 Found keeps the method
```
POST /form
→ 302 redirect
In theory: client re-POSTs to new location
In practice: All browsers turned POST into GET
```

RFC 2616 couldn't fix browsers, so it:
- Renamed 302 to "Found"
- Wrote down what implementations do
- Added 307 Temporary Redirect for people who meant original 302

**Lesson**: It's easier to add a code than fix a billion clients.

### Cache-Control Vocabulary

Replaced simple Expires with expressive headers:

```
Cache-Control: max-age=3600        # Expires in 1 hour
Cache-Control: s-maxage=7200       # CDN cache 2 hours (overrides max-age)
Cache-Control: no-cache            # Revalidate before use (not same as no-store!)
Cache-Control: no-store            # Don't write to cache at all
Cache-Control: public              # Anyone can cache
Cache-Control: private             # Only client can cache (not CDN)
Cache-Control: immutable           # Never changes (forever)
```

**Common mistake**: no-cache ≠ no-store
- `no-cache`: Cache it, but revalidate before serving (validation required)
- `no-store`: Don't cache it at all (safest for secrets)

---

## 1.4 RFC 7230-7235 (June 2014): One Document Became Six

**Why the split**: One large RFC with many stakeholders → separate RFCs by topic

| RFC | Title | For Whom |
|-----|-------|----------|
| 7230 | Message Syntax and Routing | Proxies, load balancers, CDNs |
| 7231 | Semantics and Content | Application frameworks (methods, status codes) |
| 7232 | Conditional Requests | Browsers, caches, object stores (ETags) |
| 7233 | Range Requests | Video players, download managers, data loaders |
| 7234 | Caching | Every CDN on earth |
| 7235 | Authentication | WWW-Authenticate / Authorization |

**Same pattern as microservices**: Large monolith → separate services with clear ownership, versioned independently.

**Result**: Caching changes don't require re-ratifying GET definition.

---

## 1.5 RFC 9110-9114 (June 2022): Semantics vs Encoding

**The key insight**: HTTP semantics (what it means) are independent of encoding (how you write it)

| RFC | What It Is | Shared Across Versions? |
|-----|-----------|------------------------|
| 9110 | HTTP Semantics (methods, status, headers, ranges, auth) | Yes - shared by 1.1, 2, 3 |
| 9111 | HTTP Caching | Yes - shared by all three |
| 9112 | HTTP/1.1 Wire Format | No - 1.1 specific |
| 9113 | HTTP/2 Wire Format | No - 2 specific |
| 9114 | HTTP/3 Wire Format | No - 3 specific |

**Meaning**: GET means the same thing in all three versions. The bytes are different, but the semantics are identical.

**Implication**: You can upgrade from 1.1 to 2 to 3 and your application code doesn't change.

---

## 1.6 Token Character Set (Why Your JWT is Base64)

**RFC 7230 §3.2.6**: What characters are allowed in an Authorization header?

```
tchar = "!" / "#" / "$" / "%" / "&" / "'" / "*" / "+" / "-" / "."
      / "^" / "_" / "`" / "|" / "~" / DIGIT / ALPHA

EXCLUDED: " ( ) , / : ; < = > ? @ [ \ ] { }
```

**JWT must survive**:
- Authorization header (tchar rules apply)
- URL query string (?query=value)
- Cookie (different rules)
- Form field (application/x-www-form-urlencoded)
- JSON body (almost unrestricted)

**The intersection** of all these alphabets ≈ 64 characters = base64url

Why base64url specifically:
```
Standard base64: Uses + and /
URL problems: + means space in URLs, / is path separator
Solution: Use - and _ instead (base64url)
```

**Lesson**: Every layer you pass through has an alphabet. Design for the most restrictive one.

---

## 1.7 Summary: HTTP/1.0 → 1.1 Evolution

| Problem | HTTP/1.0 | HTTP/1.1 | How |
|---------|----------|----------|-----|
| **Persistence** | No (close after response) | Yes (default) | Connection: keep-alive → default behavior |
| **Virtual hosts** | No (one IP = one site) | Yes (Host header) | One header in message |
| **Caching** | Weak (timestamp-based) | Strong (ETag + fingerprint) | SHA256 instead of clock |
| **Partial content** | No | Yes (Range:) | Enables video scrubbing, resumable downloads |
| **Streaming bodies** | No | Yes (chunked) | Send without knowing length |
| **Methods** | 3 (GET, HEAD, POST, etc) | 7+ (PUT, DELETE, OPTIONS, etc) | REST APIs possible |
| **Status codes** | 13 | 30+ | Richer error information |
| **Header vocabulary** | 16 fixed | Infinite (Cache-Control, Accept-*) | Negotiation and caching |

**The real payoff**: Multiple requests on same connection, faster page loads.

