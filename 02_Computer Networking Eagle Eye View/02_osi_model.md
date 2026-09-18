# 2. OSI MODEL

## Introduction

The OSI model is a **1984 committee model** that has outlived almost everything built on top of it. It is not a perfect model, but it is incredibly useful for understanding networks.

**Core principle:** One layer's headers are another layer's payload/body.

---

## The Seven Layers

```
L7 - APPLICATION
     ↓ (encapsulation)
L6 - PRESENTATION
     ↓
L5 - SESSION
     ↓
L4 - TRANSPORT
     ↓
L3 - NETWORK
     ↓
L2 - DATA LINK
     ↓
L1 - PHYSICAL
```

---

## Layer Responsibilities

### Layer 7: APPLICATION

**What it is:** User-facing protocols and services

**Protocols:** HTTP, FTP, DNS, SMTP, IMAP, POP3, Telnet, SSH

**Responsibility:**
- Application logic and user interaction
- Message format and semantics
- Data structure (text, binary, encoded)

**Example:**
- HTTP request: `GET / HTTP/1.1`
- SMTP command: `MAIL FROM:<user@example.com>`

**Header added:** None at this layer; this is the actual data

---

### Layer 6: PRESENTATION

**What it is:** Data transformation and encoding

**Protocols/Functions:** Encryption, compression, encoding

**Responsibility:**
- **Encryption:** Converting plaintext to ciphertext (TLS happens here)
- **Compression:** Reducing data size
- **Encoding:** Character set conversion, byte order conversion
- **Format:** Converting between different representations

**Example:**
- TLS encryption for HTTPS
- JPEG compression for images
- Character encoding conversion (ASCII to UTF-8)

**Header added:** Presentation-specific metadata (encryption algorithm, compression method)

---

### Layer 5: SESSION

**What it is:** Conversation management

**Protocols:** Session management, authentication

**Responsibility:**
- **Session establishment:** Opening a session
- **Session maintenance:** Keeping track of authentication state
- **Session termination:** Closing a session gracefully
- **Authentication:** User identity verification
- **Synchronization:** Maintaining dialogue state

**Example:**
- Login to a web application
- Session tokens
- Maintaining "logged in" state across multiple HTTP requests

**Header added:** Session ID, authentication tokens

---

### Layer 4: TRANSPORT

**What it is:** End-to-end delivery mechanism

**Protocols:** TCP, UDP, QUIC, SCTP

**Responsibility:**
- **Connection management:** Set up, maintain, tear down connections (TCP only)
- **Reliability:** Error detection, retransmission, ordering (TCP only)
- **Flow control:** Preventing sender from overwhelming receiver
- **Congestion control:** Responding to network congestion
- **Port-based multiplexing:** Allowing multiple applications on same host

**Key characteristic:** End-to-end reliability (if provided)

| Aspect | TCP | UDP |
|--------|-----|-----|
| Connection-oriented | Yes | No |
| Reliable | Yes | No |
| Ordered delivery | Yes | No |
| Flow control | Yes | No |
| Congestion control | Yes | No |
| Latency | Higher | Lower |
| Use cases | HTTP, FTP, SMTP, SSH | DNS, VoIP, video, gaming |

**Header added:** Source port (2B), destination port (2B), sequence numbers, acknowledgments, flags

---

### Layer 3: NETWORK

**What it is:** Routing and logical addressing

**Protocols:** IP (IPv4, IPv6), ICMP, Routing protocols

**Responsibility:**
- **Logical addressing:** IP addresses (not physical MAC addresses)
- **Routing:** Determining the path packets take across networks
- **Forwarding:** Moving packets from one hop to the next
- **Fragmentation:** Breaking large packets into smaller ones if needed
- **TTL (Time To Live):** Preventing packets from circulating forever

**Key characteristic:** Hop-by-hop delivery; routers only care about the destination IP, not the application

**Example:**
- Packet sent from 192.168.1.42 to 8.8.8.8
- Router looks at destination IP and forwards to next hop
- Routing protocols determine the path

**Header added:** IP version, total length, TTL, protocol type, checksum, source IP, destination IP

**Layers at work together:**
- L3 is unaware of TCP/UDP
- L4 is unaware of the physical path (L1/L2)
- They work independently

---

### Layer 2: DATA LINK

**What it is:** Physical addressing and framing

**Protocols:** Ethernet, MAC addressing, ARP, Wi-Fi (802.11)

**Responsibility:**
- **Framing:** Packaging data into frames
- **Physical addressing:** MAC addresses (48-bit addresses)
- **Switch management:** How frames move between devices on same LAN
- **Medium access control:** Sharing the physical medium
- **Error detection:** CRC (Cyclic Redundancy Check)

**Key characteristic:** Local network only (same LAN)

**Example:**
- Ethernet frame with source MAC 00:11:22:33:44:55 and dest MAC AA:BB:CC:DD:EE:FF
- ARP (Address Resolution Protocol): "Who has IP 192.168.1.1?" → "It's at MAC 00:11:22:33:44:55"

**Header added:** Destination MAC (6B), source MAC (6B), EtherType (2B), FCS/CRC (4B)

---

### Layer 1: PHYSICAL

**What it is:** Raw signal transmission

**Protocols/Media:** Copper cables, fiber optic, radio waves, satellite links

**Responsibility:**
- **Bit transmission:** Converting bits to electrical signals, radio waves, or light
- **Hardware:** Cables, repeaters, hubs, transceivers
- **Physical connectors:** RJ45, fiber connectors
- **Signaling:** Voltage levels, frequencies, modulation

**Key characteristic:** No concept of packets, frames, or protocols—just raw bits

**Example:**
- Ethernet cable carrying 1s and 0s as voltage levels
- Wi-Fi transmitter sending radio waves
- Fiber optic sending light pulses

---

## Packet Structure: Encapsulation

**One layer's headers are another layer's body.**

When a browser on 192.168.1.42 sends `GET / HTTP/1.1` to example.com:

```
LAYER 2 (ETHERNET II FRAME)
┌─────────────────────────────────────────────────────────┐
│ Dst MAC (6B) │ Src MAC (6B) │ Type (2B) │ PAYLOAD │ FCS │
│ 6 bytes      │ 6 bytes      │ 0x0800    │ → IP   │ 4B  │
└─────────────────────────────────────────────────────────┘
                                ↓ The entire IP packet

LAYER 3 (IPv4 PACKET - 20B header)
┌─────────────────────────────────────────────────────────┐
│ Ver │ Len │ TTL │ Proto │ Checksum │ Src IP │ Dst IP │ PAYLOAD │
│ 4b  │ 4b  │ 1B  │ 6=TCP │ 2B       │ 4B     │ 4B     │ → TCP   │
└─────────────────────────────────────────────────────────┘
                                ↓ The entire TCP segment

LAYER 4 (TCP SEGMENT - 20B header minimum)
┌──────────────────────────────────────────────────────────┐
│ Src Port │ Dst Port │ Seq │ Ack │ Flags │ Window │ PAYLOAD  │
│ 2B       │ 2B       │ 4B  │ 4B  │ flags │ 2B     │ → HTTP   │
└──────────────────────────────────────────────────────────┘
                                ↓ Application data

LAYER 7 (APPLICATION DATA - HTTP)
GET / HTTP/1.1
Host: example.com
```

### Byte Budget Calculation

- **MTU (Maximum Transmission Unit):** 1500 bytes (Ethernet frame limit)
- **Ethernet header + FCS:** 14 + 4 = 18 bytes
- **IP header:** 20 bytes
- **TCP header:** 20 bytes (minimum)
- **MSS (Maximum Segment Size):** 1500 - 20 - 20 = **1460 bytes** of application data

Total on wire: 1518 bytes (1500 + 18)

---

## TCP vs UDP at L4

### TCP: Connection-Oriented, Reliable

**Characteristics:**
- ✓ Connection-oriented (3-way handshake)
- ✓ Reliable, ordered delivery
- ✓ Flow and congestion control
- ✓ Error recovery
- ✗ Higher latency (due to handshake and acknowledgments)

**Use cases:** HTTP, FTP, SMTP, SSH, any app needing reliability

**Cost:** Extra overhead and round trips

### UDP: Connectionless, Fast

**Characteristics:**
- ✓ Connectionless (no handshake)
- ✓ Fast, low overhead
- ✗ No delivery guarantee
- ✗ No ordering
- ✓ Low latency

**Use cases:** DNS, VoIP, video calls, gaming, real-time streaming

**Why UDP is right for these:** 
- A retransmitted audio frame arrives too late to play
- Dropping it is the correct behavior
- Reliability would only add latency

---

## Wi-Fi: CSMA/CA at Layer 2

### Difference: Ethernet uses CSMA/CD, Wi-Fi uses CSMA/CA

**On Ethernet (wired):**
- Devices can **detect collisions** (they hear the collision)
- If collision detected → back off and retry
- **CSMA/CD** = Carrier Sense, Multiple Access, Collision Detection

**On Wi-Fi (radio):**
- Radio **cannot listen while transmitting** (own signal drowns everything out)
- Cannot detect collisions in real-time
- Must **avoid** collisions instead
- **CSMA/CA** = Carrier Sense, Multiple Access, Collision Avoidance

### CSMA/CA Process (Wi-Fi)

```
1. Want to transmit?
   ↓
2. LISTEN to channel (Carrier Sense)
   ↓
3. Is someone transmitting?
   ├─ YES → Wait / defer, listen again
   └─ NO  → Go to step 4
   ↓
4. Random backoff (contention window)
   ↓
5. Transmit frame over radio
   ↓
6. Wait for ACK
   ├─ ACK received? → Success
   └─ NO ACK?      → Back off and retransmit
```

### Time Cost of CSMA/CA

**≈2 milliseconds of contention delay** before a frame even leaves your device!

**Why so much delay?**
- Every frame is individually acknowledged at **L2** (not L4)
- This happens long before TCP at L4 knows anything happened
- Multiple devices may be trying to transmit simultaneously
- Backoff times accumulate

**Important:** This ~2ms is not part of network latency; it's **local contention** before the frame even reaches the network.

---

## Layer Abstraction: Starlink Example

**"Your packet can go to space and back, and nothing above L2 notices"**

### The Setup

```
Your laptop
   ↓ (Ethernet)
Ethernet / Wi-Fi (local network)
   ↓ (phased-array dish)
Starlink terminal (Ku/Ka-band)
   ↓ (RF uplink)
LEO satellite (~550 km, ~20 ms)
   ↓ (laser crosslink)
Another satellite (optional)
   ↓ (ground gateway)
Ground gateway (terrestrial handoff)
   ↓ (normal internet)
The internet (same IP packet)
```

### The Magic of Layering

- **IP packet written by your laptop** arrives unchanged at the internet
- Only exceptions: **TTL** (decremented), **checksum** (recalculated), **NAT rewrites** (if any)
- **L3 and above never learn** that space was involved
- The routing, TCP, HTTP all work identically
- That is the **entire point of having layers**

### Why This Matters

- You can run TCP/IP over **anything** at L1/L2
- Starlink is a physical layer innovation
- TCP doesn't care if the medium is copper, fiber, or space
- The abstraction allows innovation at L1 without breaking everything above

---

## Layer Independence

**Each layer refuses to care about the others:**

- L7 doesn't care if it's TCP or UDP (though protocols differ)
- L4 doesn't care about routing (L3 handles that)
- L3 doesn't care about MAC addresses (L2 handles that)
- L2 doesn't care about cable types (L1 handles that)
- L1 doesn't care about protocols (just signals)

This **separation of concerns** is why the model has lasted 40 years.

---

## Common Confusions

### 1. **MAC addresses vs IP addresses**
- **MAC:** L2, local network only (48 bits)
- **IP:** L3, routable across the internet (32 bits for IPv4)
- MAC addresses change on each network hop
- IP addresses stay the same across the entire path

### 2. **Routers use IP, switches use MAC**
- **Router:** L3 device, reads IP headers, makes routing decisions
- **Switch:** L2 device, reads MAC addresses, forwards to ports

### 3. **TCP/UDP is L4, not L3**
- IP is L3 (network layer)
- TCP and UDP are L4 (transport layer)
- IP doesn't know about ports

### 4. **FTP uses TCP, SMTP uses TCP, but they're different apps**
- Both use TCP for transport
- But they're L7 (application) protocols
- TCP is the same for both; application layer differs

### 5. **Encryption at L6, not L7**
- TLS is technically L6 (presentation) or sometimes described as "between L4 and L7"
- Application data is encrypted before L4 sees it (wrong mental model)
- Actually: Application data goes to L6, gets encrypted, then to L4

---

## Summary Table: Layers at a Glance

| Layer | Name | Examples | Key Unit | Responsibility |
|-------|------|----------|----------|-----------------|
| 7 | Application | HTTP, SMTP, DNS | Message | User app logic |
| 6 | Presentation | TLS, compression | Data | Encoding, encryption |
| 5 | Session | Auth, tokens | Session | Conversation state |
| 4 | Transport | TCP, UDP, QUIC | Segment/Datagram | End-to-end delivery |
| 3 | Network | IP, ICMP | Packet | Routing, logical addressing |
| 2 | Data Link | Ethernet, Wi-Fi, MAC | Frame | Physical addressing, framing |
| 1 | Physical | Cables, fiber, radio | Bit | Signal transmission |

