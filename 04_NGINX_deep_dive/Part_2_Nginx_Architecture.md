# Part 2: Nginx Architecture - The Event Loop Revolution

## 2.1 Igor Sysoev & The Birth of Nginx

### The Problem Context
- **Company**: Rambler (one of Russia's largest portals, 2002)
- **Issue**: Apache servers falling over under connection volume, not request volume
- **Root Cause**: Thread-per-connection model couldn't handle C10K
- **Solution**: Igor Sysoev started writing nginx in 2002

### Timeline
- **2002**: Started writing nginx to solve C10K specifically
- **October 4, 2004**: First public release (chosen for Sputnik anniversary)
- **April 2011**: Version 1.0.0 released (7 years before "1.0" - shipped early, versioned late)

### The Fundamental Question Shift

**Apache asked**: "How do I make the worker cheaper?"
**Nginx asked**: "Why is there a worker per connection at all?"

**Key Insight**: A connection is NOT a thing that needs a thread. It's a thing that needs:
- A few hundred bytes of state
- A place in a list
- Until it has something to say

When it does have data, some CPU handles it, finishes, and moves on.

---

## 2.2 Nginx Process Model

### Architecture Overview

```
Master Process
├── Reads configuration file
├── Binds to network ports (:80, :443, etc.)
├── Spawns worker processes
└── Handles signals (reload, graceful shutdown)

Worker Process 1 → Event Loop → Handles 10,000 connections
Worker Process 2 → Event Loop → Handles 10,000 connections
Worker Process 3 → Event Loop → Handles 10,000 connections
...
Worker Process N → Event Loop → Handles 10,000 connections

Cache Manager Process
└── Evicts LRU cache entries

Cache Loader Process
└── Warms up cache index
```

### Worker Count Configuration

**Design principle**: One worker process per CPU core

**Example**: 8-core server → 8 worker processes

**Why this ratio?**
- Operating system rarely needs context switches between them
- Each worker stays on its assigned core
- Worker runs constantly to process network requests
- No thread scheduling overhead

**Proof**:
```bash
$ ps -o pid,ppid,args -C nginx
2663 1 nginx: master process
2665 2663 nginx: worker process
2666 2663 nginx: worker process
2667 2663 nginx: cache manager process
```

The process count does NOT increase under load (unlike Apache).

---

## 2.3 The Event Loop: The Core of Nginx

### Event Loop in 6 Lines

This is what nginx does, distilled:

```c
timer = ngx_event_find_timer();           // Line 1: Find next timeout
ngx_process_events(cycle, timer, flags);  // Line 2: SLEEP on epoll_wait()
ngx_event_process_posted(cycle, &ngx_posted_accept_events);  // Line 3
ngx_shmtx_unlock(&ngx_accept_mutex);      // Line 4
ngx_event_expire_timers();                // Line 5: Handle expired timers
ngx_event_process_posted(cycle, &ngx_posted_events);         // Line 6
```

### Where Nginx Spends Its Life

**Line 2 is critical**: A worker spends **99.9% of its life asleep** on `epoll_wait()`

- The timer is passed as an ARGUMENT to the sleep
- Nginx **never polls** for timeouts
- Handlers don't run inside the poll; they're posted and drained after (lines 3-6)

### Why This is Brilliant

```
Traditional polling:
while (true) {
    check_all_connections()  // Thousands of times per second
    check_timers()
    process_work()
}
CPU: 100% (even when idle)

Nginx event loop:
while (true) {
    epoll_wait() // SLEEP until something happens
    process_ready_connections()
}
CPU: Near 0% (when idle)
```

**Result**: Everything in `src/http/` is just callbacks reached from line 2 or line 6 of the event loop.

---

## 2.4 Epoll: The Kernel Does the Watching

### The Problem with Watching Thousands of Connections

A worker is responsible for thousands of connections. Most are idle at any moment.

**Naive approach**: Walk through all connections and check if each has data
- Thousands of checks per iteration
- Wasted CPU on idle connections
- Doesn't scale

**Smart approach**: Let the kernel do it

### Epoll System Call

Nginx uses Linux kernel's **epoll** facility:
- Kernel receives all network traffic anyway
- Kernel already knows which connections have data
- Kernel tells nginx which connections need attention
- Nginx only processes connections with actual work

### Epoll Two-List System

The worker and kernel communicate via two lists:

#### 1. Interest List
```
Worker writes: "Kernel, please watch these connections for me"

When connection opens:
  epoll_ctl(ADD) → Add connection to interest list
  
Example interest list:
Connection 1 → (registered once, stays on list)
Connection 2 → (registered once, stays on list)
Connection 3 → (registered once, stays on list)
...
Connection 10,000 → (registered once, stays on list)
```

#### 2. Ready List
```
Kernel writes: "These connections have something happening"

When data arrives:
  Kernel checks interest list
  If connection is there → Add to ready list
  
Example ready list (keeps changing):
[Connection 5 has incoming request]
[Connection 127 has response from backend ready]
[Connection 8942 sent close signal]
```

### Epoll Example: Real Flow

```
Step 1: User opens web app
  → Opens connection
  → Worker sees new connection
  → Worker: epoll_ctl(ADD) to interest list
  
Step 2: User clicks orders tab
  → Frontend sends request
  → Request travels over existing connection
  → Data arrives at kernel
  
Step 3: Kernel spots incoming bytes
  → Checks interest list
  → Finds connection in list
  → Adds connection to ready list
  
Step 4: Worker's event loop
  → Calls epoll_wait()
  → Kernel says: "Connection 5 is ready!"
  → Worker grabs connection
  → Reads request, fetches orders, sends response
  → Goes back to epoll_wait() to sleep
  
Step 5: Connection sitting idle
  → No new data
  → NOT on ready list
  → Worker doesn't waste time checking it
  → Worker is asleep, using 0% CPU
```

### Select vs Epoll Performance

| Aspect | select() | epoll() |
|--------|----------|---------|
| **Watch list location** | Your process (rebuilt every call) | Kernel (edited with epoll_ctl) |
| **Cost per iteration** | O(n) to build + O(n) in kernel + O(n) to scan | O(active events only) |
| **Example: 10,000 idle, 10 active** | 30,000 units of work to find 10 events | 10 units of work |
| **Descriptor ceiling** | FD_SETSIZE = 1024 (compile-time, in header) | ulimit -n (configurable) |
| **Portable** | Everywhere since 1983 | Linux only (kqueue on BSD) |

**Key difference**: `select()` is O(n), `epoll()` is O(active events)

---

## 2.5 The Slow Disk Trap & Thread Pools

### The Problem

Event loop seems perfect, but has one fatal flaw:

```
Worker is responsible for 10,000 connections
Each connection is in the event loop
One slow operation blocks everyone else
```

### Scenario: Video File on Slow Disk

```
Step 1: User requests large video file
  → Connection lands on ready list
  → Worker picks it up
  
Step 2: Worker asks disk for data
  → Mechanical hard drive is SLOW
  → Worker sits doing nothing, just waiting
  
Step 3: Other users are blocked
  → 9,999 other connections are waiting
  → Worker can't get back to event loop
  → Another user requests small JavaScript file
  → They wait until video finishes loading
  
Result: One slow operation blocks everyone
```

### Solution: Thread Pools

```
When worker gets request for slow operation:
  ├── Refuses to handle it directly
  ├── Pushes task to queue
  └── Returns to event loop
  
Background Thread (separate from event loop):
  ├── Picks up task from queue
  ├── Talks to slow disk
  ├── Waits for response
  └── Puts data in memory
  
Worker's event loop (continues):
  ├── epoll_wait() for next event
  ├── Serves other connections
  └── No blocking
  
When data is ready:
  ├── Background thread sends signal
  ├── Worker checks ready list next iteration
  ├── Sees data is ready
  └── Grabs bytes and ships to user
```

**Key**: Main worker never blocks. Background threads handle slow I/O. Main event loop stays free to serve others.

---

## 2.6 Critical Bug Every Event-Loop Author Writes Once

### The Stale Event Problem

Epoll_wait() returns a BATCH of events.

```
Suppose epoll_wait() returns 100 events
Handling event 1 can close the connection that event 7 points at
A new client connects and gets the recycled file descriptor
Event 7 is delivered to the new client!
The new client processes stale data meant for the old connection
```

### Nginx's Solution: Instance Counter

```c
c = event_list[i].data.ptr;
instance = (uintptr_t) c & 1;                    // Extract low bit
c = (ngx_connection_t *) ((uintptr_t) c & (uintptr_t) ~1);

if (c->fd == -1 || rev->instance != instance) {  // Check generation
    continue;  // Skip stale event
}
```

**How it works**:
- Structs are aligned, so low bit of pointer is always 0
- Nginx borrows that bit as a generation flag
- On connection reuse, flip the bit
- When event arrives, check if generation matches
- Free bit, no extra memory, one branch

**Cost**: One pointer subtraction + one branch

---

## 2.7 Key Concepts Summary

| Concept | Meaning |
|---------|---------|
| **Event Loop** | Endless cycle: sleep on epoll_wait() → process ready events → repeat |
| **Epoll** | Linux kernel facility tracking which connections have data |
| **Interest List** | Connections the worker wants kernel to watch |
| **Ready List** | Connections that currently have data/events |
| **epoll_wait()** | Blocking call that returns when any watched connection has data |
| **Context Switching** | Not needed between workers (one per core stays on core) |
| **Thread Pool** | Background threads handle slow I/O without blocking event loop |
| **Stale Events** | Events from closed connections delivered to new clients on recycled FDs |
| **Instance Counter** | Generation flag preventing stale events from corrupting new connections |

---

## 2.8 Why Nginx Changed Everything

**Old model**: Make per-connection worker cheaper
**New model**: Don't have a per-connection worker

**Impact**: 
- From handling 100 connections per machine → 10,000+ connections
- From 80 GB RAM → Megabytes
- From CPU thrashing on context switches → CPU doing actual work
- From one machine serving 100 → One machine serving thousands

One architectural question unlocked an order of magnitude improvement.
