# Part 8 — Revision & Quiz Preparation

[← Previous](07_real_world_server_architectures.md)



---

## The Four Core Ideas

The entire session circles around four unifying concepts. **Know these cold.**

### Core Idea #1: Amortise Setup

> **Pay the cost once, not per request.**

Every approach in this course — from pre-forking in [Part 1](01-scaling-servers.md) to FastCGI in [Part 4](04-fastcgi.md) to nginx's worker pool in [Part 7](07-real-world-server-architectures.md) — follows this pattern:

- **Fork-per-request:** No amortisation. Pay full process-creation cost on every request.
- **Pre-fork:** Amortise by creating workers once at startup.
- **FastCGI:** Amortise by keeping long-lived worker processes.
- **Servlet thread pools:** Amortise by creating threads once at startup.

**The question to ask:** "Where is the setup cost being paid — on every request, or once at startup?"

### Core Idea #2: Nothing Is Free Per Connection

> **Holding a connection costs memory. Period.**

Whether it's an OS thread (8 MB stack), a goroutine (2 KB initial, grows on demand), or just a socket entry in an epoll set (minimal), holding a connection costs resources.

You cannot have a million concurrent connections without paying for a million entries in *something* — either OS threads, or goroutines, or epoll entries, or some other mechanism.

**The question to ask:** "What data structure holds this connection, and how much does each entry cost?"

### Core Idea #3: Framing Is Length or Delimiter

> **When you receive a stream of bytes, how do you know where one message ends and the next begins?**

The session showed this theme repeatedly:
- CGI: blank-line delimiter (see [Part 3](03-cgi.md)).
- FastCGI: both length (per-record header) and delimiter (empty record) (see [Part 4](04-fastcgi.md)).
- HTTP: content-length (length) or chunked encoding (delimiter).

**The question to ask:** "Is this protocol using length, delimiter, or both?"

### Core Idea #4: Concurrency = Throughput × Latency (Little's Law)

> **How many connections in flight = (requests per second) × (seconds per request)**

From [Part 6](06-scaling-limits.md):
- 10,000 req/s at 10 ms latency = 100 connections in flight.
- 10,000 req/s at 1000 ms latency = 10,000 connections in flight.

Same traffic, 100× more connections, because latency went up 100×. **Latency is a memory bug.**

**The question to ask:** "If latency increases 10×, connections in flight increase 10×. Can my system handle that?"

---

## Important Numbers — Memorise These

| Number | Meaning | Context |
|---|---|---|
| **1024** | `FD_SETSIZE` hard limit; default `ulimit -n`; the "K" in C10K | [Part 2](02-select-epoll.md), [Part 6](06-scaling-limits.md) |
| **10,000** | C10K — Dan Kegel's 1999 problem statement | [Part 6](06-scaling-limits.md) |
| **10,000,000** | C10M — Robert Graham's 2013 argument for kernel bypass | [Part 6](06-scaling-limits.md) |
| **2–3 million** | Demonstrated connections on a single modern server today | [Part 6](06-scaling-limits.md) |
| **8 MB** | Default OS thread stack (reserved upfront) | [Part 6](06-scaling-limits.md) |
| **2 KB** | Initial goroutine stack (grows on demand) | [Part 6](06-scaling-limits.md) |
| **4,000×** | Goroutine vs OS thread memory ratio | [Part 6](06-scaling-limits.md) |
| **O(n)** | `select()` scan cost — kernel scans every fd on every call | [Part 2](02-select-epoll.md) |
| **O(ready)** | `epoll()` scan cost — kernel returns only ready fds | [Part 2](02-select-epoll.md) |
| **hundreds of ns** | Cost per syscall (worsened by Spectre/Meltdown mitigations) | [Part 6](06-scaling-limits.md) |

---

## Formula Sheet

### Little's Law (Concurrency = Throughput × Latency)

```
Connections in flight = (Requests per second) × (Seconds per request)

Example:
10,000 req/s × 0.05 s/req = 500 connections
10,000 req/s × 0.5 s/req = 5,000 connections
10,000 req/s × 1.0 s/req = 10,000 connections
```

### Memory Cost of N Concurrent Connections

**OS threads:**
```
Total memory = N × 8 MB (stack) + overhead
Example: 1,000 threads = 8 GB just in stacks
```

**Goroutines:**
```
Total memory = N × 2 KB (initial) + growth as needed
Example: 1,000,000 goroutines ≈ 2 GB or less, often much less
```

### TCP Setup Cost

From [Part 1](01-scaling-servers.md):
```
fork() + exec() cost >> accept() cost
This is why pre-fork amortises setup.
```

### Syscall Tax

From [Part 6](06-scaling-limits.md):
```
One syscall = hundreds of nanoseconds + Spectre/Meltdown mitigations
High-frequency syscalls = significant latency at scale
Solutions: sendfile(), io_uring (fewer syscalls), kernel bypass (no syscalls)
```

---

## Most Important Things to Memorise

1. **The four walls** (from [Part 6](06-scaling-limits.md)): file descriptors, memory, context switches, the queue.

2. **C10K and C10M**: **Kegel (1999) = C10K (10,000); Graham (2013) = C10M (10,000,000)**. Don't swap them.

3. **select vs epoll**:
   - `select()`: O(n) on every call; 1024 hard limit; portable.
   - `epoll()`: O(ready); no limit; Linux-specific.

4. **Goroutines vs OS threads**: **8 MB (OS thread) vs 2 KB (goroutine) = 4,000× difference**. Still both ultimately run on epoll (Go's netpoller).

5. **FastCGI record sequence**: `BEGIN_REQUEST → PARAMS (+empty) → STDIN (+empty) → [process] → STDOUT (+empty) → STDERR → END_REQUEST`.

6. **CGI environment variables**: `User-Agent: curl` becomes `HTTP_USER_AGENT=curl` (uppercase, dashes→underscores, `HTTP_` prefix).

7. **Amortise setup**: Prefork (startup cost), FastCGI (startup cost), servlet thread pools (startup cost) — all variations of paying once, not per request.

8. **Little's Law**: connections in flight = throughput × latency. Latency directly multiplies concurrent connections.

9. **Apache's keep-alive problem**: In prefork/worker, a keep-alive connection ties up a process/thread. Event MPM fixes it via epoll.

10. **nginx is the modern standard**: master + workers (per CPU), epoll, sendfile, reverse proxy, caching, TLS, thread pool for blocking I/O.

11. **sendfile()** avoids copying file data through user space — critical for static file serving.

12. **SO_REUSEPORT** lets the kernel distribute new connections across multiple worker processes.

---

## Common Confusions — Cleared Up

| Confusion | Reality |
|---|---|
| **fork-per-request** = **prefork** | No. Fork-per-request pays setup cost on every request. Prefork pays it once. Prefork is the production fix. |
| **Threads are free** | No. Each OS thread costs 8 MB stack upfront. Not free; costly. Goroutines are cheaper (2 KB initial). |
| **event-driven = single-threaded** | No. Event-driven = event loop (epoll). Can still have threads. nginx uses both. |
| **epoll has a timeout like select** | No. epoll has no timeout argument. If you want timeout behavior, you set it on the sockets themselves or use a separate timer. |
| **Keep-alive always bad** | No. Prefork/worker MPM make it bad (idle connection = tied-up process/thread). Event MPM solves it (idle connection = just an epoll entry). |
| **HAProxy is a web server** | No. HAProxy is a load balancer. nginx is a web server (and can also reverse-proxy). |
| **Varnish replaces your origin server** | No. Varnish is a cache *in front of* your origin server, reducing its load. |
| **Sendfile = compression** | No. Sendfile = zero-copy file-to-socket. It's fast. Compression is separate (and can be done in a thread pool to avoid blocking the event loop). |
| **Goroutines run on a single thread** | No. The Go runtime multiplexes goroutines onto a small number of OS threads using its own scheduler (on top of epoll). |
| **C10K is outdated** | No. The *problem* (scaling to many connections) is timeless. The number "10K" was 1999's target; we've moved to millions, but the underlying scaling question is the same. |

---

## 5-Minute Revision

If you have 5 minutes before the exam, memorise this:

- **Four walls:** fds, memory, context switches, queue.
- **C10K (1999, Kegel, 10K) → C10M (2013, Graham, 10M)** — don't swap.
- **select**: O(n), 1024 limit. **epoll**: O(ready), no limit.
- **8 MB (OS thread) vs 2 KB (goroutine)** — remember the direction.
- **Amortise setup** — prefork, FastCGI, thread pools all do this.
- **Concurrency = throughput × latency** (Little's Law).
- **Event MPM fixes keep-alive** via epoll.
- **nginx** = master + workers + epoll + sendfile + reverse proxy.
- **Core Idea #4 is the most important:** latency directly multiplies memory cost.

---

## 25–30 Multiple Choice Questions

### Question 1
Which of the following is NOT one of the four walls?
- A) File descriptors
- B) Memory per connection
- C) Network latency
- D) Context switches

**Answer: C** — Network latency is not listed as one of the four walls. The four walls are: file descriptors, memory, context switches, and the queue (queueing/latency trade-off).

---

### Question 2
Dan Kegel named the _____ problem in 1999; Robert Graham argued for kernel bypass to scale to _____ in 2013.

- A) C10M, C10K
- B) C10K, C10M
- C) C1000, C100K
- D) C100K, C1M

**Answer: B** — Kegel named C10K (10,000 connections); Graham argued for C10M (10,000,000) via kernel bypass.

---

### Question 3
What is `FD_SETSIZE` and why does it matter?

- A) The maximum network packet size
- B) The compile-time maximum number of fds that `select()` can watch (typically 1024)
- C) The maximum size of a TCP window
- D) The total memory allocated to file descriptor tables

**Answer: B** — `FD_SETSIZE` is a hard, compiled-in limit (typically 1024) on the width of the `fd_set` bitmap used by `select()`. This is the origin of the 1024 hard ceiling.

---

### Question 4
An OS thread's default stack size is _____, and a goroutine's initial stack is _____.

- A) 2 KB, 8 MB
- B) 8 MB, 2 KB
- C) 1 MB, 512 bytes
- D) 8 KB, 64 bytes

**Answer: B** — OS thread = 8 MB (reserved upfront), goroutine = 2 KB (initial, grows on demand). The ratio is 4,000×.

---

### Question 5
The `select()` call is O(___) on every call because the kernel _____.

- A) O(log n), binary-searches ready fds
- B) O(ready), only returns ready fds
- C) O(n), scans every fd in the set regardless of readiness
- D) O(1), cached by the OS

**Answer: C** — `select()` is O(n) because the kernel must scan every fd in the set on every call, regardless of how many are ready. This is the key inefficiency epoll fixes.

---

### Question 6
`epoll()` is O(___) because _____.

- A) O(n), it's essentially the same as select
- B) O(ready), only fds that fire events are returned
- C) O(log n), it uses an internal hash table
- D) O(1), all operations are pre-computed

**Answer: B** — `epoll()` is O(ready) because the kernel only returns fds that actually became ready; idle fds are not rescanned.

---

### Question 7
The five FastCGI record types in a request, in order, are _____.

- A) BEGIN_REQUEST, PARAMS, STDIN, STDOUT, STDERR, END_REQUEST
- B) BEGIN_REQUEST, STDIN, PARAMS, STDOUT, END_REQUEST, STDERR
- C) PARAMS, BEGIN_REQUEST, STDIN, STDOUT, END_REQUEST, STDERR
- D) BEGIN_REQUEST, QUERY_STRING, STDIN, STDOUT, END_REQUEST, STDERR

**Answer: A** — The correct order is `BEGIN_REQUEST → PARAMS (+ empty) → STDIN (+ empty) → [process] → STDOUT (+ empty) → STDERR → END_REQUEST`.

---

### Question 8
An HTTP header `Content-Type: application/json` becomes the CGI environment variable _____.

- A) `CONTENT_TYPE=application/json`
- B) `HTTP_CONTENT_TYPE=application/json`
- C) `HEADER_CONTENT_TYPE=application/json`
- D) `CONTENT-TYPE=application/json`

**Answer: A** — Special CGI variables like `CONTENT_TYPE`, `CONTENT_LENGTH`, and `REQUEST_METHOD` don't get the `HTTP_` prefix or dash-to-underscore conversion. Generic headers do (e.g., `User-Agent → HTTP_USER_AGENT`).

---

### Question 9
Why does Apache's prefork MPM struggle with keep-alive connections?

- A) It cannot parse the Connection header
- B) Each process is blocked on one client and cannot serve others while waiting for the next request
- C) The kernel doesn't support TCP keep-alive
- D) HTTP keep-alive isn't implemented in early Apache versions

**Answer: B** — In prefork, a process is blocked on a single client. If a keep-alive client goes idle, that entire process waits for the next request and cannot serve other clients. Event MPM fixes this with an event loop.

---

### Question 10
Apache's **event MPM** solves the keep-alive problem by _____.

- A) Lowering the KeepAliveTimeout setting
- B) Running threads on an epoll loop so idle keep-alive clients don't block threads
- C) Refusing to support keep-alive connections
- D) Using more processes

**Answer: B** — Event MPM adds epoll to worker MPM. Threads run an event loop instead of blocking on individual sockets, so idle keep-alive clients are just entries in the epoll set and don't tie up a thread.

---

### Question 11
HAProxy is primarily a _____, not a _____.

- A) web server, reverse proxy
- B) caching proxy, load balancer
- C) load balancer, web server
- D) web server, load balancer

**Answer: C** — HAProxy is a **load balancer** (sits in front of your servers and distributes connections to them). It is not a web server (does not generate responses). It can reverse-proxy connections.

---

### Question 12
Varnish is a _____ reverse proxy, meaning it _____.

- A) caching, stores responses and serves them directly to clients without contacting the origin
- B) filtering, rejects requests that don't match a pattern
- C) load-balancing, distributes requests across multiple origins
- D) stateful, maintains session state for each client

**Answer: A** — Varnish is a **caching** reverse proxy. It sits in front of the origin server and stores responses in memory. If a request is cache-hit, it serves the cached response directly to the client without contacting the origin.

---

### Question 13
nginx's worker processes are typically _____ per _____.

- A) one, CPU core
- B) one, client
- C) ten, server
- D) one, gigabyte of RAM

**Answer: A** — nginx typically spins up one worker process per CPU core. This is a common practice to maximize parallelism without excessive context switching.

---

### Question 14
`sendfile()` is valuable for serving static files because _____.

- A) It compresses the file on the fly
- B) It encrypts the file for HTTPS
- C) It moves the file directly to the socket without copying through user space
- D) It automatically caches the file in memory

**Answer: C** — `sendfile()` does zero-copy file-to-socket I/O. The kernel reads the file and writes it to the socket directly, avoiding user-space buffer copies. This is fast and memory-efficient.

---

### Question 15
Which syscall mechanism is most associated with Windows?

- A) epoll
- B) select
- C) kqueue
- D) IOCP

**Answer: D** — **IOCP** (I/O Completion Ports) is Windows' equivalent to epoll/kqueue — it's a kernel event mechanism for monitoring many sockets.

---

### Question 16
Goroutines are efficient compared to OS threads because _____.

- A) The Go runtime doesn't use the kernel at all
- B) The Go runtime multiplexes many goroutines onto a small number of OS threads using epoll (the netpoller)
- C) Goroutines are compiled to pure machine code with no overhead
- D) Go servers don't support more than 100 concurrent connections anyway

**Answer: B** — The Go runtime's scheduler (built on epoll via the netpoller) multiplexes many goroutines onto a small number of actual OS threads. This is why goroutines are so lightweight (2 KB initial) compared to OS threads (8 MB).

---

### Question 17
Little's Law states that the number of concurrent connections is approximately _____.

- A) The sum of all request sizes
- B) The number of CPU cores squared
- C) Throughput (requests/sec) × Latency (seconds/request)
- D) The ulimit -n setting

**Answer: C** — **Concurrency = Throughput × Latency**. If requests arrive at 10,000/sec and each takes 50 ms, you're holding roughly 500 connections at once. This is Little's Law applied to servers.

---

### Question 18
If latency increases from 100 ms to 1000 ms but throughput stays constant at 10,000 req/sec, the number of concurrent connections _____.

- A) Stays the same
- B) Increases by 10×
- C) Decreases to 1/10 the original
- D) Is unpredictable

**Answer: B** — By Little's Law, 10,000 req/sec × 0.1 s = 1,000 connections (original). 10,000 req/sec × 1.0 s = 10,000 connections (after latency increase). Latency directly multiplies concurrent connections.

---

### Question 19
The PDF describes this as "Core Idea #4" and links it to a memory problem: _____.

- A) Framing is length or delimiter
- B) Concurrency = throughput × latency; slowness is a memory bug
- C) Amortise setup cost
- D) Kernel bypass is always faster

**Answer: B** — The PDF explicitly states "slowness is a memory bug" in the context of Little's Law. If requests get slow, you hold more connections, using more memory. The only real fix is reducing latency (often via async work).

---

### Question 20
`SO_REUSEPORT` allows _____.

- A) A single process to listen on many ports
- B) The kernel to distribute incoming connections across multiple worker processes on the same port
- C) A socket to accept multiple connections simultaneously
- D) An application to reuse a port immediately after closing (avoiding TIME_WAIT)

**Answer: B** — `SO_REUSEPORT` enables multiple processes to bind to the same port. The kernel then distributes new incoming connections across those processes, effectively load-balancing at the kernel level.

---

### Question 21
The default `ulimit -n` on most Linux distributions is _____, which ties directly to _____ and _____.

- A) 1024; C10K; FD_SETSIZE
- B) 65536; C10M; epoll
- C) 512; memory limit; connection count
- D) Unlimited; number of processes; file size

**Answer: A** — **1024** is the default `ulimit -n` (file descriptor soft limit), which is the same as `FD_SETSIZE` (the hard limit for `select()`), and "1024" is the "K" in C10K (Dan Kegel's 1999 problem statement). All three are the same number, not coincidentally.

---

### Question 22
CGI programs read the request body from _____ and write the response to _____.

- A) stdin, stdout
- B) environment variables, stderr
- C) a socket, a pipe
- D) /dev/stdin, /dev/stdout

**Answer: A** — In CGI, the request body (for POST) comes from stdin; the response (headers + body) is written to stdout. The server redirects these before `exec()`-ing the CGI program.

---

### Question 23
FastCGI uses a _____ to delimit the end of a stream (e.g., end of PARAMS or STDIN).

- A) Blank line
- B) Special marker byte (0xFF)
- C) Empty record (length = 0)
- D) A length field in the previous record

**Answer: C** — An **empty record** (content length = 0) signals "no more records of this type." This is the delimiter-style framing for FastCGI record streams.

---

### Question 24
Which of the following is NOT a true statement about nginx?

- A) It uses a master process and worker processes
- B) Each worker process typically runs on a single CPU core
- C) It uses `sendfile()` for static file serving
- D) It cannot handle HTTPS connections

**Answer: D** — nginx **absolutely can** handle HTTPS connections. In fact, TLS termination (handling HTTPS so upstream servers don't have to) is one of nginx's key features.

---

### Question 25
The syscall tax is the _____ cost per syscall, made worse by _____.

- A) Latency; slow networks
- B) Hundreds of nanoseconds; Spectre/Meltdown mitigations
- C) Throughput; compression overhead
- D) Memory; goroutine allocation

**Answer: B** — Each syscall costs hundreds of nanoseconds. Spectre and Meltdown mitigations made this **worse**, not better, by adding extra CPU cache flushes and validation on kernel boundary crossings.

---

### Question 26
Kernel bypass techniques like DPDK, netmap, mTCP, and Seastar are designed to _____.

- A) Make select() faster
- B) Implement TCP in user space, avoiding the kernel entirely (for well-known internal networks)
- C) Add encryption to network packets
- D) Load-balance connections across multiple cores

**Answer: B** — These techniques implement networking (often TCP) in user space, bypassing the kernel entirely. This eliminates the syscall tax but requires sacrificing OS tools (exception handling, routing, etc.) and is only practical for controlled, internal networks.

---

### Question 27
`io_uring` is an approach to reducing the syscall tax by _____.

- A) Eliminating the kernel entirely (like DPDK)
- B) Submitting a batch of operations through a shared ring buffer instead of one syscall per operation
- C) Using a single `select()` call to monitor all sockets
- D) Implementing TCP in user space

**Answer: B** — `io_uring` is a modern Linux mechanism that lets you submit multiple I/O operations in a batch via a shared ring buffer, reducing the number of individual syscalls and thus reducing the per-call overhead.

---

### Question 28
When comparing Apache's event MPM to Varnish, which statement is true?

- A) Varnish uses more memory because it maintains multiple processes
- B) Both use worker threads running on epoll/kqueue
- C) Varnish is primarily a web server; event MPM is a caching proxy
- D) Event MPM is primarily used for caching upstream responses

**Answer: B** — Both Apache's event MPM and Varnish use worker threads running on epoll (Linux) or kqueue (BSD), multiplexing many concurrent sockets per thread.

---

### Question 29
The "four walls" are an exhaustive list of _____ that you will eventually hit when scaling servers.

- A) Programming languages you can use
- B) Physical/OS-level limits
- C) Types of TCP packets
- D) HTTP header fields

**Answer: B** — The four walls are physical/OS-level constraints: file descriptors, memory, context switches, and the queue (queueing/latency). Every scaling strategy dodges one of these four.

---

### Question 30
Which of the following best describes "Core Idea #1 — Amortise Setup"?

- A) Always use event-driven I/O
- B) Pre-create workers/threads at startup so the cost is paid once, not per request
- C) Avoid forking entirely
- D) Use the smallest possible socket buffer

**Answer: B** — Amortising setup means paying the (expensive) cost of creating workers/threads **once** at startup, not on every single request. This is the philosophy behind pre-forking, FastCGI, and servlet thread pools.

---

## Summary

You now have:

1. **Four core ideas** to guide your thinking across the entire session.
2. **Important numbers** to memorise exactly.
3. **Key formulas** (Little's Law, memory costs).
4. **Common confusions** cleared up explicitly.
5. **30 MCQs** covering every major concept from the session.

Go over the four core ideas one more time, memorise the numbers, and you're ready.

---

[← Previous](07_real_world_server_architectures.md)
