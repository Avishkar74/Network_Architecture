# Part 1: Web Server Architecture History & Evolution

## 1.1 Understanding Connections vs Requests

**Connection**: An open channel between browser and server that persists over time
- A browser opens a connection first before sending requests
- Multiple requests can travel through one connection sequentially
- Connection remains open even when idle (no data being transferred)
- This persistence is key to the problem we'll solve

**Request**: Individual data exchanges through the connection
- JavaScript file request
- CSS file request
- API calls
- Each travels through the same connection

**Critical Insight**: A connection is NOT the same as a request. One connection = multiple requests over time.

---

## 1.2 Thread-Per-Connection Model (Late 1990s - Early 2000s)

### How It Works

```
User 1 → Server → Thread 1 (assigned)
User 2 → Server → Thread 2 (assigned)
User 3 → Server → Thread 3 (assigned)
...
User 10,000 → Server → Thread 10,000 (assigned)
```

**Process**:
1. Browser opens connection
2. Server spawns a new thread/process for that user
3. Thread stays alive as long as connection remains open
4. Thread dedicated entirely to that one user

### Why This Model Failed

#### Problem 1: Memory Exhaustion
- Each thread requires its own stack memory
- Default Linux stack size: **8 MB per thread**
- 10,000 users × 8 MB = **80 GB of RAM just for thread stacks**
- This happens BEFORE the application even processes work

**Real-world impact**: Scaling from 20 users to 10,000 users meant going from 160 MB to 80 GB of RAM.

#### Problem 2: Context Switching Overhead
- CPU can only execute one instruction per core at a time
- OS rapidly switches between threads (context switching)
- Each switch costs: save thread state + load new thread state
- At 10,000 threads: CPU spends 99% of time switching, 1% doing actual work

**CPU waste**: Like a teacher constantly switching between 10,000 students without teaching anything.

#### Problem 3: Connections Are Mostly Idle
- A connection spends most of its life waiting:
  - Waiting for client to send next request
  - Waiting for disk to read data
  - Waiting for backend database to respond
  - Waiting for network to carry bytes back
- Thread is BLOCKED the entire time (cannot do anything else)
- That thread holds its 8 MB of memory uselessly

### The C10K Problem (2002)

Named by Dan Kegel in 1999:
- **C** = Concurrent
- **10K** = 10,000 connections
- **Problem**: Hardware could support serving 10,000 people from one machine, but software couldn't

**Hardware limitations in 2002**:
- 1024 file descriptor limit (FD_SETSIZE in header)
- ulimit could not increase it (hardcoded in bitmap)
- 8 MB stack per thread
- CPU context switching limits

---

## 1.3 Apache's Attempts to Solve the Problem

### Apache 1.3: Prefork Model (1995)

**Idea**: Create a pool of processes at startup instead of per-request

```
Master Process
  ├── Worker 1 (pre-created)
  ├── Worker 2 (pre-created)
  ├── Worker 3 (pre-created)
  └── ... (N workers)
```

**Improvement**: Moves setup cost (fork + exec) off the request path
**Limitation**: Still one process parks on one connection

### Apache 2.0: Worker MPM with Threads (1999)

**Idea**: Use threads instead of processes to share memory

```
Process 1
  ├── Thread 1
  ├── Thread 2
  └── Thread 3
```

**Challenge**: pthreads on Linux were new, buggy, and reentrancy issues were poorly understood

### Apache 2.4: Event MPM (2004 onwards)

**Idea**: Separate listener thread parks idle keep-alives on epoll
- Listener thread: accepts new connections, hands off only active ones
- Worker threads: only work on connections with actual data

**Pattern**: All three were trying to make the per-connection worker cheaper, NOT questioning why there's a worker per connection at all.

---

## 1.4 Java's Answer: Connection Pooling & Servlet Model

### CGI Approach (1993)
```
Per request:
fork() → exec() → load interpreter → parse script → run → exit
```
Extremely expensive for each request.

### Servlet Approach (1997)
```
At startup: Load class, instantiate ONCE
Per request: Call service(req, res) method
Object outlives the request ← THE TRICK
```

**Strategy**: J2EE (1999) made multi-layer application servers default
- Web tier
- EJB tier  
- Database tier

**Core Pattern**: Take expensive setup off the request path, pay it once

### Connection Pooling
```
Pool of pre-created DB connections
Reuse same connection for multiple requests
Avoid TCP handshake overhead for each query
```

**Same fundamental pattern**: Amortize setup cost across multiple requests.

---

## 1.5 The 2002 Landscape

**What was true**:
- Hardware could serve 10,000 concurrent connections on one machine
- Software could not (thread-per-connection model)
- All optimization was on making the worker cheaper
- Everyone asking the same question

**What was needed**:
- Someone asking a DIFFERENT question
- Not: "How do I make the worker cheaper?"
- But: "Why is there a worker per connection at all?"

---

## 1.6 Key Concepts Summary

| Concept | Definition |
|---------|-----------|
| **Connection** | Persistent open channel, survives multiple requests |
| **Request** | Individual data exchange through connection |
| **Thread-Per-Connection** | One thread dedicated to one user, alive for entire connection duration |
| **Context Switching** | OS switching CPU between threads, expensive at scale |
| **C10K Problem** | Can't serve 10,000 concurrent connections with thread-per-connection model |
| **Prefork** | Pre-create process pool to avoid fork() per request |
| **Connection Pooling** | Reuse pre-created resources across requests |
| **Amortization** | Take expensive operation off request path, pay once |

---

## 1.7 Why Understanding History Matters

> "Understanding the evolution tells you what the limitation was, and what was proposed to fix it. Sometimes you look at the same limitation and fix it a completely different way. Understanding history is how you get to create a different timeline."

**Lesson**: Every design choice in this era was answering a specific constraint. That constraint changed. Virtual threads in Java, Goroutines in Go brought thread-per-connection back when memory costs dropped. Knowing which rules are laws and which are habits is essential.
