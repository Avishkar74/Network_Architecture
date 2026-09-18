# COMPUTER NETWORKS — SESSION 2: COMPLETE STUDY GUIDE

## 📚 NOTES STRUCTURE

This study guide contains **8 comprehensive markdown files** covering all content from the Scaler Networks Lecture 2 PDF.

### Files Overview

| File | Topics | Best For |
|------|--------|----------|
| **01_sockets.md** | Socket syscalls, TCP server/client flow, SO_LINGER | Understanding network APIs |
| **02_osi_model.md** | All 7 OSI layers, TCP vs UDP, Starlink example | Layer architecture |
| **03_ss7.md** | SS7 stack, SMS, telephone signaling, ISUP/SIP | Legacy/telecom networks |
| **04_tcp_udp_quic.md** | TCP handshake, UDP, QUIC, RTT costs, congestion control | Transport layer deep dive |
| **05_text_protocols.md** | SMTP, POP3, IMAP, FTP, base64, framing | Application protocols |
| **06_cheat_sheet.md** | Quick reference, port numbers, important numbers | Last-minute review |
| **07_quiz.md** | 75 exam-style questions (MCQs, short-answer, etc.) | Self-assessment |
| **08_final_revision.md** | Top 10 concepts, common traps, essay answers | Final review before exam |

---

## 🎯 HOW TO USE THESE NOTES

### If You Have 1 Hour
1. Read **08_final_revision.md** ("Top 10 Concepts")
2. Review **06_cheat_sheet.md** (port numbers, socket syscalls)
3. Quick skim of difficult sections from **04_tcp_udp_quic.md** and **03_ss7.md**

### If You Have 3 Hours
1. **01_sockets.md** (30 min) — understand socket APIs
2. **02_osi_model.md** (30 min) — internalize the 7-layer model
3. **04_tcp_udp_quic.md** (30 min) — TCP handshake, UDP, QUIC
4. **05_text_protocols.md** (20 min) — protocols you'll use
5. **06_cheat_sheet.md** (10 min) — finalize memory

### If You Have 6+ Hours (Thorough Prep)
1. Read all 5 core files in order: **01** → **02** → **03** → **04** → **05**
2. Take the quiz **07_quiz.md** (1-2 hours)
3. Review wrong answers
4. Do final revision **08_final_revision.md**

### Night Before Exam
1. **08_final_revision.md** — top 10 concepts
2. **06_cheat_sheet.md** — memorize port numbers and syscalls
3. Do a few **07_quiz.md** MCQs to rebuild confidence

---

## 📋 TOPIC QUICK-REFERENCE

### Sockets & Server Architecture
- **File:** 01_sockets.md
- **Key concepts:** socket(), bind(), listen(), accept(), htons(), SO_LINGER
- **Time to study:** 30 minutes
- **Exam likelihood:** High (foundational)

### OSI Model & Layering
- **File:** 02_osi_model.md
- **Key concepts:** 7 layers, encapsulation, TCP vs UDP, Wi-Fi CSMA/CA
- **Time to study:** 45 minutes
- **Exam likelihood:** Very high (fundamental)

### SS7 & Telephone Networks
- **File:** 03_ss7.md
- **Key concepts:** In-band vs out-of-band, SMS 140-byte limit, ISUP call setup
- **Time to study:** 45 minutes
- **Exam likelihood:** Medium-high (unique knowledge)

### Transport Layer & Congestion
- **File:** 04_tcp_udp_quic.md
- **Key concepts:** TCP handshake, SYN cookies, QUIC, BBR, RTT costs
- **Time to study:** 60 minutes
- **Exam likelihood:** Very high (core topic)

### Application Protocols
- **File:** 05_text_protocols.md
- **Key concepts:** SMTP, POP3, IMAP, FTP, base64, framing
- **Time to study:** 40 minutes
- **Exam likelihood:** Medium (likely 1-2 questions)

---

## 🎓 LEARNING OBJECTIVES

By the end of these notes, you should be able to:

### Sockets
- [ ] Draw socket syscall sequence for both server and client
- [ ] Explain why bind()/listen() only on server
- [ ] Explain what SO_LINGER does and when to use it
- [ ] Calculate port numbers from network byte order

### OSI Model
- [ ] List all 7 layers and their responsibilities
- [ ] Explain how one layer's headers = next layer's payload
- [ ] Compare TCP and UDP at L4
- [ ] Explain Wi-Fi CSMA/CA vs Ethernet CSMA/CD
- [ ] Describe the Starlink example and why layering enables it

### SS7
- [ ] Contrast in-band vs out-of-band signaling
- [ ] Explain the three nested limits that make SMS 140 bytes
- [ ] Calculate GSM-7 vs UCS-2 character counts
- [ ] Draw a phone call setup (IAM, ACM, ANM, REL, RLC)
- [ ] Compare SS7 per-hop vs TCP end-to-end reliability

### TCP/UDP/QUIC
- [ ] Draw TCP 3-way handshake with sequence numbers
- [ ] Explain why SYN and FIN consume sequence numbers
- [ ] Describe TCP 4-way close and TIME_WAIT
- [ ] Explain SYN cookies and how they stop floods
- [ ] Compare HTTP/2 vs HTTP/3 head-of-line blocking
- [ ] Explain BBR congestion control

### Text Protocols
- [ ] Manually type SMTP commands to send mail
- [ ] Understand MAIL FROM vs From: difference
- [ ] Calculate base64 overhead (33%)
- [ ] Compare POP3 vs IMAP (client vs server state)
- [ ] Decode FTP PASV response to port number
- [ ] Distinguish delimiter vs length framing

---

## 🎯 EXAM PREPARATION STRATEGY

### Week Before
- [ ] Read **01_sockets.md** and **02_osi_model.md** carefully
- [ ] Make flashcards for port numbers and socket syscalls

### 3 Days Before
- [ ] Read **03_ss7.md** and **04_tcp_udp_quic.md**
- [ ] Do practice questions from **07_quiz.md** (30-MCQ section)

### 2 Days Before
- [ ] Read **05_text_protocols.md**
- [ ] Complete full **07_quiz.md** (all 75 questions)
- [ ] Review wrong answers against the main files

### 1 Day Before
- [ ] Final read of **08_final_revision.md**
- [ ] Memorize **06_cheat_sheet.md** (port numbers, numbers to remember)
- [ ] Do 5-10 random MCQs from **07_quiz.md**

### Exam Day
- [ ] Read **08_final_revision.md** ("If you have 5 minutes")
- [ ] Keep **06_cheat_sheet.md** visible during exam
- [ ] Trust your preparation

---

## 📊 CONTENT DISTRIBUTION (by topic)

| Topic | Pages | MCQs | Difficulty |
|-------|-------|------|------------|
| Sockets | 8 | 5 | Medium |
| OSI Model | 12 | 8 | Medium |
| SS7 | 14 | 7 | Hard |
| TCP/UDP/QUIC | 12 | 7 | Hard |
| Text Protocols | 10 | 3 | Easy-Medium |
| TOTAL | 56 | 30 | - |

---

## 🔑 KEY DEFINITIONS

### Encapsulation
One layer's headers become the next layer's payload. Ethernet frame contains IP packet, which contains TCP segment, which contains HTTP message.

### Layering
Each layer refuses to care about the others. L3 doesn't know about MAC addresses. L2 doesn't know about IP.

### Out-of-Band Signaling
Control signals (signaling) travel separately from data (voice/media).

### Per-Hop Reliability
Each hop guarantees delivery to the next hop (SS7 model).

### End-to-End Reliability
Only endpoints guarantee delivery; middle hops don't care (TCP model).

### Head-of-Line Blocking
One lost packet in a stream stalls other streams (HTTP/2 problem).

---

## ⚠️ COMMON MISCONCEPTIONS

1. **listen() backlog = max connections** → WRONG. It's accept queue depth.
2. **CLOSE_WAIT is a network problem** → WRONG. It's an app bug.
3. **MAC and IP are similar** → WRONG. Different scopes (L2 vs L3).
4. **SYN doesn't need a sequence number** → WRONG. Needs it to avoid retransmit confusion.
5. **SMS is 140 bytes for no reason** → WRONG. Three nested limits enforce it.
6. **MAIL FROM = From:** → WRONG. Envelope ≠ header.
7. **Wi-Fi uses CSMA/CD like Ethernet** → WRONG. Uses CSMA/CA (can't listen while transmitting).
8. **All congestion algorithms wait for loss** → WRONG. BBR measures bandwidth×RTT.
9. **FTP active mode is modern** → WRONG. Passive mode is (blocked by NAT).
10. **Starlink packet changes at each hop** → WRONG. IP packet arrives unchanged (except TTL, checksum).

---

## 📝 FORMULAS TO MEMORIZE

```
MSS = MTU - IP header - TCP header
    = 1500 - 20 - 20
    = 1460 bytes

GSM-7 characters = (octets × 8) ÷ 7
                 = (140 × 8) ÷ 7
                 = 160 characters

UCS-2 characters = octets ÷ 2
                 = 140 ÷ 2
                 = 70 characters

Base64 overhead = 4/3 = 33%

FTP PASV port = high_byte × 256 + low_byte
              = 117 × 256 + 48
              = 30000

TCP RTT cost (modern) = 1 RTT (QUIC/HTTP3)
TCP RTT cost (old) = 3 RTTs (TLS 1.2)
```

---

## 🔗 CONNECTIONS BETWEEN TOPICS

```
Sockets (01)
  ↓
OSI Model (02) ← Understanding layers
  ↓
TCP/UDP/QUIC (04) ← Transport implementation
  ↓
Text Protocols (05) ← Applications using transport

SS7 (03) ← Parallel stack (similar layers, different era)

Encapsulation is the unifying concept across ALL topics.
```

---

## ✅ FINAL CHECKLIST BEFORE EXAM

- [ ] Can draw TCP 3-way handshake from memory
- [ ] Can name all 7 OSI layers in order
- [ ] Understand why SMS is exactly 140 bytes
- [ ] Know the difference between MAIL FROM and From:
- [ ] Can explain how one layer's header = next layer's body
- [ ] Understand SYN cookies prevent SYN floods
- [ ] Know TCP vs UDP tradeoffs
- [ ] Can calculate GSM-7 (160 chars) vs UCS-2 (70 chars)
- [ ] Understand why TIME_WAIT exists
- [ ] Know the difference between CLOSE_WAIT and TIME_WAIT
- [ ] Remember ports: 25/587/465 (SMTP), 110/143 (POP/IMAP), 21 (FTP)
- [ ] Understand FTP active vs passive
- [ ] Know that socket server = socket→bind→listen→accept→read/write→close
- [ ] Understand QUIC fixes HTTP/2 head-of-line blocking
- [ ] Remember that BBR measures bandwidth×RTT, not waiting for loss

---

## 📖 RECOMMENDED READING ORDER

**First Pass (Casual Reading):**
1. 08_final_revision.md (Top 10 concepts)
2. 06_cheat_sheet.md (Port numbers)
3. 01_sockets.md (Socket basics)

**Second Pass (Deep Learning):**
1. 02_osi_model.md (Layers)
2. 04_tcp_udp_quic.md (Transport)
3. 03_ss7.md (Telecom network)
4. 05_text_protocols.md (Applications)

**Third Pass (Assessment):**
1. 07_quiz.md (Self-test)
2. Review wrong answers against main files

**Fourth Pass (Final Polish):**
1. 08_final_revision.md (Common traps)
2. 06_cheat_sheet.md (Numbers memorization)

---

## 🎬 GET STARTED

Pick your path based on time available:

| Time | Path |
|------|------|
| 1 hour | Read 08 + 06 |
| 3 hours | Read 01→02→04→05→06 |
| 6+ hours | Read 01→02→03→04→05, take 07, review 08 |

**Good luck! You've got this.** 🚀

