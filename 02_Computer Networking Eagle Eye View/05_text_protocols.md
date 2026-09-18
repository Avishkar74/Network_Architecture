# 5. TEXT PROTOCOLS: SMTP, POP3, IMAP, FTP

## Introduction to Text Protocols

**Last session:** Built binary protocols with explicit framing

**This session:** Text protocols—you can be the client by typing commands into telnet

**Key advantage:** Human-readable, easily extensible

**Key characteristic:** One layer's headers are another layer's body (same as binary protocols)

---

## SMTP (Simple Mail Transfer Protocol)

### Overview

**"The S in SMTP is Simple — it has never stood for Secure"**

A mail transfer is a **conversation**, and both halves are **human-readable ASCII**.

### SMTP Ports

| Port | Name | Details |
|------|------|---------|
| **25** | SMTP relay | Server-to-server, plaintext |
| **587** | Submission | Client-to-server, STARTTLS (use this one) |
| **465** | SMTPS | Implicit TLS from first byte |
| **110** | POP3 | Mail retrieval, plaintext |
| **143** | IMAP | Mail retrieval, plaintext |
| **995** | POP3S | POP3 + TLS |
| **993** | IMAPS | IMAP + TLS |

### Why It Stayed Text

**Key requirement:** Every intermediate relay must be able to read, rewrite, and add headers.

- Binary protocol → can't reliably modify without parsing
- Text protocol with fixed delimiter (blank line) → trivial to extend
- Add a header nobody understands → nothing breaks

**Example:** SPF, DKIM, DMARC are all just headers bolted on 40 years later.

### Why It Stayed Insecure

**MAIL FROM is whatever you type.** No authentication in base protocol.

- You can send as anyone
- SPF, DKIM, DMARC are **later patches** trying to answer a question SMTP never asked
- They're all header-based, not protocol changes

### SMTP Commands

```
EHLO <domain>
└─ Extended HELLO, advertise capabilities

MAIL FROM:<sender@example.com>
└─ Envelope sender (where bounces go)

RCPT TO:<recipient@example.com>
└─ Envelope recipient (where it's delivered)

DATA
└─ Start message body
└─ Headers + blank line + body
└─ End with lone "." on its own line

QUIT
└─ Close connection
```

### MAIL FROM vs From: Header

**Critical distinction:**

```
MAIL FROM:<jeet@scaler.com>    ← Envelope (delivery)
                                 Tells server where to route
                                 
From: Jeet <jeet@scaler.com>   ← Header (display)
                                 What mail client shows you
                                 Doesn't have to match!
                                 
To: Kshitij <kshitij@scaler.com> ← Header (display)
                                   Just text printed on the letter
```

**The envelope decides routing. The headers are just display text.**

You could:
```
MAIL FROM:<attacker@example.com>
From: Bank of America <security@bankofamerica.com>
RCPT TO:<victim@example.com>
```

Mail client shows "From: Bank of America" but it came from attacker@example.com. The envelope was different.

### The Lone Dot

**Message ends with a single "." on its own line.**

```
MAIL FROM:<jeet@scaler.com>
RCPT TO:<kshitij@scaler.com>
DATA
From: Jeet <jeet@scaler.com>
To: Kshitij <kshitij@scaler.com>
Subject: SMTP is surprisingly simple

Hello K,
We just sent this email by manually speaking SMTP.
.
QUIT
```

**Why the dot?**

It's the **delimiter** — tells server "message complete, stop reading."

**Escaping:** If your message body starts a line with a dot, an extra one is added:
- You write: `.` at start of line
- Server stores: `..` (escaped)
- Client reads: `..` then unescapes to `.`

(The PDF doesn't explain unescaping details, but the escaping principle is clear.)

### MIME: Base64 (Text Protocol, Binary Data)

**Problem:** Text protocol can't carry arbitrary bytes. SMTP relays don't understand 0x00, 0xFF, etc.

**Solution:** Encode binary as text.

### Base64 Encoding

```
3 bytes in → 4 characters out

01001101 01100001 01101110  (3 bytes: "Man")
├─ Regroup as 6-bit chunks
├─ 010011 010110 000101 101110
├─ Map to 64-character alphabet (A-Z a-z 0-9 + / =)
└─ T W F u
```

**The 64 characters:**
- A–Z (26)
- a–z (26)
- 0–9 (10)
- `+` and `/` (2)
- `=` for padding (1)

**Total:** 64 characters, chosen because every mail system, gateway, and 7-bit link passes them unchanged.

### Base64 Overhead

```
Original: 3 bytes
Encoded:  4 characters

Overhead: 4/3 = 1.33× = 33% overhead (always)

Line length limit: 76 characters per line (RFC 2045)
```

### MIME: Multipart Messages

How to separate text and images:

```
Content-Type: multipart/mixed; boundary="=_a7f3c91"

--=_a7f3c91
Content-Type: text/plain

This is the text version of the message.

--=_a7f3c91
Content-Type: image/png
Content-Transfer-Encoding: base64

iVBORw0KGgoAAAANSUhEUgAA... (base64 encoded image)

--=_a7f3c91--
```

**Boundary:** Pick a string that **cannot appear in the body**.

Same principle as binary protocol framing: choose a delimiter that doesn't conflict with content.

---

## POP3 (Post Office Protocol 3)

### Overview

**"POP is four verbs, and you can hold all of it in your head"**

Simple protocol for retrieving mail from a server.

### POP3 Commands

```
USER <username>
└─ Authenticate

PASS <password>
└─ Send password (plaintext)

STAT
└─ Return: message count and total size in bytes

LIST
└─ Return: one line per message (number and size)

RETR <n>
└─ Retrieve message n in full

DELE <n>
└─ Mark message n for deletion

QUIT
└─ Close connection (deletions take effect)
```

### Plaintext Password Issue

**USER and PASS go over the wire in the clear.**

**Solution:** POP3S on port **995**
- TLS wraps the entire connection
- Authentication happens over encrypted channel

### Full Example

```
Terminal 1:
$ telnet localhost 3110
USER bob
PASS secret
STAT              ← Returns "2 1024" (2 messages, 1024 bytes total)
LIST              ← Lists all messages
RETR 1            ← Get message 1
DELE 1            ← Mark for deletion
QUIT              ← Deletion takes effect

Terminal 2 (sending):
$ telnet localhost 3025
MAIL FROM:<sender@example.com>
RCPT TO:<bob@localhost>
DATA
From: Sender <sender@example.com>
Subject: Test

Hello Bob!
.
QUIT
```

### Protocol Simplicity

POP3 is **stateful:**
- Each command is independent
- Server maintains state (which messages marked deleted)
- Deletion takes effect only on QUIT

---

## POP3 vs IMAP: The Big Difference

**The trade: POP3 puts state on your machine, IMAP puts it on the server.**

### POP3 Model

```
Mail lives on your device
Server is a spool to be emptied

Second device: Sees nothing (first client already took it)
Read/unread: Local only (nobody knows what you opened)
Folders: One (the inbox)
Search: Download everything, then search locally
Partial fetch: No (RETR gives entire message)
Synchronization: None (each client independent)
```

**Typical workflow:**
1. Download mail with POP3 client
2. Delete from server
3. Read locally
4. If you use another device, it doesn't see the mail (already deleted)

### IMAP Model

```
Mail lives on the server
Client holds a cache

Second device: Same mailbox, same state, same moment
Read/unread: Server-side flag (\Seen, \Answered, \Flagged)
Folders: Arbitrary hierarchy, created/renamed over the wire
Search: SEARCH runs on server (IDLE pushes new mail)
Partial fetch: FETCH BODY[1] — one MIME part, headers only, etc.
Synchronization: Full (multiple devices stay in sync)
```

**Typical workflow:**
1. Connect to IMAP server
2. Server shows all folders and messages
3. Mark messages as read (state saved on server)
4. Connect from another device → same view
5. Search for message → server searches, returns results

### Comparison Table

| Aspect | POP3 | IMAP |
|--------|------|------|
| Mail location | Your device | Server |
| Client state | Local only | Cached locally |
| Synchronization | None | Full |
| Multiple devices | Fragmented view | Unified view |
| Search | Local | Server-side |
| Partial fetch | No | Yes |
| Flags/labels | Local | Server |
| Folders | One | Many |
| Scalability | Better for single device | Better for multi-device |

### Why POP3 Exists

- **Simpler** (only 4 verbs)
- **Less bandwidth** (don't re-download flags)
- **Works offline** (you have the messages locally)
- **Server-side resources** (no state to maintain)

### Why IMAP is Growing

- **Multiple devices** (phone, laptop, web)
- **Server-side search** (faster than searching locally)
- **Unified view** (same state everywhere)
- **Partial fetch** (save bandwidth, only get what you need)

---

## Framing: Length vs Delimiter

Every protocol must frame messages. Three approaches:

### Approach 1: Delimiter-Based

**Agreement:** A byte sequence ends the message.

| Protocol | Delimiter |
|----------|-----------|
| SMTP | Lone "." on its own line |
| HTTP/1.1 headers | CRLF CRLF (blank line) |
| MIME | `--=_boundary--` |
| Redis | CRLF between parts |

**Advantages:**
- Cheap to write
- Human-readable
- Stream without knowing size in advance

**Disadvantages:**
- Must escape delimiter if it appears in payload (dot-stuffing)
- If you get escaping wrong, content becomes protocol

### Approach 2: Length-Based

**Agreement:** Put the size in front, read exactly that many bytes.

| Protocol | Length field |
|----------|--------------|
| SMS TPDU | TP-UDL = octets |
| HTTP | Content-Length: 4096 |
| SS7 MTP2 | LI, SIF ≤ 273 |
| Protobuf | varint length prefix |

**Advantages:**
- Content can never be confused with protocol
- No escaping needed
- No scanning required

**Disadvantages:**
- Must know size before sending
- Chunked transfer encoding needed to avoid this

### Approach 3: Both (Pragmatic)

**Delimit the frame, then length-prefix the payload inside.**

| Protocol | Pattern |
|----------|---------|
| IMAP literals | `{310}` then 310 bytes |
| HTTP/1.1 | CRLF headers + Content-Length + body |
| HTTP/2 | Binary framing layer over stream |
| POP3 | `+OK` line, then dotted body |

**Advantages:**
- Human-readable control
- Safe binary payload
- No escaping needed

**Disadvantages:**
- Two parsers, two failure modes
- **Request smuggling** lives in the gap between them

---

## FTP (File Transfer Protocol)

### Key Design: Separate Control and Data

**FTP refuses to mix commands and data at all.**

- **One connection:** For the conversation (telnet-like, port 21)
- **A second connection:** For every single file transfer (data connection)

### Active Mode (Original Design, 1971)

```
Client                              Server
  │                                  │
  │  (opens port 21 to server)       │
  ├─→ USER, PASS, LIST, RETR        │
  │                                  │
  │  (server connects back to client) │
  │◄────────────────────────────────┤
  │  Port 20 (data)                  │
  │                                  │
  └─ File bytes flow over this       │
```

**Problem:** Every NAT and firewall blocks inbound connections. Server can't connect back to client.

### Passive Mode (Added Later, Now Essential)

```
Client                              Server
  │                                  │
  │  (opens port 21 to server)       │
  ├─→ PASV                           │
  │                                  │
  │◄─ 227 Entering Passive Mode      │
  │   (h,h,h,h,p1,p2)              │
  │                                  │
  │  (client connects to port data)  │
  ├─→ port p                         │
  │                                  │
  └─ File bytes flow over this       │
```

**Both connections are opened by the client.**

Only shape NAT was ever going to allow.

### PASV Response: Decoding the Port

```
227 Entering Passive Mode (127,0,0,1,117,48)

The response contains:
├─ First 4 octets: IP address (127.0.0.1)
└─ Last 2 octets: Port (big-endian pair)

port = 117 × 256 + 48 = 30000
```

### Why Two Numbers for Port?

**1971 design constraint:** Line is text, nobody wanted to parse numbers > 255.

**Solution:** 16-bit port as two 8-bit octets:
- High byte first (network byte order)
- Same `htons()` from the very first slide, **written by hand**

This is **the entire history of networking in one command.**

### FTP: Active vs Passive

| Aspect | Active | Passive |
|--------|--------|---------|
| Data connection | Server → Client | Client → Server |
| Port | Predictable (20) | Random (server assigns) |
| Firewalls | Block (inbound) | Allow |
| NAT | Breaks | Works |
| Modern use | Rare | Standard |

---

## Complete Protocol Flow Examples

### SMTP Example

```
$ telnet localhost 25

220 ESMTP Server ready
EHLO scaler-demo
250 HELLO
MAIL FROM:<jeet@scaler.com>
250 OK
RCPT TO:<kshitij@scaler.com>
250 OK
DATA
354 Start mail input
From: Jeet <jeet@scaler.com>
To: Kshitij <kshitij@scaler.com>
Subject: SMTP is surprisingly simple

Hello K,
We just sent this email by manually speaking SMTP.
.
250 OK
QUIT
221 Goodbye
```

### POP3 Example

```
$ telnet localhost 110

+OK POP3 server ready
USER bob
+OK
PASS secret
+OK Logged in
STAT
+OK 2 1024
LIST
+OK
1 512
2 512
.
RETR 1
+OK 512 octets
(message content here)
.
DELE 1
+OK
QUIT
+OK bye
```

### FTP Example

```
$ telnet localhost 21

220 FTP server ready
USER scaler
331 Password required
PASS demo
230 Logged in
PWD
257 "/"
LIST
150 File list follows
-rw-r--r-- 1 scaler scaler 14 hello.txt
226 Done
PASV
227 Entering Passive Mode (127,0,0,1,117,48)
RETR hello.txt
150 Opening data connection (10 bytes)
(file contents over port 30000)
226 Complete
QUIT
221 Goodbye
```

---

## Key Protocols Summary

| Protocol | Port | Purpose | Stateless? | Binary? |
|----------|------|---------|-----------|---------|
| SMTP | 25/587/465 | Send mail | Yes | No |
| POP3 | 110/995 | Retrieve mail | Mostly | No |
| IMAP | 143/993 | Manage mail | No | No |
| FTP | 21 + random | File transfer | Yes | Mixed |

---

## Framing Methods Used in This Session

| Protocol | Method | Delimiter/Length |
|----------|--------|------------------|
| SMTP | Both | "." + blank line for headers |
| POP3 | Both | "+OK" line + dotted body |
| IMAP | Both | Length prefix + literal bytes |
| FTP | Delimiter | Line-based commands, PASV decoding |
| HTTP/1.1 | Both | Headers + Content-Length |

