# Revision Short Notes - Nginx & Web Server Architecture

[← Previous](CHEATSHEET.md) | [Next →](30_QUIZ_QUESTIONS.md)


## Part 1: History (Late 1990s - 2002)

**Connection vs Request**
- Connection: Persistent open channel (survives multiple requests)
- Request: Individual data exchange

**Thread-Per-Connection Model**
- 1 user = 1 thread (stays alive for entire connection)
- 10,000 users = 10,000 threads
- 10,000 × 8 MB stack = 80 GB RAM consumed

**Why It Failed**
1. Memory exhaustion: 8 MB per thread
2. CPU context switching: Threads waste CPU switching (99% overhead)
3. Idle waiting: Thread holds memory while waiting for disk/network

**C10K Problem (2002)**
- Concurrent 10,000 connections impossible with thread-per-connection
- Hardware could support it, software couldn't
- File descriptor limit (1024), stack memory (8 MB), CPU limitations

**Apache Tried**
- Prefork (1995): Pre-create process pool
- Worker MPM (1999): Use threads (shared memory)
- Event MPM (2004): Listener thread + worker threads
- All still trying to make per-connection worker cheaper (wrong question)

**Java Solution: Connection Pooling**
- Servlets: Instantiate once, reuse for many requests
- Connection pools: Reuse DB connections
- Core pattern: Amortize expensive setup

---

## Part 2: Nginx Architecture

**Fundamental Shift**
- Old: "How do I make the worker cheaper?"
- Nginx: "Why have a worker per connection at all?"

**Igor Sysoev (2002)**
- Rambler portal falling over under connection volume
- Started nginx to solve C10K
- 2004: First release; 2011: Version 1.0

**Process Model**
```
Master (reads config, spawns workers)
├── Worker 1 (event loop, 10,000 connections)
├── Worker 2 (event loop, 10,000 connections)
├── ... one per CPU core
└── Cache manager + cache loader
```

**Event Loop (99.9% sleeping)**
```c
timer = find_next_timeout();
epoll_wait(timer);           // SLEEP until event
process_ready_events();
```

**Epoll: Kernel Does Watching**
- Interest list: Connections to watch (built once)
- Ready list: Connections with data (built by kernel)
- Worker only processes connections on ready list
- Select is O(n), epoll is O(active_events)

**Stale Event Bug**
- epoll returns batch; processing first event can close connection second event points to
- New client gets recycled file descriptor, gets stale event
- Solution: Generation counter in pointer's low bit
- Check instance/generation matches before processing

**Thread Pools for Slow I/O**
- Slow disk read would block event loop
- Solution: Push to background thread queue
- Background thread talks to disk, main worker continues
- Main worker resumes when data ready

---

## Part 3: Features

**Reverse Proxy**
- Sits between clients and servers (not near clients like forward proxy)
- Routes, caches, load balances
- Secret weapon: Absorbs slow clients (app server responds fast, nginx drips to client)

**Cache Components**
- keys_zone: Shared memory holding index (not data) ~8,000 keys/MB
- levels=1:2: Two directory levels on disk (prevent inode overload)
- max_size: Disk limit; eviction when exceeded
- inactive: Evict if not READ for X seconds (regardless of TTL)

**LRU Eviction**
```c
Check tail of queue
If expired and count==0: Delete
count==0 means nobody streaming it
Prevents in-use objects from being evicted mid-stream
```

**Cache Stampede**
- Problem: Object expires, 10 requests all miss simultaneously
- Solution: proxy_cache_lock on
- One request fetches, others wait for result
- Off by default (adds latency)

**Stale Content**
- proxy_cache_use_stale: Serve old data if origin down
- With updating: Background refresh while serving stale
- X-Cache-Status header: MISS, HIT, UPDATING

**Location Precedence**
```
1. Exact match (=)       → Wins immediately
2. Longest prefix (^~)   → Wins, suppresses regex
3. Regex (~ ~*)          → First match in file order
4. Implicit prefix       → Longest, fallback only
```

**Why ^~ Exists**
- Prefixes are ternary tree (built at config time, O(log n))
- Regexes are array (checked each request, O(n))
- ^~ suppresses expensive regex search

**Sendfile**
- read()+write(): 4 copies + 2 mode switches (CPU cost)
- sendfile(): 2 copies, 0 mode switches (kernel copies to socket buffer)
- Disabled when bytes need touching (gzip, TLS, templating)
- Not faster on loopback; shows up as headroom under concurrency

---

## Part 4: Advanced

**HTTP Parser: Resumable State Machine**
- 27 states for request line alone
- Parses one byte at a time
- Saves state between TCP segments
- No regex, no string functions, handles fragmented data

**Smooth Weighted Round Robin**
- Naive RR bursts requests to single server
- Smooth WRR spreads evenly: a b a a b a (no bursts)
- Effective_weight: Passive health check (gradually restore failed servers)

**Fallbacks**
- try_files $uri $uri/ /index.html?args: Check disk, fallback to app routing
- Named location @app: Only reachable from try_files, not from URLs
- WordPress/Rails pattern: Static files direct, everything else to app

**Request Phases (11 total)**
```
POST_READ → SERVER_REWRITE → FIND_CONFIG → REWRITE → POST_REWRITE 
→ PREACCESS → ACCESS → POST_ACCESS → PRECONTENT → CONTENT → LOG
```
- return NGX_OK means "suspended", not "done"
- Request goes to event loop, resumes at same phase later

**Which module runs when**
- limit_req: PREACCESS (rate limit before auth)
- auth_basic: ACCESS (auth check)
- try_files: PRECONTENT (prepare content)
- proxy_pass/fastcgi_pass: CONTENT (generate response)

**FastCGI Protocol**
- 8-byte header: version, type, requestId, contentLength, padding
- Length-based framing + empty record delimiter
- Empty PARAMS record = no more env vars
- Empty STDIN record = no more body
- Empty STDOUT record = no more response
- Forget empty record = responder hangs

---

## Key Algorithms

**Epoll-based event loop**
- Scalable to 10,000+ connections per process
- O(active_events) vs O(all_connections)
- Zero CPU when idle (sleeps on epoll_wait)

**LRU cache eviction**
- Intrusive linked list (no separate allocation)
- Check tail: Is it fresh? Is anyone using it? Delete if both no.
- One line: `ngx_queue_last()` + `fcn->count == 0`

**Smooth weighted round robin**
- current_weight += effective_weight
- Pick highest current_weight
- Subtract total from chosen
- Result: No bursts, even distribution

**Load balancing without coordinator**
- Each worker decides alone (no shared counter)
- Formula: ngx_accept_disabled = connection_n/8 - free_connection_n
- When 7/8 full, stop accepting, let siblings handle new requests

---

## Design Patterns

**Amortization**
- Prefork: Pre-create instead of fork per request
- Servants: Instantiate once, call method per request
- Connection pools: Reuse across requests
- Keep-alive: Reuse connection for multiple requests

**Reverse Proxy Benefits**
1. Separates concerns (web server vs app server)
2. Absorbs slow clients (frees up app servers)
3. Caches responses (reduces origin load)
4. Routes requests (single entry point)
5. Distributes load (multiple backends)

---

## Common Mistakes

**Location matching**
- Wrong: Assuming /images/a.php matches regex because it's a PHP file
- Right: Prefixes checked first, then regex; /images/ prefix wins

**Cache config**
- proxy_cache_valid + inactive: Not the same
- proxy_cache_valid: When cache expires (TTL)
- inactive: When cache evicted if not read (LRU)

**FastCGI**
- Forgetting empty record closes stream
- Responder waits forever for "end of stream"
- Request times out

**Sendfile**
- Benchmarking on loopback shows no win
- Real benefit on high-concurrency: CPU freed for other requests
- Disabled automatically when gzip enabled

---

## Architecture Principles

**1. Ask Different Question**
- Industry optimizes workers → Nginx asks why have workers at all

**2. Constraint-Based Design**
- 2002: Threads expensive, context switches expensive
- 2010s: Virtual threads cheap, goroutines cheap
- Rules are habits, not laws

**3. Data Structure = Documentation**
- Prefixes (tree) → Longest wins
- Regexes (array) → First wins
- Precedence is only rules those structures could have

**4. Take Setup Off Request Path**
- Prefork, threads, connection pools, FastCGI, keep-alive
- All pay expensive setup once, amortize across many requests
- Pattern matters more than name

---

## Quick Reference: When to Use What

| Task | Directive | Why |
|------|-----------|-----|
| Cache responses | proxy_cache | Reduce origin load, faster response |
| Prevent stampede | proxy_cache_lock | Serialize requests during miss |
| Serve outdated | proxy_cache_use_stale | 3am: old data better than error |
| Route by path | location blocks | Ternary tree, fast O(log n) lookup |
| Route by regex | location ~ | When pattern matching needed |
| Suppress regex | location ^~ | Performance: avoid O(n) search |
| Static/app fallback | try_files | Disk first, app for dynamic |
| Distribute load | upstream | Multiple backend servers |
| Smooth weights | (default) | ngx_http_upstream_round_robin.c |
| Active server only | least_conn | Better than weighted for variable latency |
| Slow I/O | thread pool | Prevent blocking event loop |

---

## Red Flags on Exam

1. "Thread per connection" = "won't scale to 10,000"
2. "Epoll" = "kernel watches connections, not user space"
3. "Generator counter" = "prevent stale events from corrupted FDs"
4. "Smooth WRR" = "no bursts, spread evenly"
5. "Try_files last arg" = "never tested, always fallback"
6. "Empty FastCGI record" = "signals end-of-stream"
7. "Inactive != proxy_cache_valid" = "Different knobs, different meanings"
8. "Sendfile disabled by gzip" = "Bytes must be touched in user space"
9. "Location precedence" = "= > ^~ > regex > implicit"
10. "NGX_OK means suspended" = "Not done, goes back to event loop"

[← Previous](CHEATSHEET.md) | [Next →](30_QUIZ_QUESTIONS.md)
