# LAST-MINUTE REVISION: WHAT YOU MUST REMEMBER

[← Previous](07_quiz.md)


## TOP 10 CONCEPTS THAT WILL DEFINITELY BE ON THE EXAM

### 1. TCP 3-WAY HANDSHAKE

```
Client → SYN (seq=1000) → Server
Client ← SYN-ACK (seq=5000, ack=1001) ← Server
Client → ACK (seq=1001, ack=5001) → Server
```

**Why 3, not 2?**
- SYN announces client's ISN
- SYN-ACK announces server's ISN
- ACK confirms both ISNs

**Remember:** Each direction needs its own ISN confirmed.

---

### 2. ONE LAYER'S HEADERS ARE ANOTHER LAYER'S BODY

```
Ethernet Frame [MAC header] [IP packet]
  └─ IP packet [IP header] [TCP segment]
      └─ TCP segment [TCP header] [HTTP message]
```

**This is the entire point of the OSI model.**

---

### 3. SMS = 140 BYTES (NOT ARBITRARY)

Three stacked limits:
```
272 (MTP2 SIF hard ceiling)
  └─ 200 (MAP sm-RP-UI)
      └─ 140 (TP-UD chosen to fit one signaling packet)
```

**GSM-7:** 140 × 8 ÷ 7 = **160 characters**
**UCS-2 (emoji):** 140 ÷ 2 = **70 characters**

One emoji silently halves your message length.

---

### 4. TCP vs UDP AT L4

| Feature | TCP | UDP |
|---------|-----|-----|
| Handshake | 3-way | None |
| Reliability | Guaranteed | Best effort |
| Ordering | In-order | Any order |
| Latency | Higher | Lower |
| Overhead | 20B header | 8B header |
| Use | Correctness matters | Speed matters |

---

### 5. OSI LAYERS: MEMORIZE ALL 7

```
L7: Application (HTTP, SMTP, FTP, DNS, SSH)
L6: Presentation (encryption, compression)
L5: Session (auth, conversation state)
L4: Transport (TCP, UDP, QUIC)
L3: Network (IP, routing)
L2: Data Link (Ethernet, MAC, ARP, Wi-Fi)
L1: Physical (cables, fiber, radio, space)
```

**Bottom line:** One layer's headers = next layer's payload.

---

### 6. SYN COOKIES PREVENT SYN FLOODS

**Attack:** Spoofed SYNs fill accept queue

**Defense:** Encode state in ISN itself
```
Server: hash(4-tuple, timestamp, MSS) → ISN
Client: ACK with ack = ISN + 1
Server: recompute hash, validate, reconstruct
```

**No backlog entry ever created!**

---

### 7. MAIL FROM ≠ FROM:

```
MAIL FROM:<attacker@evil.com>       ← Envelope (routing)
From: Bank of America <bank@example.com>  ← Header (display)
```

**Mail client shows:** "From: Bank of America"

**Reality:** Message from attacker@evil.com

This is why SPF/DKIM/DMARC are patches bolted on 40 years later.

---

### 8. QUIC SOLVES HEAD-OF-LINE BLOCKING

**HTTP/2 problem:**
```
Stream 1: [LOST packet] ← blocks all streams
Stream 2: [waiting...]
Stream 3: [waiting...]
```

**QUIC solution:**
```
Stream 1: [LOST] ← only this stream waits
Stream 2: [continues normally]
Stream 3: [continues normally]
```

Each stream has independent sequencing.

---

### 9. Wi-Fi CAN'T DETECT COLLISIONS (ONLY AVOID)

**Ethernet:** CSMA/CD
```
Transmit → Listen → Detect collision → Back off
```

**Wi-Fi:** CSMA/CA
```
Listen → Sense channel → Back off → Transmit → ACK required
~2 ms of contention delay before frame even leaves your device
```

**Why?** Radio can't listen while transmitting.

---

### 10. RTT TAXES ARE THE ENEMY

```
TCP: 1 RTT overhead
TCP + TLS 1.2: 3 RTTs overhead
TCP + TLS 1.3: 2 RTTs overhead
QUIC + HTTP/3: 1 RTT overhead (first connection!)
```

**The entire modern internet is attacking the RTT tax.**

Mumbai to Virginia ≈ 190 ms. Speed of light ≠ upgradeable.

---

## CRITICAL NUMBERS TO KNOW

| What | Value | Context |
|------|-------|---------|
| TCP MSS | ~1460 bytes | 1500 MTU - headers |
| Ethernet MTU | 1500 bytes | Typical |
| SMS payload | 140 octets | GSM-7 limit |
| SMS (emoji) | 70 chars | UCS-2 limit |
| SS7 SIF | 272 octets | MTP2 hard limit |
| Backlog queue | listen(fd, n) | Not max connections |
| TIME_WAIT | 2 MSL (~30 sec) | Before reuse |
| Wi-Fi contention | ~2 ms | Local delay |
| TCP ISN | 32 bits | Sequence space |
| SS7 FSN | 7 bits | Wraps at 128 |
| SMTP port (client) | 587 | STARTTLS |
| SMTP port (relay) | 25 | Plaintext |
| POP3 | 110 | Plaintext |
| IMAP | 143 | Plaintext |
| FTP control | 21 | Always |
| FTP data | 20 (active) / random (passive) | Depends on mode |

---

## SOCKET SYSCALLS: ROTE MEMORIZATION

**Server:**
```
socket() → bind() → listen() → accept() → read/write → close()
```

**Client:**
```
socket() → [no bind] → connect() → read/write → close()
```

**Key difference:** Server binds and listens; client connects directly.

---

## TCP STATES THAT TRAP STUDENTS

| State | Meaning | Common Bug |
|-------|---------|-----------|
| ESTABLISHED | Both sides ready | Normal state |
| FIN_WAIT_1 | Sent FIN, waiting for ACK | Normal close |
| CLOSE_WAIT | **Received FIN, app hasn't closed yet** | **App forgot close()** |
| TIME_WAIT | Waiting 2 MSL before reuse | Why "address in use" |

**CLOSE_WAIT is NOT a network problem—it's an app bug.**

---

## PROTOCOL PORTS: MEMORIZE THESE

| Port | Protocol | Note |
|------|----------|------|
| 25 | SMTP relay | Server-to-server |
| 587 | SMTP submission | Client-to-server (use this) |
| 465 | SMTPS | Implicit TLS |
| 110 | POP3 | Plaintext |
| 995 | POP3S | TLS |
| 143 | IMAP | Plaintext |
| 993 | IMAPS | TLS |
| 21 | FTP control | Always |
| 80 | HTTP | Plaintext |
| 443 | HTTPS | TLS |

---

## ENCAPSULATION: THE FUNDAMENTAL PATTERN

**TCP/IP:**
```
Ethernet [MAC] IP [IP hdr] TCP [TCP hdr] HTTP "GET /"
          ↑────────────────────────────────────────↑
          One frame's payload is another layer's packet
```

**SS7:**
```
MTP2 [MSU] MTP3 [routing] SCCP [transport] TCAP [txn] MAP [SMS] TP-UD "Hello"
     ↑─────────────────────────────────────────────────────────────────────↑
     Same picture, different network
```

**The pattern:** As you go up the stack, each layer adds a header (encapsulation).

---

## COMMON EXAM TRAPS

### Trap 1: listen() Backlog
**Wrong:** "listen(fd, 1) means 1 concurrent connection"
**Right:** "listen(fd, 1) means accept queue holds 1 pending connection"

### Trap 2: CLOSE_WAIT
**Wrong:** "Network problem, need to tune TCP"
**Right:** "Application bug—app forgot to close()"

### Trap 3: TIME_WAIT
**Wrong:** "Useless delay we should get rid of"
**Right:** "Prevents confused packets when port is reused"

### Trap 4: MAC vs IP
**Wrong:** "Both are addresses, use them interchangeably"
**Right:** "MAC is L2 (local), IP is L3 (routable). Different scope."

### Trap 5: MAIL FROM vs From:
**Wrong:** "Both are the same, just displayed differently"
**Right:** "Envelope (routing) vs header (display). Can be different people!"

### Trap 6: SYN Consume Sequence
**Wrong:** "SYN doesn't use a sequence number because it has no data"
**Right:** "SYN consumes a sequence number so it's not confused with a retransmit"

### Trap 7: Congestion Control
**Wrong:** "All TCP algorithms wait for packet loss"
**Right:** "BBR measures bandwidth×RTT instead of waiting for loss"

### Trap 8: FTP Modes
**Wrong:** "Active mode is modern, passive is old"
**Right:** "Active is old (blocked by NAT), passive is modern"

### Trap 9: SMS 140 Bytes
**Wrong:** "Arbitrary choice by engineers"
**Right:** "Three stacked limits: 272 (SIF), 200 (MAP), 140 (fit in one packet)"

### Trap 10: Wi-Fi Contention
**Wrong:** "Same as Ethernet CSMA/CD"
**Right:** "CSMA/CA: can't detect, must avoid (~2 ms delay)"

---

## ONE-SENTENCE SUMMARIES

1. **Sockets:** Seven syscalls make a server; client mirrors them without bind/listen.

2. **OSI:** Seven layers, each refusing to care about the others. One layer's header = next layer's body.

3. **SS7:** Separated signaling from voice in 1975. TCP/IP is the internet's SS7.

4. **SMS:** 140 bytes because three nested limits (272→200→140) force 1 SMS = 1 packet.

5. **TCP:** 3-way handshake confirms both ISNs. 4-way close because both sides close independently.

6. **UDP:** Connectionless, no guarantees. You can hold the spec in your head.

7. **QUIC:** HTTP/2's head-of-line blocking, gone. Runs in browser, deploys in days.

8. **SMTP:** Envelope ≠ headers. Text protocol, extensible, never was secure.

9. **POP3:** Mail on client. Simple. 4 verbs.

10. **IMAP:** Mail on server. Sync across devices. Server-side search.

11. **FTP:** Active (blocked by NAT), passive (modern). Two connections.

12. **SYN Cookies:** No state in server. Hash in ISN. Client hands it back.

13. **Wi-Fi:** Can't listen while transmitting. CSMA/CA avoids collisions, ~2 ms delay.

14. **BBR:** Bandwidth × RTT. Works on lossy links. Google deploys in days (userspace).

15. **Layers:** Starlink packet goes to space, comes back, arrives unchanged at internet.

---

## IF YOU HAVE 5 MINUTES

Memorize ONLY these:

1. **TCP:** SYN → SYN-ACK → ACK (3-way)
2. **Socket server:** socket → bind → listen → accept → read/write → close
3. **OSI:** 7 layers, one layer's headers = next layer's body
4. **SMS:** 140 bytes = 160 chars (GSM-7) = 70 chars (emoji)
5. **QUIC:** Fixes HTTP/2 head-of-line blocking (independent streams)

---

## IF YOU HAVE 15 MINUTES

Add these:

6. **TCP close:** FIN-ACK → ACK → FIN-ACK → ACK (4-way), then TIME_WAIT
7. **SYN cookies:** Hash state into ISN, no backlog needed
8. **MAIL FROM vs From:** Envelope (routing) vs header (display)
9. **SS7:** Separated signaling from voice (in-band → out-of-band)
10. **FTP:** Active (blocked), passive (modern)
11. **Ports:** 25/587/465 (SMTP), 110/143 (POP3/IMAP), 21 (FTP)
12. **Wi-Fi:** CSMA/CA (avoid collisions), ~2 ms before frame leaves
13. **BBR:** Bandwidth×RTT, works on lossy links
14. **POP3 vs IMAP:** State on client vs state on server
15. **Congestion control:** Reno/CUBIC lose on loss, BBR thrives on lossy links

---

## ESSAY QUESTION: "WHAT IS THE MOST IMPORTANT IDEA IN THIS LECTURE?"

**Best answer:**

"The most important idea is that one layer's headers are another layer's payload. This is why the OSI model, which is from 1984, has outlived nearly everything built on top of it. You can run TCP/IP over Ethernet, or over Wi-Fi, or over a Starlink terminal orbiting 550 km up—and the IP packet arrives unchanged. That's the power of layering. The same idea applies to SS7 (MTP2 ⊃ MTP3 ⊃ SCCP ⊃ TCAP ⊃ MAP ⊃ SMS-SUBMIT), which is 50 years old. Two committees, separated by decades, invented the same architecture because it works. Layering is the fundamental principle of network design."

---

## PRACTICE THIS BEFORE THE EXAM

### 1. Draw from Memory
- TCP 3-way handshake (with sequence numbers)
- TCP 4-way close (with states)
- OSI layer stack (all 7 layers)
- SMS encapsulation (MTP2 down to TP-UD)

### 2. Answer Without Notes
- Explain why SMS is 140 bytes
- Explain why SYN and FIN consume sequence numbers
- Explain why TIME_WAIT exists
- Explain why CLOSE_WAIT means app bug
- Explain MAIL FROM vs From:

### 3. Decode These
- FTP PASV response: (127,0,0,1,117,48) → port?
- TCP header: seq=1000, ack=5001 in SYN-ACK → what does each mean?
- GSM-7 vs UCS-2 → character counts?

### 4. Complete These
- Socket server: socket → ____ → ____ → accept → ...
- TCP handshake: SYN → ____ → ____
- SMTP ends with: ____
- FTP has ____ connections

---

## EXAM DAY STRATEGY

**First 10 minutes:** Read all questions. Mark the hard ones.

**Next 30 minutes:** Do all easy MCQs (30 questions). These are your baseline.

**Next 20 minutes:** Do short-answer (pick 10 of 15). Focus on answers from the PDF.

**Next 15 minutes:** Sequence questions. Draw the flows.

**Last 10 minutes:** Review, fix obvious errors.

**If stuck:** Flip back to your notes. Don't guess.

---

## FINAL TRUTH ABOUT THIS LECTURE

**The PDF is a masterclass in layering, encapsulation, and design tradeoffs.**

You'll see these principles in:
- Microservices (API layers)
- Kubernetes (network abstractions)
- Cloud architecture (security groups, VPCs, subnets)
- Database (views, schemas, indexing)
- Real-time systems (control vs data paths)

The specifics of SMTP, POP3, SS7 might not be in your daily work. But **the principle of layering will be**. That's what matters.

Good luck. 🚀

[← Previous](07_quiz.md)
