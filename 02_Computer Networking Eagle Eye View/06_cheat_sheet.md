# CHEAT SHEET & QUICK REFERENCE

[← Previous](05_text_protocols.md) | [Next →](07_quiz.md)


## PORT NUMBERS TO MEMORIZE

| Service | Port | Note |
|---------|------|------|
| SMTP (submit) | 587 | Use this for client-to-server |
| SMTP (relay) | 25 | Server-to-server, plaintext |
| SMTPS | 465 | Implicit TLS |
| POP3 | 110 | Plaintext |
| POP3S | 995 | TLS encrypted |
| IMAP | 143 | Plaintext |
| IMAPS | 993 | TLS encrypted |
| FTP | 21 | Control connection |
| FTP data | 20 (active) / random (passive) | Data connection |
| HTTP | 80 | Plaintext |
| HTTPS | 443 | TLS encrypted |
| DNS | 53 | UDP primarily |
| Telnet | 23 | Login (insecure) |

---

## SOCKET SYSCALLS: THE BIG SEVEN

**Server:** socket → bind → listen → accept → [read/write] → close

**Client:** socket → [NO bind] → connect → [read/write] → close

| Call | Server? | Client? | Returns | Purpose |
|------|---------|---------|---------|---------|
| socket() | ✓ | ✓ | fd | Create endpoint |
| bind() | ✓ | ✗ | 0/-1 | Assign local address |
| listen() | ✓ | ✗ | 0/-1 | Mark listening |
| accept() | ✓ | ✗ | client_fd | Wait for connection |
| connect() | ✗ | ✓ | 0/-1 | Initiate handshake |
| read() | ✓ | ✓ | bytes | Receive data |
| write() | ✓ | ✓ | bytes | Send data |
| close() | ✓ | ✓ | 0/-1 | Terminate |

---

## OSI LAYERS & PROTOCOLS

| Layer | Name | Protocols | Key Unit |
|-------|------|-----------|----------|
| 7 | Application | HTTP, SMTP, DNS, FTP | Message |
| 6 | Presentation | TLS, compression | Data |
| 5 | Session | Auth, tokens | Session |
| 4 | Transport | TCP, UDP, QUIC | Segment |
| 3 | Network | IP, ICMP | Packet |
| 2 | Data Link | Ethernet, MAC, ARP | Frame |
| 1 | Physical | Cables, fiber, radio | Bit |

**Key rule:** One layer's headers = next layer's payload

---

## TCP vs UDP at a Glance

| Feature | TCP | UDP |
|---------|-----|-----|
| Connection | 3-way handshake | No connection |
| Reliability | ✓ Yes | ✗ No |
| Ordering | ✓ Yes | ✗ No |
| Flow control | ✓ Yes | ✗ No |
| Congestion control | ✓ Yes | ✗ No |
| Header size | 20B min | 8B always |
| Latency | Higher | Lower |
| Use | HTTP, FTP, SMTP, SSH | DNS, VoIP, gaming |

---

## TCP HANDSHAKE (3-WAY)

```
Client                                  Server
  │                                       │
  ├─ SYN (seq=1000)                      │
  │                                       │
  │◄─ SYN-ACK (seq=5000, ack=1001)       │
  │                                       │
  ├─ ACK (seq=1001, ack=5001)            │
  │                                       │
  └─ ESTABLISHED                         ESTABLISHED
```

**Why 3 messages?**
- Segment 1 announces client's ISN
- Segment 2 acknowledges it, announces server's ISN
- Segment 3 acknowledges server's ISN

**Why SYN/FIN consume sequence numbers?**
- So bare SYN ≠ retransmission of SYN
- ack=1001 answers seq=1000 even with zero payload

---

## TCP CLOSE (4-WAY)

```
Client (Active)                         Server (Passive)
  │                                       │
  ├─ FIN-ACK (seq=2000, ack=6000)        │
  │                                       │
  │◄─ ACK (ack=2001)                     │
  │                                       │
  │◄─ FIN-ACK (seq=6000, ack=2001)       │
  │                                       │
  ├─ ACK (ack=6001)                      │
  │                                       │
  └─ TIME_WAIT (2 MSL) → CLOSED         CLOSED
```

**4-Way:** Both sides must close independently

**TIME_WAIT:** Why it exists:
- Delayed packet from old connection could confuse new connection
- 2 MSL ensures old packets die before tuple is reused
- Causes "address already in use" on server restart
- Fix: SO_REUSEADDR

---

## SMS: THE 140-BYTE LIMIT

Three independent limits:
```
272 octets (SIF - MTP2 hard ceiling)
  └─ ~200 octets (sm-RP-UI - MAP's field)
      └─ 140 octets (TP-UD - SMS payload)
         └─ Chosen so 1 SMS = 1 signaling packet
```

**GSM-7 encoding:**
- 140 octets × 8 bits = 1120 bits
- ÷ 7 bits/character = **160 characters**

**UCS-2 (emoji):**
- 140 octets ÷ 2 bytes = **70 characters**
- One emoji can halve your message length!

---

## SYN FLOOD & SYN COOKIES

**Attack:** Spoofed SYNs fill server's accept queue, preventing legitimate connections

**Defense (SYN Cookies, 1996):** Don't store state. Encode connection into ISN:
```
Server hashes: (4-tuple) + (timestamp) + (MSS)
             → uses hash as SYN-ACK sequence number
             → no backlog entry created

Client sends ACK with ack = server's seq + 1
Server recomputes hash, validates, reconstructs connection
```

**Cost:** Lose some TCP options (window scale, SACK, timestamps)

---

## SS7: IN-BAND VS OUT-OF-BAND

**Before SS7 (In-Band):**
```
One channel carries:
├─ Voice (what you say)
└─ Control (2600 Hz tone = idle, MF = digits)
```
Problem: Anyone who can make the sound can manipulate the network

**After SS7 (Out-of-Band):**
```
Voice bearer: 64 kbps DS0 (conversation)
Signaling network: Separate packet-switched network
                   (MTP1/2/3 + SCCP + TCAP + MAP/ISUP)
```

**Modern analogy:** Control plane ≠ data plane

---

## SS7 ENCAPSULATION: THE ONION

**"Seven layers of nesting to carry eleven bytes"**

```
L1: MTP2 MSU (273 octets max)
  └─ L2: MTP3 (routing info)
      └─ L3: SCCP (transport)
          └─ L4: TCAP (transactions)
              └─ L5: Invoke (operation ID)
                  └─ L6: MAP (SMS operation)
                      └─ L7: SMS-SUBMIT TPDU
                          └─ L8: TP-UD
                              └─ "Hello World!" (11 octets)
```

Identical to: Ethernet ⊃ IP ⊃ TCP ⊃ HTTP

---

## SS7 vs TCP/IP COMPARISON

| Aspect | SS7 | TCP/IP |
|--------|-----|--------|
| Sequencing | FSN (7 bits) | Seq# (32 bits) |
| Ack method | Piggybacked on every SU | Cumulative with ACK |
| Retransmission | BIB toggle | RTO timers |
| Flow control | Stop/go signal | Sliding window |
| Addressing | Point code + SSN | IP + port |
| Connection | Connectionless (SCCP if needed) | 3-way handshake |
| Congestion | Hop-by-hop (MTP3) | End-to-end |
| Reliability scope | Per hop | End-to-end |
| Max payload | 272 octets | ~1460B typical |

**Key difference:** SS7 = per-hop reliable, TCP = end-to-end reliable

---

## TCP RTT COST: THE EVOLUTION

```
TCP alone:
└─ 1 RTT (handshake)

TCP + TLS 1.2:
└─ 3 RTTs (handshake + ClientHello + ServerHello + key exchange)

TCP + TLS 1.3:
└─ 2 RTTs (handshake + ClientHello)

TCP Fast Open:
└─ 1 RTT (returning client puts data in SYN)

QUIC + HTTP/3:
└─ 1 RTT (even first connection!)
   └─ Transport + crypto + data all in 1 RTT
```

**The entire history is attacking the RTT tax.**

Mumbai to Virginia ≈ 190 ms. **Speed of light doesn't change for money.**

---

## QUIC KEY ADVANTAGE

**HTTP/2 head-of-line blocking:**
```
Stream 1: Data 1 → Data 2 → [LOST] → stalls
Stream 2: Data A → Data B → [stalled by Stream 1]
```

**QUIC independent streams:**
```
Stream 1: Seq 1 → Seq 2 → [LOST] → retransmit
Stream 2: Seq 1 → Seq 2 → [continues normally]
```

**Why userspace matters:** Browser updates instantly, no OS reboot needed.

---

## FRAMING METHODS: THE ETERNAL CHOICE

| Type | Example | Pro | Con |
|------|---------|-----|-----|
| Delimiter | SMTP ".", HTTP CRLF CRLF | Human-readable, stream-friendly | Must escape, scanning required |
| Length | HTTP Content-Length, SMS TPDU | No escaping, unambiguous | Must know size first |
| Both | IMAP literals {n}, POP3 +OK | Safe + readable | Two parsers, request smuggling |

---

## SMTP KEY POINTS

**Envelope ≠ Headers**

```
MAIL FROM:<attacker@example.com>       ← Envelope (routing)
From: Bank <bank@example.com>          ← Header (display)
```

Client shows "From: Bank" but it's a lie.

**Lone dot:** `.` on its own line ends message

**Plaintext:** BASE64 for binary (33% overhead)

**SPF/DKIM/DMARC:** Headers bolted on 40 years later

---

## POP3 vs IMAP: THE CHOICE

| Want | Use | Why |
|------|-----|-----|
| Single device, simple | POP3 | Download mail, delete from server, offline access |
| Multiple devices, sync | IMAP | Same view everywhere, server-side search |
| Both secure | POP3S or IMAPS | Add TLS (port 995 or 993) |

---

## FTP: ACTIVE VS PASSIVE

**Active (old):** Server connects back to client → blocked by NAT

**Passive (modern):** Client connects to server's random port → NAT-friendly

```
PASV reply: (127,0,0,1,117,48)
            port = 117 × 256 + 48 = 30000
```

**Why two numbers?** 1971 constraint: don't parse > 255. This is the speed-of-light constraint in networking.

---

## IMPORTANT NUMBERS TO MEMORIZE

| Item | Value | Context |
|------|-------|---------|
| MSS (TCP) | ~1460 bytes | 1500 MTU - 20 IP - 20 TCP |
| MTU (Ethernet) | 1500 bytes | Max frame size |
| SMS payload | 140 octets | GSM-7, 160 chars |
| SMS with emoji | 70 chars | UCS-2, same 140 octets |
| SIF (SS7) | 272 octets | MTP2 hard limit |
| TCP ISN | 32 bits | Sequence number space |
| SS7 FSN | 7 bits | Wraps at 128 |
| TTL default | 64 | Hops before discard |
| TCP backlog | listen(fd, n) | Accept queue depth |
| TIME_WAIT | 2 MSL | ~30 seconds |
| Wi-Fi contention | ~2 ms | Before frame leaves |
| BBR gain | 2000× | Google's claimed improvement |
| GSM-7 bits | 7 bits/char | Packing trick |

---

## PROTOCOL STACK COMPARISON

### TCP/IP Stack (Modern Internet)

```
L7: HTTP, FTP, DNS, SMTP, SSH
L6: TLS
L5: Session/app-specific
L4: TCP/UDP/QUIC
L3: IP (IPv4/IPv6)
L2: Ethernet, Wi-Fi, PPP
L1: Copper, fiber, radio
```

### SS7 Stack (Telephone Network)

```
L7: MAP, ISUP, CAP, INAP (SMS, calls, features)
L5-6: TCAP (transactions, ASN.1)
L4: SCCP (subsystem routing)
L3: MTP3 (point code routing)
L2: MTP2 (signal unit framing, sequencing)
L1: MTP1 (64 kbps DS0, E1/T1 circuits)
```

**Same jobs, different architecture, different era.**

---

## COMMON EXAM TRAPS

1. **TCP sequence numbers:** SYN and FIN consume a sequence number (even with zero payload)

2. **listen() backlog:** Not max connections, but **accept queue depth**

3. **CLOSE_WAIT:** Application bug (forgot to close()), not network problem

4. **TIME_WAIT:** Why "address already in use" on restart

5. **MAC vs IP:** MAC is L2 (local), IP is L3 (routable)

6. **MAIL FROM vs From:** Envelope vs display, must be different

7. **SMS 140 bytes:** Not arbitrary, comes from three stacked limits

8. **POP3 vs IMAP:** State location (client vs server)

9. **BBR vs Reno:** Bandwidth×RTT vs wait-for-loss

10. **SYN cookies:** Encode state in ISN, no backlog entry

[← Previous](05_text_protocols.md) | [Next →](07_quiz.md)
