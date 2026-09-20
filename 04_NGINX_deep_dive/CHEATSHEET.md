# Nginx Cheatsheet - Exam Prep

[← Previous](Part_4_Advanced_Topics.md) | [Next →](REVISION_SHORT_NOTES.md)


## Definitions

**Connection** = Persistent channel (survives multiple requests)
**Request** = Single data exchange
**Thread-per-connection** = 1 user = 1 thread (8 MB × 10K = 80 GB)
**C10K** = Can't serve 10,000 concurrent connections (2002 problem)
**Epoll** = Kernel mechanism telling nginx which connections have data
**Event loop** = Sleep on epoll_wait(), process ready events, repeat
**Reverse proxy** = Sits between clients and servers, routes/caches/load-balances

---

## History Timeline

| Year | What | Why It Matters |
|------|------|----------------|
| 1990 | CERN httpd (Berners-Lee) | First web server |
| 1993 | NCSA HTTPd (Rob McCool) | Invented CGI |
| 1995 | Apache prefork | Pre-create processes, avoid fork() per request |
| 1999 | Apache worker MPM | Threads instead of processes |
| 2002 | C10K Problem recognized | Hardware ready, software not |
| 2004 | Nginx first release | Event loop, single worker, 10K connections |
| 2011 | Nginx 1.0.0 | After 7 years of shipping |

**Key shift**: Apache asked "How cheaper?", Nginx asked "Why at all?"

---

## Thread-Per-Connection Failures

**Memory**: 8 MB/thread × 10,000 = 80 GB RAM (before app runs)
**CPU**: 99% context switching, 1% work
**Idle**: Threads block waiting for disk/network, hold memory uselessly

---

## Nginx Process Model

```
Master (config, spawn workers)
├─ Worker 1 (1 event loop, ~10K connections)
├─ Worker 2 (1 event loop, ~10K connections)
├─ Worker N (one per CPU core)
├─ Cache manager
└─ Cache loader
```

**Key**: Process count doesn't change under load (unlike Apache)

---

## Event Loop (Core of Nginx)

```c
timer = find_timeout();
epoll_wait(timer);                    // SLEEP here 99.9% of time
process_ready_events();
```

**Result**: ~0% CPU when idle, scales to 10K+ connections

---

## Epoll Mechanism

**Interest List** (Worker → Kernel): "Watch these connections"
**Ready List** (Kernel → Worker): "These have data"

**Flow**:
1. Connection opens → Worker: epoll_ctl(ADD) to interest list
2. Data arrives → Kernel checks interest list, adds to ready list
3. Worker wakes up → epoll_wait() returns ready list
4. Worker processes ready connections only
5. Loop sleeps again

**Performance**: O(active_events), not O(all_connections)

---

## Stale Event Bug & Fix

**Problem**: Batch from epoll_wait(); closing connection 1 = recycled FD; connection 7's event delivered to new client on same FD

**Solution**: Generation counter in pointer's low bit
- Flip bit on connection reuse
- Check bit matches before processing
- One branch, no extra memory

---

## Slow I/O & Thread Pools

**Problem**: Worker blocks on slow disk → all 10K connections wait
**Solution**: 
- Push slow task to background thread queue
- Worker returns to event loop immediately
- Background thread handles disk I/O
- Worker resumes when data ready

---

## Cache Structure

**keys_zone=demo:10m**: Shared memory holding index (~8K entries/MB), not data
**levels=1:2**: Two-level disk dirs (prevent inode overload)
**max_size=100m**: Disk limit (eviction when exceeded)
**inactive=60s**: Evict if not READ for 60s (regardless of TTL)

---

## LRU Eviction (One Line)

```
Check tail (LRU) → Expired? → Nobody streaming? → Delete
```

**count==0** = not being streamed to client = can evict

---

## Cache Stampede Prevention

```
proxy_cache_lock on;
```

One request fetches, others wait for result (no thundering herd)

---

## Location Precedence

```
= (exact match)     → Wins, stop search
^~ (longest prefix) → Wins, suppress regex
~  (regex)          → First match in file order
(implicit prefix)   → Fallback only
```

**Why**:
- Prefixes = ternary tree (O(log n), built at parse time)
- Regexes = array (O(n), checked every request)
- ^~ avoids expensive regex scan

---

## Sendfile

**Without**: read() + write() = 4 copies + 2 mode switches
**With**: kernel copies to socket buffer = 2 copies + 0 mode switches
**Disabled by**: gzip, TLS, templating (bytes need touching)

---

## HTTP Parser: 27 States

Resumable state machine (handles fragmented TCP segments)

```
Segment 1: "GET /u" → Save state
Segment 2: "ri/path " → Resume, parse more
Segment 3: "HTTP/1.1\r\n" → Resume, done
```

No regex, no blocking, handles any TCP fragmentation

---

## Smooth Weighted Round Robin

```
current_weight += effective_weight
Pick highest current_weight
Subtract total from chosen
```

Result: a b a a b a (smooth, no bursts)
Traditional: a a a b (bursts to one server)

**Passive health check**: effective_weight gradually restored if failed

---

## Try_Files Fallback

```nginx
location / { try_files $uri $uri/ /index.html?$args; }
```

Check disk file → Check directory → Fallback to app

**Named location** `@app` (only from try_files, never from URL):
```nginx
location @app { proxy_pass http://app; }
```

---

## Request Phases (11)

```
POST_READ → SERVER_REWRITE → FIND_CONFIG → REWRITE → POST_REWRITE 
→ PREACCESS → ACCESS → POST_ACCESS → PRECONTENT → CONTENT → LOG
```

**NGX_OK return** = Suspended (not done), goes to event loop, resumes later

**Module placement**:
- limit_req: PREACCESS (rate limit before auth)
- auth_basic: ACCESS (auth check)
- try_files: PRECONTENT
- proxy_pass: CONTENT

---

## FastCGI Protocol

8-byte header: version|type|requestId|contentLength|padLen|reserved

**Key**: Empty record = end-of-stream
- Empty PARAMS = no more env vars
- Empty STDIN = no more body
- Empty STDOUT = no more response

**Forget empty record** = responder hangs waiting for "close"

---

## Amortization Pattern (Core Idea)

Take expensive operation OFF request path, pay once:
- Prefork: Fork at startup, not per request
- Servlets: Instantiate once, reuse
- Connection pools: Reuse DB connections
- Keep-alive: Reuse TCP connections
- FastCGI: Reuse responder processes

---

## Design Principles

**1. Ask different question**
- Old: "How do I make worker cheaper?"
- Nginx: "Why have a worker per connection?"

**2. Constraint changes → Rules are habits**
- 2002: Threads = 8 MB, expensive context switch
- 2010s: Virtual threads cheap, goroutines cheap
- Rules are laws (physics) or habits (2004)

**3. Data structure = Documentation**
- Tree → longest wins
- Array → first wins
- Precedence = only rules structure could have

**4. Amortize setup**
- Six different patterns, same idea
- Take setup off request path

---

## Quick Q&A

**Q: Why 10,000 threads fail?**
A: 80 GB memory + 99% CPU on context switching

**Q: How does epoll solve it?**
A: Kernel tells worker which connections need work; worker sleeps otherwise

**Q: What's the stale event bug?**
A: Closed connection FD recycled; new client gets old event

**Q: Why ^~ before regex?**
A: Prefixes are tree (fast), regexes are array (slow); ^~ avoids expensive scan

**Q: When does sendfile disable?**
A: When bytes must be touched (gzip, TLS, templating)

**Q: What's cache stampede?**
A: Popular object expires; all requests miss simultaneously; all hit origin

**Q: Why proxy_cache_lock?**
A: Serialize requests during miss; one fetches, others wait

**Q: What's try_files last arg?**
A: Fallback; never tested; always used if nothing else matches

**Q: Why FastCGI needs empty record?**
A: Signals end-of-stream; responder knows when to stop waiting

**Q: What does NGX_OK mean?**
A: Suspended, not done; request goes to event loop

---

## Formulas

**RAM for threads**: Num_threads × Stack_size_MB
- 10,000 × 8 = 80,000 MB = 80 GB

**Cache key capacity**: keys_zone_MB × 8,000 keys/MB
- 10 MB = 80,000 keys

**Smooth WRR selection**:
```
current_weight += effective_weight
best = highest current_weight
best.current_weight -= total_weight
```

**Load balancing formula** (no coordinator):
```
ngx_accept_disabled = connection_n/8 - free_connection_n
if (ngx_accept_disabled > 0) stop_accepting();
```

---

## Common Mistakes

| Mistake | Reality |
|---------|---------|
| "/images/a.php matches regex" | No, /images/ prefix wins first |
| "inactive same as proxy_cache_valid" | No, LRU eviction vs TTL |
| "sendfile faster on loopback" | No, CPU-bound; benefit in concurrency |
| "location order matters for precedence" | No, structure matters (tree vs array) |
| "One thread handles all connections" | Not true, one per core; still event loop per thread |
| "Forgetting empty FastCGI record is OK" | No, responder hangs |
| "Cache with lock = always fast" | No, one request still pays latency |

---

## For Exam: Memorize These Numbers

- **8 MB** = default thread stack size
- **80 GB** = RAM for 10,000 threads (10K × 8MB)
- **10,000** = the "10K" in C10K problem
- **1,024** = FD_SETSIZE limit (select)
- **27** = states in HTTP parser
- **11** = request phases
- **8 bytes** = FastCGI record header
- **2002** = year C10K problem recognized
- **2004** = nginx first release
- **2011** = nginx 1.0.0 released

---

## Nginx Config Mnemonics

**Location precedence = "ERPI"**:
- **E**xact match first
- **R**egex before implicit (but after ^~)
- **P**refix longest (with ^~)
- **I**mplicit prefix fallback

**Cache config**:
- **keys_zone** = in-memory index
- **levels** = disk directory levels
- **max_size** = eviction limit
- **inactive** = LRU timeout

**Phases**:
- PRE-ACCESS, ACCESS, POST-ACCESS = auth flow
- PRECONTENT, CONTENT = response generation
- POST_READ, FIND_CONFIG = request setup

---

## Diagram Patterns (No Colors)

### Event Loop Flow
```
Worker Process
    ↓
    └─→ Event Loop (endless)
           ├─ epoll_wait() [SLEEP 99.9%]
           ├─ Process ready connections
           └─ [LOOP]
```

### Connection Lifecycle
```
Client connects
    ↓
    └─→ Worker: epoll_ctl(ADD) → interest list
           ↓
        Data arrives
           ↓
        Kernel: add to ready list
           ↓
        epoll_wait() wakes
           ↓
        Worker processes
           ↓
        Response sent
```

### Cache Hit/Miss Flow
```
Request arrives
    ↓
    └─→ Check cache (keys_zone)
           ├─ HIT: Serve from disk
           ├─ MISS: Fetch from origin
           │        └─→ Store in cache
           └─ STALE: Serve stale + update background
```

---

## Last-Minute Checklist

Before exam:
- [ ] C10K = 10K connections, can't do thread per connection
- [ ] Epoll = kernel watches, worker only processes ready connections
- [ ] Event loop = sleep 99.9% of time on epoll_wait()
- [ ] Stale events = generation counter in pointer low bit
- [ ] Thread pools = background I/O, main loop unblocked
- [ ] Cache = keys_zone (index), levels (dirs), max_size (eviction), inactive (LRU)
- [ ] LRU = check tail, is it expired + nobody using? delete
- [ ] Cache lock = one request fetches, others wait (no stampede)
- [ ] Location = = (exact) > ^~ (prefix) > ~ (regex) > implicit
- [ ] Prefixes = tree (fast), regexes = array (slow)
- [ ] Sendfile = disabled by gzip/TLS (bytes must be touched)
- [ ] Parser = 27 states, resumable, handles fragmentation
- [ ] Try_files = disk → directory → fallback
- [ ] Phases = 11 total; NGX_OK = suspended, go to event loop
- [ ] FastCGI = 8-byte header, empty record = end-of-stream
- [ ] WRR = smooth formula: highest current_weight, subtract total
- [ ] Amortize = take setup off request path
- [ ] Design question = ask different question, not how to make cheaper

[← Previous](Part_4_Advanced_Topics.md) | [Next →](REVISION_SHORT_NOTES.md)
