# Part 3: Nginx Features - Caching, Routing & Load Balancing

## 3.1 Reverse Proxy: Why Nginx Sits in the Middle

### Forward Proxy vs Reverse Proxy

#### Forward Proxy (Squid, 1996)
```
Client 1 → [Forward Proxy] → Internet
Client 2 → [Forward Proxy] → Internet
Client 3 → [Forward Proxy] → Internet

Sits next to CLIENTS
Caches downloads so others don't download same thing
Protects uplink bandwidth
Client configures the proxy
Client knows the proxy exists
```

**Example**: Corporate proxy on campus network
- Student downloads image
- Proxy caches it
- Next student gets cached version
- Saves bandwidth

#### Reverse Proxy (Nginx)
```
Internet → [Nginx Reverse Proxy] → Backend App Servers
                ├── App Server 1
                ├── App Server 2
                └── App Server 3

Sits next to SERVERS (hence "reverse")
Same caching machinery as forward proxy
PLUS: Route by path/host, distribute load, handle TLS, cache
User doesn't configure it
User usually doesn't know it's there
```

**Example**: Nginx in front of Node.js servers
- Request comes to nginx
- Nginx routes by path or host
- Nginx distributes to backend servers
- User just sees one address

### Nginx's Secret Weapon: Absorbing Slow Clients

```
Your app server is fast: responds in 10ms
But client is on 2G network: 500ms to receive response

Old model: App server blocks waiting for client to receive data
Result: App server tied up for 500ms, can't handle other requests

Nginx model:
  App server: sends response to nginx in 10ms
  Nginx: buffers response
  App server: free to handle next request
  Nginx: slowly drips response to slow client over 500ms
  
Result: App server unblocked, nginx absorbs the slow client
```

This is why reverse proxies are valuable even before caching/routing.

---

## 3.2 Nginx Caching Architecture

### Cache Configuration

```nginx
proxy_cache_path temp/cache levels=1:2 keys_zone=demo:10m
                 max_size=100m inactive=60s use_temp_path=off;
```

Breaking it down:

#### keys_zone=demo:10m
**10 MB of SHARED MEMORY** holding:
- Red-black tree (rbtree) for fast lookup
- LRU queue for eviction tracking
- The INDEX, NOT the data

**Capacity**: Roughly 8,000 keys per megabyte
- Small 10 MB zone can track 80,000 entries
- Actual data lives on disk (much larger)

#### levels=1:2
**Two-level directory structure on disk**

```
temp/cache/
├── a/
│   ├── 1e/  (cache key hash)
│   ├── 2f/
│   └── ...
├── b/
│   ├── 3d/
│   └── ...
└── ...
```

**Why?** Prevents single directory holding millions of files
- Filesystem lookup time O(1) per directory
- No inode overload
- Some filesystems can't handle 1M files in one directory

#### max_size=100m
**Disk size limit**: 100 megabytes total cache

When cache exceeds 100m:
- Cache manager process evicts LRU entries
- Keeps cache under the limit
- Makes room for new entries

#### inactive=60s
**Evict if not READ for 60 seconds** (regardless of TTL)

**Important distinction**:
- `proxy_cache_valid 10s` = Cache is valid for 10 seconds
- `inactive=60s` = Evict if nobody reads it for 60 seconds

**Example**:
```
Cache entry created at time 0
proxy_cache_valid = 10s (expires at time 10)
inactive = 60s

Scenario 1: Entry read at time 5 and time 55
  At time 65: Entry hasn't been read since time 55
  Even though it's still valid: EVICTED
  
Scenario 2: Entry read at time 5, never read again
  At time 65: Entry is evicted despite being valid
```

**Quiz question**: If proxy_cache_valid is 10s and inactive is 60s, which wins?
- Answer: Entry expires at 10s (earlier wins)
- If entry expired: can't be read, triggers revalidation

---

## 3.3 LRU Cache Eviction

### How Nginx Evicts Cache

The actual eviction code (simplified):

```c
q = ngx_queue_last(&cache->sh->queue);  // Get tail of LRU queue
fcn = ngx_queue_data(q, ngx_http_file_cache_node_t, queue);

wait = fcn->expire - now;
if (wait > 0) { 
    break;  // Tail is still fresh, stop evicting
}

if (fcn->count == 0) {  // Nobody is streaming it
    ngx_http_file_cache_delete(cache, q, name);  // Delete it
}
```

### The Eviction Algorithm

1. **Start at tail** of LRU queue (least recently used)
2. **Check if fresh**: Is expire time still in future?
   - If yes: Stop. Everything else is fresher.
   - If no: Continue
3. **Check if in use**: Is anybody streaming this object to a client?
   - If yes: Skip (can't evict while being streamed)
   - If no: Delete it
4. **Repeat** until cache is under limit

### Why count == 0 Matters

```
Object being streamed to a client:
┌─────────────────────────────────────┐
│ Client (slow, on 2G network)        │
│ ↑                                   │
│ │ Streaming (count = 1)             │
│ │                                   │
│ Nginx → Cache object                │
│         (count = 1, in-use)         │
└─────────────────────────────────────┘

If we evict while count > 0:
  Object disappears mid-stream
  Client gets broken response
  
Nginx solution:
  Only evict when count == 0
  Object can be evicted out from under client
  Protects against corrupted responses
```

**LRU queue data structure**: Intrusive doubly-linked list
- Link pointers live inside the node
- No separate allocation for the list
- Moving node to head: just pointer rewrites
- Cache LRU, posted-events lists, half of nginx core use this structure

---

## 3.4 Cache Stampede Prevention

### The Stampede Problem

```
Popular object expires

10ms window where old copy is invalid, new one not yet fetched

10 requests arrive in that 10ms → all are MISSES

All 10 go to origin server simultaneously

Origin server: sudden 10x traffic spike for single object

This is "cache stampede" or "thundering herd"
```

### Solution: proxy_cache_lock

```nginx
proxy_cache_lock on;
```

**How it works**:

```
Object expires

Request 1: Tries to fetch, gets MISS, acquires lock
Request 2: Tries to fetch, LOCKED, waits
Request 3: Tries to fetch, LOCKED, waits
Request 4: Tries to fetch, LOCKED, waits
...
Request 10: Tries to fetch, LOCKED, waits

Request 1: Fetches from origin, stores in cache, releases lock

Requests 2-10: Lock releases, they check cache, get HIT

Result: Only ONE request goes to origin, others wait
```

**Config**:
```nginx
proxy_cache_lock on;
proxy_cache_lock_timeout 10s;  # How long to wait for lock
```

**Default**: OFF (because it adds latency for waiting requests)

**When to enable**: 
- High-traffic popular objects
- Slow origin server
- Preventing origin overload during cache expiry

---

## 3.5 Stale Content Serving

### proxy_cache_use_stale

```nginx
proxy_cache_use_stale error timeout
                     updating 
                     http_500 http_502 http_503 http_504;
```

**Meaning**: Serve stale content when:
- Error contacting origin (network error)
- Timeout waiting for origin
- Origin returns 5xx error
- Object is being updated (background refresh)

### When Stale Content Saves You

```
Scenario: Your origin database is down

Without proxy_cache_use_stale:
  Request arrives
  Cache expired 4 minutes ago
  Try to fetch from origin
  Origin is DOWN
  Return 502 Bad Gateway
  User sees error page

With proxy_cache_use_stale:
  Request arrives
  Cache expired 4 minutes ago
  Try to fetch from origin
  Origin is DOWN
  Return stale copy from 4 minutes ago
  User sees slightly old page
  
Which is better? Obviously the stale page.
At 3am when origin is down, slightly old data is better than error.
```

### Background Refresh with "updating"

```nginx
proxy_cache_use_stale updating;
```

```
Request 1: Arrives, cache expired
  ├── Sends request to origin (background)
  ├── Serves stale copy immediately to request 1
  └── Origin responds, updates cache

Request 2: Arrives while Request 1 is being refreshed
  ├── Sees cache is being updated
  ├── Serves stale copy immediately
  ├── Wait for Request 1's origin response? NO
  └── Gets instant response from stale cache

Result: All requests get instant response while background refresh happens
One request pays the cost (to origin), all others get instant stale response
```

### Debug Header

```nginx
add_header X-Cache-Status $upstream_cache_status;
```

**Test it**:
```bash
$ curl -i localhost:8082/ | grep X-Cache
X-Cache-Status: MISS

$ curl -i localhost:8082/ | grep X-Cache
X-Cache-Status: HIT

$ curl -i localhost:8082/ | grep X-Cache
X-Cache-Status: UPDATING
```

---

## 3.6 Location Matching Precedence

### The Precedence Rules

```nginx
location = /exact { }              # Rule 1: Exact match
location ^~ /images/ { }           # Rule 2: Longest prefix (suppresses regex)
location ~ \.php$ { }              # Rule 3: Regex (FIRST in file order)
location / { }                     # Rule 4: Longest prefix (fallback)
```

### Evaluation Order

1. **Exact match** (`location = /path`)
   - If matches: WINS immediately, search stops
   - Result: /exact → Rule 1

2. **Longest prefix** ALL (`^~` and implicit)
   - Find all prefixes that match
   - Pick the longest one
   - If that prefix has `^~`: WINS, suppress regex search
   - Result: /images/a.php → Rule 2

3. **Regex** (in file order)
   - If longest prefix was `^~`: SKIP THIS
   - Walk regex rules in order they appear in config
   - Return FIRST match
   - Result: /other/a.php → Rule 3

4. **Fallback longest prefix**
   - If no regex matched: use the longest prefix found in step 2
   - Result: /anything → Rule 4

### Common Mistake

```nginx
location ^~ /images/ { }   # Rule A
location ~ \.php$ { }      # Rule B
```

Request: `/images/a.php`

**Wrong guess**: "It's a .php file, so it matches regex (Rule B)"

**Correct answer**: Matches `/images/` prefix first, `^~` suppresses regex, returns Rule A

**Why?** The longest prefix match happened BEFORE the regex check.

### Why ^~ Exists

```nginx
location /api/ {
    proxy_pass http://api_backend;
}

location ~ \.js$ {
    # Some special handling for JS files
}

Request: /api/file.js

Without ^~:
  Matches /api/ (longest prefix)
  Also matches \.js$ (regex)
  File order says JS block comes first
  Goes to JS handler (WRONG!)

With ^~ on /api/:
  Matches /api/ (longest prefix)
  ^~ suppresses regex search
  Goes to /api/ handler (CORRECT)
```

---

## 3.7 Location Matching Performance

### Prefixes vs Regexes

#### Prefixes: Ternary Search Tree

```c
n = (len <= node->len) ? len : node->len;
rc = ngx_filename_cmp(uri, node->name, n);
if (rc != 0) {
    node = (rc < 0) ? node->left : node->right;  // Binary tree decision
    continue;
}
if (len > node->len && node->inclusive) {
    node = node->tree;  // Descend
    uri += n;
    len -= n;
}
```

- Built at config-parse time (not per-request)
- Walked one URI segment at a time
- O(log n) lookup
- 500 prefixes: negligible cost

#### Regexes: Plain Array

```c
for (i = 0; i < rules; i++) {
    if (regex_match(uri, rules[i])) {
        return rules[i];
    }
}
```

- Walked in order every request
- O(n) in worst case
- 500 regexes: noticeably slower

**Lesson**: Data structure IS the documentation
- Prefixes are tree: Longest wins (ternary search)
- Regexes are array: First wins (sequential scan)
- Precedence rules are not trivia, they're inevitable consequences of data structures

---

## 3.8 Sendfile: Zero-Copy Transmission

### The Problem: Four Copies

Without sendfile:

```
read() from disk + write() to socket:

disk →[copy 1]→ page cache →[copy 2]→ your buffer →[copy 3]→ socket buffer →[copy 4]→ NIC
                                      (user space)
```

**Cost**:
- Copy 1: Disk to page cache (DMA, free)
- Copy 2: Page cache to your buffer (64KB chunks, CPU cost)
- Copy 3: Your buffer to socket buffer (CPU cost)
- Copy 4: Socket buffer to NIC (DMA, free)

**Mode switches**: 2 per chunk (user ↔ kernel)

**For 64 MB file**: 2048 syscalls, hours of CPU time copying bytes

### Solution: Sendfile

```c
sendfile(2)  // Linux syscall
```

With sendfile:

```
disk →[copy 1]→ page cache →[copy 2]→ socket buffer →[copy 4]→ NIC
                            (kernel space)
```

**Cost**:
- Copy 1: Disk to page cache (DMA, free)
- Copy 2: Page cache to socket buffer (DMA after Linux 2.4, CPU before)
- Copy 4: Socket buffer to NIC (DMA, free)

**Mode switches**: 0 per chunk (stays in kernel)

**Benefit**: Data never enters your process's address space

---

## 3.9 Why Sendfile Doesn't Solve Everything

### When You CAN'T Use Sendfile

Sendfile copies in kernel. If you need to TOUCH the bytes:
- **gzip**: Compress bytes before sending (can't compress in kernel)
- **TLS**: Encrypt bytes before sending (can't do TLS in kernel)
- **Templating**: Insert dynamic data (can't template in kernel)

### Configuration Conflict

```nginx
sendfile on;
gzip on;
```

These fight! When both are on:
- Nginx sees gzip enabled
- Disables sendfile for that request
- Data must come to user space to compress
- Then sent to client

**Result**: You get one or the other, not both benefits simultaneously

### Honest Performance Truth

On loopback (no real network):
```
read()           : 37.4 ms wall time
mmap()           : 23.3 ms wall time
sendfile()       : 33.2 ms wall time
```

Sendfile doesn't win on loopback! Why?

- No NIC, no DMA benefit
- Kernel memcpy's to receiver's buffer anyway
- Memory bandwidth is bottleneck
- All three approaches hit the same limits
- curl competing for CPU

**But sendfile IS valuable**:
- 2048 syscalls become 1 (system call overhead gone)
- 64 MB never enters process address space (memory bandwidth freed)
- Benefit shows up as headroom under concurrency
- CPU saved copying is CPU available for someone else's request

**Lesson**: Benchmark the bottleneck you actually have, not the operation itself

---

## 3.10 Key Concepts Summary

| Feature | Purpose |
|---------|---------|
| **Reverse Proxy** | Sits between clients and servers; routes, caches, load balances |
| **Absorb Slow Clients** | Nginx buffers response while app server moves on |
| **keys_zone** | Shared memory holding cache index (metadata, not data) |
| **levels=1:2** | Two-level disk directories preventing inode overload |
| **max_size** | Disk limit; eviction triggered when exceeded |
| **inactive** | Evict if not read for X seconds (regardless of TTL) |
| **LRU Eviction** | Least Recently Used queue; tail evicted first |
| **count field** | Reference count preventing in-use objects from being evicted |
| **proxy_cache_lock** | Prevent cache stampede; serialize requests during miss |
| **proxy_cache_use_stale** | Serve old content on origin error or timeout |
| **Location Precedence** | = > ^~ > regex > implicit prefix |
| **^ Prefix** | Ternary tree (O(log n), built at parse time) |
| **Regex** | Array (O(n), walked every request) |
| **Sendfile** | Zero-copy transmission; kernel handles data |
| **sendfile limitation** | Disabled when bytes need to be touched (gzip, TLS) |

---

## 3.11 Summary: Why These Features Matter

Nginx sits in the middle because:
1. **It can handle 10,000 connections** (event loop)
2. **It can cache aggressively** (efficient memory usage)
3. **It can route intelligently** (low-cost lookups)
4. **It can distribute load** (smooth algorithms)
5. **It can absorb slow clients** (your app servers stay fast)

The features are not add-ons; they're natural consequences of the architecture.
