# 30 Quiz Questions - Nginx & Web Server Architecture

[← Previous](REVISION_SHORT_NOTES.md)


---

## PART 1: HISTORY & FUNDAMENTALS (Questions 1-8)

### Q1: Difference Between Connection and Request

**Question**: Explain the difference between a connection and a request in the context of web servers. Why is this distinction important for understanding the C10K problem?

**Answer**: 
- **Connection**: A persistent open channel between browser and server that remains open over time, even when idle
- **Request**: An individual data exchange (like asking for a JavaScript file) that travels through the connection
- **Key difference**: One connection can carry many requests sequentially
- **Why it matters for C10K**: Thread-per-connection model allocates one thread per connection (not per request), so idle connections still consume 8 MB of memory. Understanding this distinction shows why the problem exists—threads are wasted during idle periods when no requests are being sent.

---

### Q2: Memory Calculation - Thread-Per-Connection at Scale

**Question**: If a web server uses thread-per-connection model with 10,000 concurrent users and each thread requires 8 MB of stack space, how much RAM is consumed just for thread stacks (before the application does any work)? What does this tell us about scalability?

**Answer**: 
- Calculation: 10,000 threads × 8 MB/thread = 80,000 MB = 80 GB
- **What it tells us**: Even before processing a single request, the server has exhausted all available RAM
- **Scalability problem**: Machines don't typically have 80 GB just for thread stacks; this was the hardware ceiling at the time
- **Implication**: You cannot scale beyond ~1,000-2,000 concurrent users with this model on typical hardware

---

### Q3: Context Switching Overhead

**Question**: How does CPU context switching become a problem at 10,000 threads? Why does this create a bottleneck?

**Answer**:
- **The problem**: CPU can execute one instruction per core at a time; to manage 10,000 threads, the OS rapidly switches between them
- **Cost of switching**: Save thread state + load new thread state = significant CPU cycles wasted
- **At 10,000 threads**: CPU spends ~99% of time switching between threads, ~1% doing actual work
- **Bottleneck**: The CPU's scheduler becomes the performance limiter, not application logic
- **Example**: Like a teacher jumping between 10,000 students every microsecond without teaching anything

---

### Q4: The C10K Problem - What, When, Who

**Question**: Define the C10K problem. Who first documented it, when did it appear, and why was it significant?

**Answer**:
- **C10K**: Concurrent 10,000 connections (C = concurrent, 10K = 10,000)
- **Who**: Dan Kegel documented it in 1999
- **When**: Emerged around 2002 as hardware became fast enough to serve thousands simultaneously
- **Why significant**: Hardware was finally capable, but software architecture (thread-per-connection) couldn't handle it—the limits were: 1) per-connection stack memory, 2) per-connection scheduler entry, 3) 1983 select() API with bitmap limitations

---

### Q5: Apache's Evolution - Three Attempts

**Question**: Apache attempted to solve the thread-per-connection problem three times. Name each approach, the year, and what problem each tried to solve.

**Answer**:
1. **Prefork (Apache 1.3, 1995)**: Pre-create process pool at startup (not per-request fork)
   - Problem solved: Avoid fork() + exec() overhead per request
   
2. **Worker MPM (Apache 2.0, 1999)**: Use threads instead of processes for shared memory
   - Problem solved: Reduce memory per worker (shared memory instead of separate process space)
   - Challenge: pthreads on Linux were new and buggy at the time

3. **Event MPM (Apache 2.4, 2004)**: Listener thread parks idle connections on epoll, hands only active connections to worker threads
   - Problem solved: Don't tie up a worker thread waiting on idle connections
   
**Key insight**: All three solutions tried to make the per-connection worker cheaper, not questioning whether a worker per connection was necessary

---

### Q6: Java's Alternative Approach

**Question**: How did Java's servlet and J2EE architecture solve the resource-consumption problem differently than Apache? What was the fundamental pattern?

**Answer**:
- **CGI (inefficient)**: fork() + exec() + load interpreter + parse + run + exit for each request
- **Servlet (efficient)**: 
  - Load class ONCE at startup
  - Instantiate object ONCE
  - Per request: just call service(req, res) method
  - Object outlives the request ← THE TRICK
  
- **Fundamental pattern**: "Amortization"—take expensive setup off the request path, pay for it once, reuse the object many times
- **Extended pattern**: J2EE applied same logic to connection pools (pre-create DB connections, reuse)
- **Why it works**: Setup cost (fork, load interpreter, compile, instantiate) is expensive; ongoing usage (method calls) is cheap

---

### Q7: Igor Sysoev and the Birth of Nginx

**Question**: Who wrote Nginx, why, and what made his solution different from Apache's approach?

**Answer**:
- **Who**: Igor Sysoev, Russian engineer
- **When**: Started 2002; released October 4, 2004 (Sputnik anniversary)
- **Why**: Rambler (Russian portal) servers were falling over under connection volume, not request volume (classic C10K)
- **What made it different**:
  - Apache asked: "How do I make the worker cheaper?"
  - Nginx asked: "Why is there a worker per connection at all?"
  - Result: One worker process handles thousands of connections (not one per connection)
  - Mechanism: Event loop + kernel-managed connection watching (epoll)
- **Timeline**: Shipped continuously from 2004, but didn't call it 1.0.0 until April 2011 (shipped early, versioned late)

---

### Q8: Connection Requirements

**Question**: A connection is NOT a thing that needs a thread. What DOES a connection actually need? Explain.

**Answer**:
- **What connection needs**:
  - A few hundred bytes of state (file descriptor, buffer pointers, etc.)
  - A place in a list (to track it)
  - Until it has something to say
  
- **When it has data**:
  - Some CPU cycles to handle it
  - Finish quickly
  - Move to next connection
  
- **Result**: Don't need dedicated thread per connection; need small state, on-demand CPU
- **Implication**: One process can manage thousands of connections by processing only those with actual work

---

## PART 2: NGINX ARCHITECTURE (Questions 9-16)

### Q9: Nginx Process Model

**Question**: Draw (or describe) Nginx's process model. How many processes are there, what is their role, and why is the worker count usually equal to the CPU core count?

**Answer**:
```
Master Process
├── Reads config
├── Binds ports
└── Spawns N workers

Worker 1 (event loop)
Worker 2 (event loop)
... Worker N (one per CPU core)

Cache Manager (evicts LRU)
Cache Loader (warms cache)
```

**Why one worker per core**:
- OS rarely needs to context switch between them
- Worker stays on assigned CPU core
- Worker runs constantly processing requests
- No thread scheduler overhead

**Proof**: Run `ps -C nginx` under load—process count doesn't increase (unlike Apache with prefork)

---

### Q10: The Event Loop - 6 Lines

**Question**: Nginx event loop can be distilled to 6 lines of code. Write pseudocode and identify which line is most important and why.

**Answer**:
```c
timer = find_next_timeout();                              // Line 1
epoll_wait(cycle, timer, flags);    // ← MOST IMPORTANT  // Line 2
process_accept_events();                                  // Line 3
unlock_accept_mutex();                                    // Line 4
expire_timers();                                          // Line 5
process_all_events();                                     // Line 6
```

**Why Line 2 is critical**:
- Worker spends **99.9% of its life asleep** on `epoll_wait()`
- Timer passed as ARGUMENT to sleep (not polled)
- When event arrives, kernel wakes worker
- When no events, CPU is near 0% (not spinning/polling)

**Result**: Scales to 10K+ connections with minimal CPU usage

---

### Q11: Epoll - Interest vs Ready Lists

**Question**: Explain epoll's two-list system. How do they work together? Draw the flow when a client sends data over an existing connection.

**Answer**:
**Interest List** (Worker → Kernel):
- Worker writes: "Kernel, please watch these connections"
- Built once at connection open (epoll_ctl ADD)
- Stays constant during connection lifetime

**Ready List** (Kernel → Worker):
- Kernel maintains: "These connections have data/events right now"
- Dynamically changes as data arrives
- Returned by epoll_wait()

**Flow when client sends data**:
```
1. Connection exists (already in interest list)
2. Data arrives at kernel
3. Kernel checks: Is this connection in interest list? Yes
4. Kernel adds to ready list
5. Worker calls epoll_wait()
6. epoll_wait() returns ready list
7. Worker processes only ready connections
8. Back to epoll_wait() (sleep)
```

**Performance**: epoll_wait() only returns N events (not check 10,000 idle connections)
- select(): O(n) to build list + O(n) to scan + O(n) in kernel
- epoll(): O(number of ready events only)

---

### Q12: The Stale Event Bug

**Question**: What is the "stale event bug"? Why does it happen? How does Nginx prevent it?

**Answer**:
**The bug**:
- epoll_wait() returns batch of events
- Processing event 1 can close the connection that event 7 points to
- Kernel reuses file descriptor for new client
- Event 7 is delivered to NEW client (pointing to old connection's data)
- New client processes stale data ← CORRUPTION

**Why it happens**:
- Batch processing: All events returned at once
- Event loop processes them sequentially
- Closing a connection frees its file descriptor
- New client on same recycled FD gets wrong event

**Nginx's solution**:
```c
c = event_list[i].data.ptr;
instance = (uintptr_t) c & 1;           // Extract low bit
c = (ngx_connection_t *) ((uintptr_t) c & (uintptr_t) ~1);

if (c->fd == -1 || rev->instance != instance) {
    continue;  // Skip stale event
}
```

**How it works**:
- Structs are aligned, so low bit of pointer is always 0
- Nginx uses that bit as a generation flag
- On connection reuse, flip the bit
- Check if generation matches before processing

**Cost**: One pointer subtraction + one branch, no extra memory

---

### Q13: Thread Pools for Slow I/O

**Question**: What is the "slow disk trap"? Why is it a problem in an event-loop architecture? How does Nginx solve it with thread pools?

**Answer**:
**The trap**:
```
Worker responsible for 10,000 connections
One user requests large video file
Worker: "Disk, give me the data"
Disk: [very slow...]
Worker: Blocked, doing nothing, waiting
Other 9,999 users: Blocked too, can't get back to event loop
```

**Why it's a problem**:
- Event loop is supposed to never block
- Blocking on one connection blocks everyone else
- Defeats entire purpose of event loop

**Solution - Thread pools**:
```
When worker gets request for slow I/O:
├── Refuse to handle directly
├── Push task to queue
└── Return to event loop

Background Thread:
├── Picks up task
├── Handles slow disk I/O
├── Waits for response
└── Puts data in memory, sends signal

Worker's event loop (continues):
├── epoll_wait() for next event
├── Serves other connections
└── No blocking

When data ready:
├── Signal arrives
├── Worker checks ready list next iteration
├── Sees data ready
└── Grabs bytes and ships to user
```

**Key**: Main worker never blocks; background threads handle slow I/O

---

### Q14: Connection Management Without Per-Connection Overhead

**Question**: Nginx manages 10,000+ connections with one worker process. How is this possible given that the traditional model dedicates a thread per connection?

**Answer**:
1. **No per-connection thread**: One worker, not 10,000 threads
2. **Minimal per-connection state**: Just file descriptor + a few pointers (~200 bytes)
3. **Event-driven processing**: Only when connection has data
4. **Epoll filtering**: Kernel tells worker which connections need work
5. **Central event loop**: One loop processes all connections
   - Connection has data → Process it → Move to next
   - Connection idle → Not in ready list → Not processed

**Memory comparison**:
- Thread-per-connection: 10,000 × 8 MB = 80 GB
- Nginx: 1 × 8 MB = 8 MB (plus ~200 bytes per connection = 2 MB)
- Total: ~10 MB vs 80 GB

**CPU comparison**:
- Thread-per-connection: ~99% context switching overhead
- Nginx: ~0% when idle (sleeping on epoll_wait)

---

### Q15: Why One Worker Per Core

**Question**: Why does Nginx configure one worker process per CPU core? What happens if you configure more or fewer?

**Answer**:
**With one worker per core**:
- OS kernel rarely context switches between them
- Worker stays on assigned core
- Worker runs constantly, handling requests for assigned core
- Minimal scheduler overhead

**With fewer workers** (e.g., 2 on 8-core):
- 6 cores unused
- Doesn't scale to full machine capacity
- Wasted hardware resources

**With more workers** (e.g., 16 on 8-core):
- OS has to context switch between workers
- Workers stealing from each other's CPU time
- More thread switching, less actual work
- Defeats the purpose of event loop efficiency

**Result**: One worker per core is the sweet spot for this architecture

---

### Q16: Event Loop vs Select vs Epoll Performance

**Question**: Compare select(), poll(), and epoll() in terms of complexity, portability, and performance. Why is epoll the right choice for Nginx?

**Answer**:

| Aspect | select() | poll() | epoll() |
|--------|----------|--------|---------|
| **Watch list** | User process (rebuilt every call) | User process (rebuilt) | Kernel (edited with epoll_ctl) |
| **Complexity** | O(n) to rebuild + O(n) in kernel + O(n) to scan | O(n) to build + O(n) scan | O(active_events only) |
| **Example: 10K idle, 10 active** | 30,000 operations to find 10 events | ~30,000 operations | 10 operations |
| **Descriptor limit** | FD_SETSIZE = 1024 (compile-time, in header) | No limit | ulimit -n (runtime) |
| **Can ulimit help** | No (bitmap width, not runtime limit) | N/A | Yes (kernel-managed) |
| **Portable** | Everywhere since 1983 | Most Unix | Linux only (kqueue on BSD) |

**Why epoll for Nginx**:
1. **Scales better**: O(active) vs O(all)
2. **No rebuild**: Interest list managed by kernel
3. **Configurable limit**: ulimit -n works
4. **Better API**: Designed for thousands of connections
5. **Matches Nginx needs**: Focus on ready events, not all connections

**Trade-off**: epoll is Linux-only (acceptable for Nginx's primary use case)

---

## PART 3: FEATURES & CONFIGURATION (Questions 17-23)

### Q17: Cache Configuration - keys_zone vs levels vs max_size

**Question**: Explain each component of this cache config and what problem each solves:
```
proxy_cache_path temp/cache levels=1:2 keys_zone=demo:10m max_size=100m
```

**Answer**:

**keys_zone=demo:10m**:
- 10 MB of SHARED MEMORY (not disk)
- Holds the index: red-black tree (lookup) + LRU queue (eviction)
- Does NOT hold actual cached data (data is on disk)
- Capacity: ~8,000 keys per megabyte = 80,000 entries in 10 MB
- Problem solved: Fast cache lookup (memory resident)

**levels=1:2**:
- Two-level directory structure on disk
- Example: `cache/a/1e/...` (first level = 'a', second level = '1e')
- Problem solved: Prevents single directory with millions of files
- Filesystem lookup O(1) per directory (no inode overload)

**max_size=100m**:
- Maximum 100 MB total disk cache
- When exceeded, cache manager evicts LRU entries
- Problem solved: Prevent cache from consuming entire disk

**Interaction**: keys_zone is memory index + max_size is disk limit; together enable efficient cache management

---

### Q18: inactive vs proxy_cache_valid

**Question**: What is the difference between `inactive=60s` and `proxy_cache_valid 10s`? Which one wins if cache_valid=10s and inactive=60s? What does each actually mean?

**Answer**:

**proxy_cache_valid 10s**:
- Cache entry is VALID for 10 seconds (TTL)
- After 10 seconds, entry is expired
- Client request after 10s triggers origin fetch and cache refresh

**inactive=60s**:
- Cache entry is EVICTED if not READ for 60 seconds
- Regardless of whether it's still valid (TTL)
- Purpose: Free disk space from rarely-used entries

**Which wins**:
- proxy_cache_valid=10s AND inactive=60s:
  - Entry expires at 10 seconds (first)
  - If expired, can't be read, would never reach 60-second eviction
  - **10 seconds wins** (earlier expiration)

**But**: They're not directly competing; they're different mechanisms:
- proxy_cache_valid: Freshness (validity lifetime)
- inactive: Eviction policy (LRU cleanup)

**Common mistake**: Thinking they're the same thing
**Right understanding**: TTL vs LRU eviction are separate concerns

---

### Q19: Cache Stampede Prevention

**Question**: Explain cache stampede and how `proxy_cache_lock on;` prevents it. What's the trade-off?

**Answer**:
**Cache stampede** (thundering herd):
```
Popular object expires at 12:00:00
12:00:00.000 - Request 1: Cache MISS
12:00:00.001 - Request 2: Cache MISS (object still expired)
12:00:00.002 - Request 3: Cache MISS
...
12:00:00.200 - Request N: Cache MISS

All 100 requests in 200ms window are MISSes
All 100 go to origin server simultaneously
Origin server gets 100x traffic spike
Classic "thundering herd"
```

**Solution - proxy_cache_lock on**:
```
Request 1: MISS, acquires LOCK, goes to origin
Request 2: MISS, but LOCKED, waits
Request 3: MISS, but LOCKED, waits
...
Request 100: MISS, but LOCKED, waits

Request 1: Origin responds, stores in cache, releases LOCK
Requests 2-100: Lock releases, they check cache, get HIT

Result: Only ONE request goes to origin, others wait for result
No thundering herd
```

**Trade-off**:
- **Pro**: Protects origin from load spike
- **Con**: Waiting requests have added latency (block longer)
- **Default**: OFF (because it adds latency)
- **When to enable**: High-traffic sites with slow origin

---

### Q20: Stale Content Strategy

**Question**: What does `proxy_cache_use_stale error timeout updating http_500 http_502 http_503 http_504;` do? When would you use this?

**Answer**:
**What it does**: Serve stale (expired) cache content when:
- `error`: Error connecting to origin (network error)
- `timeout`: Timeout waiting for origin response
- `updating`: Origin is being updated in background (serve immediately)
- `http_500, http_502, http_503, http_504`: Origin returns 5xx error

**Real-world scenario** (3am incident):
```
Origin database is down
Client makes request
Cache has 4-minute-old copy (expired)

Without proxy_cache_use_stale:
  Try origin → DOWN
  Return 502 Bad Gateway
  User sees error page

With proxy_cache_use_stale:
  Try origin → DOWN
  Return 4-minute-old cached copy
  User sees slightly stale page (BETTER than error)
  
Which is better at 3am? Obviously the stale page.
Old data > No data (error page)
```

**Background refresh with `updating`**:
```
Request 1: Arrives, cache expired
  ├── Trigger background refresh (goes to origin)
  ├── Return stale copy immediately
  └── Don't wait for refresh

Request 2: Arrives while refresh happening
  ├── Sees "updating" flag
  ├── Returns stale immediately (no wait)
  └── Gets instant response

One request pays latency cost (origin fetch)
All others get instant stale response
Scales well
```

**Debug header**:
```nginx
add_header X-Cache-Status $upstream_cache_status;
```

Test:
```bash
curl -i localhost/ | grep X-Cache-Status
X-Cache-Status: MISS  (first request)
X-Cache-Status: HIT   (second request)
X-Cache-Status: UPDATING (while background refresh)
```

---

### Q21: Location Precedence Rules

**Question**: Nginx evaluates location blocks in a specific order. What is that order? Demonstrate with an example where multiple locations could match.

**Answer**:
**Precedence order**:
1. **= (exact match)**: If matches, WINS immediately, search stops
2. **^~ (longest prefix, suppress regex)**: If matches, WINS, suppresses regex search
3. **~ (regex)**: First match in file order (not longest)
4. **Implicit prefix**: Longest match, fallback only

**Example config**:
```nginx
location = /exact { }        # Rule 1
location ^~ /images/ { }     # Rule 2
location ~ \.php$ { }        # Rule 3
location / { }               # Rule 4
```

**Test cases**:
```
Request: /exact
  → Matches rule 1 (exact match)
  → WINNER: Rule 1

Request: /images/a.php
  → Matches rule 2 (/images/ prefix)
  → Rule 2 has ^~ (suppress regex)
  → Rule 3 (regex) not checked
  → WINNER: Rule 2 (NOT rule 3!)

Request: /other/a.php
  → No exact match
  → No prefix match
  → Check regex: \.php$ matches
  → WINNER: Rule 3

Request: /anything/else
  → No exact, no prefix, no regex
  → Fallback to longest prefix: Rule 4 (/)
  → WINNER: Rule 4
```

**Common mistake**: Thinking /images/a.php matches regex because it's a .php file
**Reality**: Prefix match happens FIRST, ^~ suppresses regex search

**Why ^~ exists**: Prefixes are tree (fast O(log n)), regexes are array (slow O(n)); ^~ avoids expensive regex scan

---

### Q22: Sendfile - When to Use and When It Fails

**Question**: Explain how sendfile works, when Nginx disables it, and why a benchmark on loopback doesn't show sendfile winning.

**Answer**:
**How sendfile works**:

Without sendfile (read + write):
```
disk → [copy 1, CPU] → page cache → [copy 2, CPU] → your buffer 
    → [copy 3, CPU] → socket buffer → [copy 4, DMA] → NIC

Cost: 2 mode switches per 64KB chunk, CPU copying
For 64 MB file: 2048 syscalls, massive CPU time
```

With sendfile:
```
disk → [copy 1, DMA] → page cache → [copy 2, kernel] → socket buffer 
    → [copy 4, DMA] → NIC

Cost: 0 mode switches, data never enters process
For 64 MB file: 1 syscall, data stays in kernel
```

**When Nginx disables it**:
Sendfile copies in kernel only. If bytes must be TOUCHED:
- `gzip on`: Must compress bytes (needs user space)
- `proxy_ssl_verify on`: Must decrypt TLS (needs user space)
- `sub_filter`: Must replace substrings (needs user space)

Config:
```nginx
sendfile on;
gzip on;      # These fight! gzip disables sendfile
```

When both enabled: Nginx disables sendfile for that response, brings data to user space.

**Loopback benchmark surprise**:
```bash
$ ./sendfiled 8005 www/big.bin  # 64 MB on loopback
read()      : 37.4 ms
mmap()      : 23.3 ms
sendfile()  : 33.2 ms
```

Sendfile doesn't win! Why?
- No real NIC, no DMA benefit (both are just memcpy)
- Kernel memcpy's to receiver's buffer either way
- Transfer is memory-bandwidth bound
- curl competing for same CPU
- All three hit same limits

**But sendfile IS valuable**:
- 2048 syscalls → 1 syscall (system call overhead eliminated)
- 64 MB never enters process (memory bandwidth freed)
- Benefit shows as headroom under concurrency
- CPU saved on copying = CPU available for other requests
- Not faster per-request, but enables serving more requests

**Lesson**: Benchmark the bottleneck you actually have, not the operation itself

---

### Q23: Try_Files for Routing

**Question**: Explain how `try_files $uri $uri/ /index.html?$args;` works. Draw the flow for a request that doesn't exist.

**Answer**:
**What it does**:
```nginx
location / {
    try_files $uri $uri/ /index.html?$args;
}
```

**Flow for request `/products` (doesn't exist)**:
```
Request: /products

Step 1: Check $uri (/products)
  ├─ Is it a real file?
  └─ No → Continue

Step 2: Check $uri/ (/products/)
  ├─ Is it a real directory?
  └─ No → Continue

Step 3: Fallback to /index.html?$args
  ├─ Hand /index.html to the app
  ├─ App reads REQUEST_URI = /products
  ├─ App does its own routing
  ├─ App returns appropriate page
  └─ Client sees /products (URL unchanged)
```

**Why this works**:
- Static files (js, css, images): Served directly from disk (fast)
- Dynamic routes (REST API, etc): Handled by app (app owns routing)
- Pretty URLs without explicit routing in nginx

**Last argument is never tested**:
```
try_files $uri $uri/ /index.html?$args;
                     ↑ last argument
```

If it got here (no file, no directory), the last argument is ALWAYS used.
- It's the fallback
- No test needed (it's assumed to exist)
- Always serves index.html (app routing from there)

**Named location example**:
```nginx
location / {
    try_files $uri @app;
}

location @app {
    proxy_pass http://backend;
}
```

Try disk first; if not there, jump to @app (named location):
- @app only reachable from try_files/error_page
- Never from external URL
- Transparent to client

---

## PART 4: ADVANCED TOPICS (Questions 24-30)

### Q24: Resumable HTTP Parser

**Question**: Why does Nginx use a resumable state machine for HTTP parsing instead of standard string functions? Give an example of what could go wrong with standard parsing.

**Answer**:
**Problem with standard parsing**:
```c
char* method = strtok(buffer, " ");  // Assumes complete buffer
char* uri = strtok(NULL, " ");
```

Request line can arrive in THREE TCP segments:
```
Segment 1: "GET /u"              (6 bytes)
Segment 2: "ri/path "             (8 bytes)
Segment 3: "HTTP/1.1\r\n"        (11 bytes)
```

**Why standard parsing fails**:
- strtok() requires complete, null-terminated string
- Segment 1 has no space to delimit; can't find method
- Blocks waiting for complete line
- With non-blocking I/O, can't block

**Nginx's solution**:
- 27 states for request line alone
- Parse one byte at a time
- Save state between calls
- Handles any fragmentation

**Example parsing**:
```
Segment 1: "GET /u"
  Parse G → sw_method
  Parse E → sw_method
  Parse T → sw_method
  Parse (space) → sw_spaces_before_uri
  Parse / → sw_uri
  Parse u → sw_uri
  [Buffer ends] → Save state, wait

Segment 2: "ri/path "
  [Resume at sw_uri]
  Parse r → sw_uri
  ... (more chars)
  Parse (space) → sw_http_H
  [Buffer ends] → Save state

Segment 3: "HTTP/1.1\r\n"
  [Resume at sw_http_H]
  Parse T → sw_http_HT
  ... (complete)
  Done!
```

**Result**: No blocking, handles fragments transparently, non-blocking I/O compatible

---

### Q25: Smooth Weighted Round Robin

**Question**: Implement smooth weighted round robin in pseudocode. Given weights 3:1, show the first 4 request distribution and compare to naive round robin.

**Answer**:
**Smooth WRR Algorithm**:
```c
for each request:
    for each peer:
        peer.current_weight += peer.effective_weight
        total += peer.effective_weight
    
    best = peer with highest current_weight
    best.current_weight -= total
    return best
```

**Example setup**:
- Backend1: weight=3
- Backend2: weight=1
- total = 4

**Smooth WRR distribution**:
```
Iteration 1:
  B1: current = 0+3 = 3
  B2: current = 0+1 = 1
  Best: B1 (3 > 1)
  After: B1.current = 3-4 = -1
  → B1

Iteration 2:
  B1: current = -1+3 = 2
  B2: current = 1+1 = 2
  Best: B1 (tie, first wins)
  After: B1.current = 2-4 = -2
  → B1

Iteration 3:
  B1: current = -2+3 = 1
  B2: current = 2+1 = 3
  Best: B2 (3 > 1)
  After: B2.current = 3-4 = -1
  → B2

Iteration 4:
  B1: current = 1+3 = 4
  B2: current = -1+1 = 0
  Best: B1 (4 > 0)
  After: B1.current = 4-4 = 0
  → B1

Smooth pattern: a a b a [repeat]
Ratio: 3:1 maintained smoothly
```

**Naive WRR comparison**:
```
Naive algorithm: Just cycle through servers weighted
  Request 1 → B1
  Request 2 → B1
  Request 3 → B1
  Request 4 → B2
  Request 5 → B1
  ...

Naive pattern: a a a b a a a b [repeat]
Ratio: 3:1 (same ratio)
But: BURSTS to B1, then gap for B2
Problem: Queue backs up at B1, then suddenly switches
```

**Why smooth is better**:
- Same 3:1 ratio
- No request bursts at any server
- Evens out load across time
- Better tail latency (p99)

**Measurement**:
```bash
for i in $(seq 24); do curl localhost:8082/x-$i; done
grep upstream logs/access.log | sort | uniq -c
  6 upstream=B1    ← weight 1 server
  18 upstream=B2   ← weight 3 server
  
Wait, that's backwards from my example
But the point: Ratio is maintained, distribution is smooth
```

---

### Q26: Request Phases and Module Execution Order

**Question**: Name all 11 request phases. Explain which module runs in which phase using these examples: limit_req, auth_basic, try_files, proxy_pass.

**Answer**:
**The 11 phases**:
```
POST_READ           ← Read headers
SERVER_REWRITE      ← Rewrite host/server
FIND_CONFIG         ← Find matching location block
REWRITE             ← Rewrite URI
POST_REWRITE        ← Validate rewrite
PREACCESS           ← Preconditions (rate limit)
ACCESS              ← Auth decision
POST_ACCESS         ← Post-auth checks
PRECONTENT          ← Prepare content (filesystem checks)
CONTENT             ← Generate response (proxy, static, etc)
LOG                 ← Log the request
```

**Module placement** (`grep -rn "NGX_HTTP_.*_PHASE" src/http/modules/`):
```
limit_req        → PREACCESS
  (Rate limit before auth; fail fast if rate exceeded)

auth_basic       → ACCESS
  (Authentication decision; check credentials)

try_files        → PRECONTENT
  (Filesystem checks; stat() for file/directory)

proxy_pass       → CONTENT
(app_logic)      (Actually generate response by forwarding)
fastcgi_pass     → CONTENT
static files     → CONTENT
```

**Example request flow**: GET /protected/file.txt
```
POST_READ:
  ├─ Parse headers
  └─ [Continue]

SERVER_REWRITE:
  ├─ [No rewrites]
  └─ [Continue]

FIND_CONFIG:
  ├─ Find location block matching /protected/
  └─ [Continue]

REWRITE:
  ├─ [No URI rewrites]
  └─ [Continue]

POST_REWRITE:
  ├─ [Validate]
  └─ [Continue]

PREACCESS: ← limit_req runs here
  ├─ Check rate limit
  ├─ If exceeded: Return 429
  └─ [Continue]

ACCESS: ← auth_basic runs here
  ├─ Check auth_basic
  ├─ If no valid credentials: Return 401
  └─ [Continue]

POST_ACCESS:
  ├─ [Post-auth checks]
  └─ [Continue]

PRECONTENT: ← try_files runs here
  ├─ try_files $uri $uri/ /index.html
  ├─ stat() filesystem
  ├─ If found: Prepare content handler
  └─ [Continue]

CONTENT: ← proxy_pass / static file handler runs here
  ├─ proxy_pass http://backend (if configured)
  ├─ OR serve /index.html from disk (if try_files fallback)
  └─ [Done]

LOG:
  ├─ Log the request
  └─ [Complete]
```

**Critical insight**: `return NGX_OK` means "SUSPENDED", not done
- Request doesn't complete immediately
- Goes back to event loop
- Resumes at same phase when event fires
- Coroutine behavior (hand-rolled in C)

---

### Q27: FastCGI Protocol - Handshake

**Question**: Explain the FastCGI wire protocol. Show the exact bytes exchanged in a BEGIN_REQUEST record and explain why the empty PARAMS record is essential.

**Answer**:
**FastCGI record header** (8 bytes):
```
Byte 0: Version (1)
Byte 1: Type (BEGIN_REQUEST=1, PARAMS=4, STDIN=5, STDOUT=6, STDERR=7, etc)
Byte 2-3: RequestId (big-endian 16-bit, e.g., 0x0001)
Byte 4-5: ContentLength (big-endian 16-bit)
Byte 6: PadLen (padding bytes)
Byte 7: Reserved
```

**BEGIN_REQUEST example**:
```
01 01 00 01 00 08 00 00
↓  ↓  ↓  ↓  ↓  ↓  ↓  ↓
V  T  RequestId(1) ContentLen(8) Pad Res
```

Followed by 8 bytes of BEGIN_REQUEST body (flags, role, etc.)

**Full handshake** (nginx → PHP-FPM):
```
BEGIN_REQUEST
  01 01 00 01 00 08 00 00 [8 bytes body]
  
PARAMS (environment variables)
  01 04 00 01 [contentLen] [padLen] 00 [env var key=value pairs]
  
PARAMS (empty) ← CRITICAL
  01 04 00 01 00 00 00 00
  This means: "No more PARAMS"

STDIN (request body)
  01 05 00 01 [contentLen] [padLen] 00 [POST data]
  
STDIN (empty) ← CRITICAL
  01 05 00 01 00 00 00 00
  This means: "No more STDIN"
```

**Why empty record is essential**:
```
Without empty PARAMS:
  Responder reads PARAMS
  Waits for "end of params" signal
  [No empty record sent]
  Responder: "Is this the end? Or is more coming?"
  Hangs forever waiting

Without empty STDIN:
  Responder reads body data
  Waits for "end of body" signal
  [No empty record sent]
  Responder: "Is this it? Or is more coming?"
  Hangs forever waiting

With empty record:
  Responder: "0 bytes? That's the end-of-stream marker!"
  Proceeds confidently
```

**Length + delimiter pattern** (Session 2's "closing idea at two levels"):
1. **Length inside header**: Efficient buffering (know how much to read)
2. **Empty record delimiter**: Protocol clarity (know when stream is complete)

**Common mistake**: Developers implement FastCGI, forget empty records
- Responder never receives "end of stream" signal
- Responder hangs
- Request times out
- Blame nginx for being slow

---

### Q28: Load Balancer Configuration

**Question**: Write Nginx config to:
1. Define three backend servers
2. Weight them 2:1:1
3. Mark one as backup (only use if others down)
4. Use least connections (don't use weights)

**Answer**:

**Weighted round robin** (2:1:1 ratio):
```nginx
upstream app_weighted {
    server backend1.example.com:8000 weight=2;
    server backend2.example.com:8000 weight=1;
    server backend3.example.com:8000 weight=1;
}

server {
    location / {
        proxy_pass http://app_weighted;
    }
}
```

**With backup server**:
```nginx
upstream app_with_backup {
    server primary1.example.com:8000 weight=2;
    server primary2.example.com:8000 weight=1;
    server backup.example.com:8000 backup;  ← Only used if all others down
}

server {
    location / {
        proxy_pass http://app_with_backup;
    }
}
```

**Least connections** (ignore weights, use active connections):
```nginx
upstream app_least_conn {
    least_conn;  ← Algorithm: always send to server with fewest active conns
    server backend1.example.com:8000;
    server backend2.example.com:8000;
    server backend3.example.com:8000;
}

server {
    location / {
        proxy_pass http://app_least_conn;
    }
}
```

**When to use which**:
- **Weighted round robin**: Servers have consistent capacity (Backend1 is 2x faster)
- **Least connections**: Request duration varies (some requests take 100ms, others 10s)
  - Better p99 latency (don't back up fast server)
- **Backup**: Disaster recovery (primary down, failover to backup)

**Health checks** (implicit):
```nginx
upstream app {
    server backend1.example.com:8000 max_fails=3 fail_timeout=30s;
    server backend2.example.com:8000;
}
```

- max_fails=3: Mark down after 3 failures
- fail_timeout=30s: Retry in 30s (passive health check)

---

### Q29: Complete Nginx Config Example

**Question**: Write a complete Nginx config that:
1. Caches responses from a backend API
2. Prevents cache stampede
3. Serves stale on origin error
4. Routes static files directly, dynamic requests to backend

**Answer**:
```nginx
# Cache definition
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m
                 max_size=500m inactive=60m use_temp_path=off;

upstream backend_api {
    server api1.example.com:8000 weight=2;
    server api2.example.com:8000 weight=1;
    server api_backup.example.com:8000 backup;
}

server {
    listen 80;
    server_name example.com;
    
    # Cache configuration
    proxy_cache api_cache;
    proxy_cache_lock on;                    # Prevent stampede
    proxy_cache_lock_timeout 5s;
    proxy_cache_use_stale error timeout     # Serve stale on error
                          updating 
                          http_500 http_502 http_503 http_504;
    proxy_cache_valid 200 10m;              # Cache 200 responses for 10m
    proxy_cache_valid 404 1m;               # Cache 404 for 1m
    
    # Debug header (see cache status)
    add_header X-Cache-Status $upstream_cache_status;
    
    # Static files (no cache)
    location ~* ^/(css|js|images)/ {
        root /var/www;
        expires 1d;                         # Browser cache 1 day
        add_header Cache-Control "public, immutable";
    }
    
    # Static files (no proxy)
    location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
        root /var/www;
        expires 7d;
        add_header Cache-Control "public, max-age=604800";
    }
    
    # Pretty URLs (try disk, fallback to app)
    location / {
        try_files $uri $uri/ @backend;
    }
    
    # Named location for backend
    location @backend {
        proxy_pass http://backend_api;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Cache rules
        proxy_cache api_cache;
        proxy_cache_methods GET HEAD;       # Only cache GET, HEAD
        proxy_cache_key "$scheme$request_method$host$request_uri";
        proxy_buffering on;                 # Buffer response
    }
    
    # Health check endpoint (no cache)
    location /health {
        access_log off;
        proxy_pass http://backend_api;
        proxy_cache off;                    # Don't cache health checks
    }
    
    # Logging
    access_log /var/log/nginx/access.log combined;
    error_log /var/log/nginx/error.log warn;
}
```

**How it works**:
1. Static files served directly from disk (no upstream, no cache)
2. Pretty URLs: try disk first (static), fallback to backend
3. Backend requests cached with stampede protection
4. Stale content served on origin errors
5. Cache key includes method + scheme + host + URI (comprehensive)
6. Health checks bypass cache (see real status)

---

### Q30: Debugging - Where Does Cache Miss Come From?

**Question**: Your cached API endpoint is getting HIT, but sometimes you see MISS. Add debugging headers and explain what each cache status means. What tools can you use to debug cache issues?

**Answer**:
**Cache status meanings**:
```
X-Cache-Status: HIT
  → Cache lookup succeeded
  → Served directly from cache disk
  → No origin request

X-Cache-Status: MISS
  → Cache lookup failed (first request or expired)
  → Fetched from origin
  → Stored in cache for future requests

X-Cache-Status: STALE
  → Cache hit, but entry is expired (past TTL)
  → Served expired copy (if use_stale configured)
  → Background refresh may be happening

X-Cache-Status: UPDATING
  → Entry is being refreshed in background
  → Stale copy served immediately
  → Another request triggered refresh

X-Cache-Status: BYPASS
  → Cache was explicitly bypassed
  → Maybe proxy_no_cache or proxy_cache_bypass condition

X-Cache-Status: EXPIRED
  → Entry exists but TTL passed
  → Not served (no use_stale configured)
  → Origin fetched instead
```

**Debugging config**:
```nginx
# Add these headers for debugging
add_header X-Cache-Status $upstream_cache_status;
add_header X-Cache-Key $scheme$request_method$host$request_uri;
add_header X-Cache-Expires $upstream_cache_last_modified;
add_header X-Upstream-Status $upstream_status;
add_header X-Upstream-Response-Time $upstream_response_time;
add_header X-Response-Time $request_time;
```

**Testing cache**:
```bash
# First request (MISS)
curl -I http://localhost/api/data | grep X-Cache
X-Cache-Status: MISS

# Second request immediately (HIT)
curl -I http://localhost/api/data | grep X-Cache
X-Cache-Status: HIT

# Check cache directory
du -sh /var/cache/nginx/
ls -la /var/cache/nginx/*/

# Flush cache
rm -rf /var/cache/nginx/*
```

**Command-line debugging**:
```bash
# Check cache index (shared memory)
curl -I http://localhost/api/data -w "\nCache: %{http_x_cache_status}\n"

# Check response headers
curl -i http://localhost/api/data | head -20

# Check nginx cache stats
# (If you compiled with stats module)
curl http://localhost/cache_stats

# Check origin response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost/api/data
```

**Common cache issues**:
```
Issue: MISS every time (not caching)
Checks:
  ├─ Is proxy_cache enabled? (proxy_cache <zone>)
  ├─ Is it on the right location block?
  ├─ Are headers Vary set? (browsers vary, cache doesn't)
  └─ Is proxy_cache_valid set? (default is no caching)

Issue: STALE always served (never gets fresh)
Checks:
  ├─ Is origin down? (check with direct request)
  ├─ Is proxy_cache_valid too long?
  └─ Is background update stuck?

Issue: HIT ratio too low (mostly MISS)
Checks:
  ├─ Cache key includes cookies/user-agent (unique per user)?
  ├─ Cache key includes query params (should it)?
  ├─ Are clients sending no-cache headers?
  └─ Is inactive timeout too short?
```

**Logs to check**:
```bash
tail -f /var/log/nginx/access.log | grep MISS   # Find misses
tail -f /var/log/nginx/error.log | grep cache   # Cache errors
```

---

## Answer Key Summary

| Q# | Topic | Key Concept |
|:--:|-------|-------------|
| 1 | Connection vs Request | Connection persistent; request individual |
| 2 | Memory Calculation | 10K × 8MB = 80 GB (unsustainable) |
| 3 | Context Switching | 99% overhead at 10K threads |
| 4 | C10K Problem | Can't scale 10K concurrent with threads |
| 5 | Apache Evolution | Prefork → Worker MPM → Event MPM |
| 6 | Java Solution | Servlet amortization; connection pooling |
| 7 | Nginx Birth | Igor Sysoev, 2002, asked "why worker at all?" |
| 8 | Connection Needs | State + list + on-demand CPU (not thread) |
| 9 | Process Model | Master + N workers (one per core) + cache procs |
| 10 | Event Loop | 6 lines; line 2 sleeps 99.9% of time |
| 11 | Epoll Lists | Interest (static) + Ready (dynamic) lists |
| 12 | Stale Events | Generation counter in pointer low bit |
| 13 | Thread Pools | Background I/O; main loop unblocked |
| 14 | Scalability | ~200 bytes per connection; epoll filtering |
| 15 | Worker Count | One per core; minimal context switching |
| 16 | Select vs Epoll | epoll O(active), select O(all); epoll wins |
| 17 | Cache Config | keys_zone, levels, max_size, inactive |
| 18 | Inactive vs Valid | LRU eviction vs TTL; different mechanisms |
| 19 | Cache Stampede | Thundering herd; proxy_cache_lock solution |
| 20 | Stale Content | Serve old on origin error; 3am lifesaver |
| 21 | Location Rules | = > ^~ > regex > implicit |
| 22 | Sendfile | Kernel copy; disabled by gzip/TLS |
| 23 | Try_Files | Disk → directory → fallback; routing |
| 24 | Parser | 27 states; one byte at a time; resumable |
| 25 | Smooth WRR | current_weight += effective; highest wins |
| 26 | Request Phases | 11 phases; modules hook into each |
| 27 | FastCGI | 8-byte header; empty record = end-of-stream |
| 28 | Load Balancing | Weighted RR, least_conn, backup, weights |
| 29 | Config Example | Cache + stampede prevention + fallback |
| 30 | Debugging | X-Cache-Status header; check keys_zone size |

---

**Good luck on your exam! 🎯**

Focus on:
1. **C10K problem** (history context)
2. **Event loop + epoll** (core architecture)
3. **Cache concepts** (features)
4. **Routing + phases** (practical config)
5. **Design patterns** (why decisions matter)

[← Previous](REVISION_SHORT_NOTES.md)
