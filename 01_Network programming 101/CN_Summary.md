# CN Summary: The Complete Picture

[← Previous](CN_Part_07-Debugging.md)


> Everything is a wrapper around seven system calls.

---

## 7.1 The Seven Calls Again

```mermaid
graph LR
    A["socket<br/>AF_INET<br/>SOCK_STREAM"] --> B["bind<br/>address<br/>htons"]
    B --> C["listen<br/>backlog"]
    C --> D["accept<br/>returns client_fd"]
    D --> E["read/write<br/>byte stream"]
    E --> F["close<br/>clean up"]
    
    D -.->|loop| D
    E -.->|loop| E
```

**These seven calls underlie everything**:
- Express.js
- nginx
- Apache
- Golang net package
- Python socket module
- Every RPC framework
- Every HTTP server

---

## 7.2 The OSI Stack We Touched

```mermaid
graph TD
    A["7 Application"]
    A --> A1["HTTP, HTTPS, gRPC, SSH, DNS"]
    
    B["6 Presentation"]
    B --> B1["Encoding: Protobuf, JSON, BCD"]
    
    C["5 Session"]
    C --> C1["Connection management"]
    
    D["4 Transport"]
    D --> D1["TCP, UDP, htons(), select()"]
    
    E["3 Network"]
    E --> E1["IP, routing, gethostbyname()"]
    
    F["2 Data Link"]
    F --> F1["Ethernet, MAC addresses"]
    
    G["1 Physical"]
    G --> G1["Copper, fiber, radio"]
```

---

## 7.3 Key Concepts Pyramid

```mermaid
graph TD
    A["Concepts"]
    
    B["Byte order<br/>htons/ntohl"]
    
    C["TCP = byte stream<br/>Need framing"]
    
    D["Concurrency<br/>fork vs select vs epoll"]
    
    E["Protocol design<br/>text vs binary<br/>length-prefix vs delimiter"]
    
    F["RPC makes network<br/>look like function calls<br/>But it's not"]
    
    G["Everything is<br/>a wrapper around<br/>socket/bind/listen/accept/read/write/close"]
    
    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
```

---

## 7.4 Server Patterns

```mermaid
graph TD
    A["Incoming clients"]
    
    B["Sequential"]
    B --> B1["socket()->bind()->listen()"]
    B1 --> B2["Loop: accept()->read()->write()->close()"]
    B2 --> B3["One at a time"]
    B3 --> B4["Simple, limited"]
    
    C["fork() per client"]
    C --> C1["socket()->bind()->listen()"]
    C1 --> C2["Loop: accept() then fork()"]
    C2 --> C3["Child handles client"]
    C3 --> C4["~1000 clients max"]
    
    D["select()"]
    D --> D1["socket()->bind()->listen()"]
    D1 --> D2["Loop: select() on all fds"]
    D2 --> D3["Handle ready ones"]
    D3 --> D4["~1024 clients, portable"]
    
    E["epoll()"]
    E --> E1["socket()->bind()->listen()"]
    E1 --> E2["epoll_wait() on interest list"]
    E2 --> E3["Handle only changed fds"]
    E3 --> E4["100k+ clients, Linux"]
```

---

## 7.5 Protocol Choices

```mermaid
graph TD
    A["Binary or Text?"]
    
    B["Text"]
    B --> B1["Human-readable"]
    B --> B2["HTTP/1.1, SMTP, FTP"]
    B --> B3["Easy to debug"]
    B --> B4["Verbose, slow"]
    
    C["Binary"]
    C --> C1["Compact, fast"]
    C --> C2["HTTP/2, gRPC, Redis"]
    C --> C3["Harder to debug"]
    C --> C4["Need tools"]
```

```mermaid
graph TD
    A["Framing?"]
    
    B["Fixed-length"]
    B --> B1["Simple, wasteful"]
    
    C["Delimiter"]
    C --> C1["Text protocols"]
    C --> C1 --> C2["HTTP headers: CRLF"]
    
    D["Length-prefix"]
    D --> D1["Modern protocols"]
    D --> D1 --> D2["gRPC, Redis, most binary"]
    
    E["TLV"]
    E --> E1["Self-describing"]
    E --> E1 --> E2["Forward-compatible"]
```

---

## 7.6 Debugging Decision Tree

```mermaid
graph TD
    A["Server not working"]
    
    B["Can't connect?"]
    B --> B1["strace: bind OK?"]
    B1 -->|Yes| B2["listen OK? accept called?"]
    B1 -->|No| B3["Port already bound? Permissions?"]
    B2 -->|No| B4["Server not listening properly"]
    B2 -->|Yes| C
    
    C["Connected but no data?"]
    C --> C1["strace: read() called?"]
    C1 -->|No| C2["Application not reading"]
    C1 -->|Yes| C3["tcpdump: data sent?"]
    C3 -->|No| C4["Client not sending"]
    C3 -->|Yes| C5["Server bug"]
    
    D["Slow response?"]
    D --> D1["tcpdump with timestamps"]
    D1 --> D2["Gap before response?"]
    D2 -->|Yes, large gap| D3["Server slow or timeout"]
    D2 -->|No gap| D4["Network slow"]
```

---

## 7.7 Performance Checklist

```mermaid
graph TD
    A["Optimize networking"]
    
    B["Connection level"]
    B --> B1["Connection pooling<br/>Skip handshake overhead"]
    
    C["Protocol level"]
    C --> C1["Binary not text"]
    C1 --> C2["gRPC beats REST"]
    
    D["Server level"]
    D --> D1["epoll > select > fork"]
    D1 --> D2["Thousands of clients"]
    
    E["Socket level"]
    E --> E1["SO_REUSEADDR"]
    E --> E2["TCP_NODELAY"]
    E --> E3["Buffer sizes"]
    
    F["OS level"]
    F --> F1["ulimit -n"]
    F --> F2["net.core.somaxconn"]
    F --> F3["TCP tuning"]
```

---

## 7.8 Quick Reference: System Calls

| Call | Purpose | Server? | Client? | Returns |
|------|---------|---------|---------|---------|
| **socket()** | Create fd | Yes | Yes | fd or -1 |
| **bind()** | Assign port | Yes | No | 0 or -1 |
| **listen()** | Queue conns | Yes | No | 0 or -1 |
| **accept()** | Get client | Yes | No | client_fd or -1 |
| **connect()** | Join server | No | Yes | 0 or -1 |
| **read()** | Receive | Yes | Yes | bytes or 0 or -1 |
| **write()** | Send | Yes | Yes | bytes sent or -1 |
| **close()** | Cleanup | Yes | Yes | 0 or -1 |

---

## 7.9 Key Takeaways

✅ **TCP = byte stream.** Framing is your job.

✅ **Byte order matters.** Use htons()/ntohl().

✅ **DNS blocks.** Can hang for seconds.

✅ **SIGPIPE kills.** Writing to closed peer terminates process.

✅ **Network ≠ function call.** RPC failures, timeouts, retries.

✅ **Concurrency options**: fork() (simple), select() (portable), epoll() (scalable).

✅ **Text protocols** are debuggable, **binary protocols** are fast.

✅ **Framing: three approaches** - fixed-length, delimiter, length-prefix.

✅ **gRPC = Protobuf + HTTP/2.** Codegen + binary = fast & typed.

✅ **Don't guess.** Use tcpdump, strace, curl to see what's really happening.

---

## 7.10 Reading for Each Context

**For interviews**:
- Know the seven calls by name
- Understand fork() vs select() trade-offs
- Explain TCP framing problem
- Describe at least one real protocol (HTTP, DNS, gRPC)

**For system design**:
- Estimate connections per server (fork ~ 1000, epoll ~ 100,000)
- Choose protocol (text = debug, binary = speed)
- Think about timeouts and retries
- Connection pooling for RPC

**For debugging**:
- tcpdump to see packets
- strace to see calls
- curl to see HTTP details
- Never guess; always inspect

---

## 7.11 The Pyramid, One More Time

```mermaid
graph TD
    Z["Framework<br/>Express, nginx, Flask"]
    
    Y["HTTP<br/>Text on TCP<br/>Framing: CRLF"]
    
    X["TCP<br/>Byte stream<br/>Ports, retransmission"]
    
    W["Socket API<br/>socket/bind/listen/accept/read/write"]
    
    V["IP<br/>Routing, addresses"]
    
    U["Physical layer<br/>Cables, radio"]
    
    Z --> Y
    Y --> X
    X --> W
    W --> V
    V --> U
```

**Every framework sits on TCP. TCP sits on seven calls. Seven calls sit on IP. IP sits on wires.**

---

## Summary

**Everything you touched in this lesson**:

| Part | Focus | Key Concept |
|------|-------|------------|
| 1 | Server | 7 system calls |
| 2 | Client | socket() → connect() → read/write |
| 3 | Concurrency | fork vs select vs epoll |
| 4 | HTTP & TLS | Text protocol, asymmetric then symmetric crypto |
| 5 | Protocol design | 3 framing approaches + encodings |
| 6 | RPC/gRPC | Marshal/unmarshal, Protobuf, HTTP/2 |
| 7 | Debugging | tcpdump, strace, curl |

---

**Go build something. Break it. Fix it with tcpdump.**

[← Previous](CN_Part_07-Debugging.md)
