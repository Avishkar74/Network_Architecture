# COMPREHENSIVE QUIZ: 65 QUESTIONS

## PART 1: MULTIPLE CHOICE QUESTIONS (30 MCQs)

### Difficulty: Easy-Medium

**Question 1:** What is the minimum number of system calls required to create a TCP server?
- A) 3
- B) 4
- C) **6** ✓
- D) 7

**Explanation:** socket() → bind() → listen() → accept() → read() → write() → close() is 7 syscalls, but the "big six" excludes close(). The PDF emphasizes six syscalls make a server.

---

**Question 2:** In the TCP 3-way handshake, which flag is sent FIRST?
- A) ACK
- B) **SYN** ✓
- C) FIN
- D) RST

**Explanation:** Client initiates with SYN. Server responds with SYN-ACK. Client acknowledges with ACK.

---

**Question 3:** What does htons() do?
- A) Converts port number from integer to string
- B) **Converts 16-bit integer from host byte order to network byte order** ✓
- C) Hashes a string to a network sequence
- D) Handles the transport negotiation segment

**Explanation:** htons = "Host To Network Short". The wire is big-endian; most laptops are little-endian.

---

**Question 4:** Which OSI layer is responsible for routing?
- A) L2 (Data Link)
- B) **L3 (Network)** ✓
- C) L4 (Transport)
- D) L7 (Application)

**Explanation:** IP (Internet Protocol) at L3 handles routing and logical addressing (IP addresses).

---

**Question 5:** SMS has a 140-byte limit because:
- A) HTTP requires it
- B) **SS7's MTP2 hard limit is 272 octets, and 140 bytes ensures one SMS fits in one signaling packet** ✓
- C) It's the international standard
- D) It's the same as TCP MSS

**Explanation:** 140 octets chosen so the entire MAP operation fits in one Message Signal Unit, enabling stateless delivery.

---

**Question 6:** What's the primary difference between TCP and UDP?
- A) TCP is faster
- B) **TCP is connection-oriented and reliable; UDP is connectionless and best-effort** ✓
- C) UDP is used for email
- D) TCP works only over Ethernet

**Explanation:** TCP guarantees ordered, reliable delivery. UDP just sends datagrams.

---

**Question 7:** In SMTP, the difference between MAIL FROM and From: is:
- A) They are the same thing
- B) **MAIL FROM is the envelope (routing); From: is the header (display)** ✓
- C) MAIL FROM is deprecated
- D) From: is only for POP3

**Explanation:** MAIL FROM decides where the message is routed. From: is just text the mail client displays.

---

**Question 8:** What does "out-of-band signaling" mean in SS7?
- A) Signaling happens on a different network from voice
- B) **Signaling travels separately from voice on a packet-switched network** ✓
- C) Signaling is encrypted
- D) Signaling uses TCP/IP

**Explanation:** Before SS7, voice and control signals shared one channel (in-band). SS7 separated them into two networks.

---

**Question 9:** What is the maximum payload for SS7 at L2?
- A) 140 bytes
- B) 160 bytes
- C) **272 octets** ✓
- D) 1460 bytes

**Explanation:** SIF (Signaling Information Field) hard limit is 273 octets (272 payload + markers).

---

**Question 10:** Which SMTP port is recommended for client-to-server submission?
- A) 25
- B) **587** ✓
- C) 465
- D) 993

**Explanation:** Port 25 is relay (server-to-server). Port 587 is submission (client-to-server with STARTTLS).

---

**Question 11:** What happens when you send a lone "." on its own line in SMTP?
- A) An error
- B) **The message ends; server stops reading** ✓
- C) A special command is invoked
- D) It's treated as part of the email body

**Explanation:** The dot is the message delimiter in SMTP. It tells the server "I'm done sending the message."

---

**Question 12:** In TCP connection termination, why does TIME_WAIT last 2 MSL?
- A) It's an arbitrary choice
- B) **So old packets from the closed connection don't confuse a new connection with same 4-tuple** ✓
- C) To allow both sides to fully close
- D) To prevent SYN floods

**Explanation:** 2 MSL ensures delayed packets from old connection have died before the port is reused.

---

**Question 13:** What does QUIC solve that HTTP/2 couldn't?
- A) Encryption
- B) **Head-of-line blocking (each stream has independent sequencing)** ✓
- C) Multiplexing
- D) TLS integration

**Explanation:** HTTP/2 streams multiplex over one TCP connection, so one lost packet stalls all streams. QUIC gives each stream its own sequence space.

---

**Question 14:** Which of the following is NOT a TCP state during connection termination?
- A) FIN_WAIT_1
- B) CLOSE_WAIT
- C) **CLOSING_WAIT** ✓
- D) TIME_WAIT

**Explanation:** Valid states are FIN_WAIT_1, FIN_WAIT_2, CLOSE_WAIT, CLOSING, LAST_ACK, TIME_WAIT. CLOSING_WAIT is not a TCP state.

---

**Question 15:** In the TCP handshake, why does the server send SYN-ACK instead of two separate packets?
- A) To save bandwidth
- B) **Both can be combined in one segment** ✓
- C) It's required by RFC
- D) To prevent SYN floods

**Explanation:** SYN and ACK are flags in the same segment. The segment carries both the ACK (ack=1001) and the new SYN (seq=5000).

---

**Question 16:** What's the key advantage of base64 encoding in SMTP?
- A) It compresses data
- B) **It converts binary data to text using only printable characters** ✓
- C) It encrypts the message
- D) It verifies the sender

**Explanation:** Base64 encodes 3 bytes as 4 text characters from a 64-character alphabet, allowing binary data in text protocols.

---

**Question 17:** Which layer does Wi-Fi's CSMA/CA operate at?
- A) L3 (Network)
- B) **L2 (Data Link)** ✓
- C) L4 (Transport)
- D) L7 (Application)

**Explanation:** CSMA/CA is part of the 802.11 MAC (Media Access Control) at the data link layer.

---

**Question 18:** Why does Wi-Fi use CSMA/CA instead of CSMA/CD (like Ethernet)?
- A) CSMA/CA is newer
- B) **Radios can't listen while transmitting, so they can't detect collisions** ✓
- C) It's faster
- D) It's required by law

**Explanation:** Radio's own signal drowns out everything else. Can't detect collisions in real-time, so must avoid them.

---

**Question 19:** What's the main difference between POP3 and IMAP?
- A) POP3 is faster
- B) **POP3 stores mail on client, IMAP stores on server** ✓
- C) IMAP is older
- D) POP3 supports folders

**Explanation:** POP3 is for single-device download. IMAP is for multi-device sync with server-side state.

---

**Question 20:** In FTP passive mode, how many ports does the client open?
- A) 1
- B) **2** ✓
- C) 3
- D) Depends on file size

**Explanation:** Port 21 for control, plus a dynamically assigned port for data (returned in PASV response).

---

**Question 21:** SYN cookies prevent which attack?
- A) Replay attacks
- B) **SYN floods** ✓
- C) Brute force
- D) Man-in-the-middle

**Explanation:** SYN cookies eliminate the need to store backlog entries, preventing attackers from filling the queue.

---

**Question 22:** What's the byte overhead of base64 encoding?
- A) 10%
- B) 25%
- C) **33%** ✓
- D) 50%

**Explanation:** 3 bytes in → 4 characters out = 4/3 = 1.33× = 33% overhead.

---

**Question 23:** Which TCP congestion control algorithm measures bandwidth × RTT instead of waiting for packet loss?
- A) Reno
- B) CUBIC
- C) **BBR** ✓
- D) Tahoe

**Explanation:** BBR (2016) measures actual bottleneck bandwidth and RTT, avoiding the sawtooth pattern of loss-based algorithms.

---

**Question 24:** How many characters can GSM-7 fit in 140 octets?
- A) 100
- B) 120
- C) **160** ✓
- D) 180

**Explanation:** 140 × 8 ÷ 7 = 1120 ÷ 7 = 160 characters.

---

**Question 25:** What happens if you use emoji in SMS (UCS-2 instead of GSM-7)?
- A) You can send twice as many characters
- B) **Message length drops to 70 characters per SMS** ✓
- C) It's automatically split across two messages
- D) The emoji are converted to text

**Explanation:** UCS-2 uses 2 bytes per character. 140 ÷ 2 = 70 characters.

---

**Question 26:** What does the L in LSSU mean in SS7?
- A) Line Signal Switching Unit
- B) **Link Status Signal Unit** ✓
- C) Layer Signaling State Unit
- D) The PDF doesn't specify

**Explanation:** LSSU carries stop/go signals for flow control. The PDF doesn't fully spell it out, but link/status/signal/unit is the abbreviation.

---

**Question 27:** In the TCP close sequence, which side sends the first FIN?
- A) Always the server
- B) Always the client
- C) **The side that's done sending (either can initiate)** ✓
- D) Both simultaneously

**Explanation:** Either side can close first (active close). The other side responds (passive close).

---

**Question 28:** What's a half-close in TCP?
- A) When half the packets are lost
- B) **After FIN-ACK is exchanged, one direction is closed but the other can still send** ✓
- C) When connection times out
- D) When the window size is zero

**Explanation:** Both sides are independent. One can close while the other still sends remaining data.

---

**Question 29:** What protocol combination gives the lowest RTT overhead?
- A) TCP + TLS 1.2
- B) TCP + TLS 1.3
- C) **QUIC + HTTP/3 (1 RTT)** ✓
- D) TCP Fast Open (1.5 RTT)

**Explanation:** QUIC combines transport, crypto, and initial data in one 1-RTT exchange.

---

**Question 30:** In the Starlink example, which layers did the packet pass through unchanged?
- A) Only L1
- B) Only L3
- C) **L3 and above (except TTL, checksum, NAT rewrites)** ✓
- D) All layers 1-7

**Explanation:** IP packet from laptop arrives at internet unchanged. L1 and L2 are different at each hop, but don't affect L3 headers.

---

## PART 2: SHORT-ANSWER QUESTIONS (15 Questions)

**Question 31:** Explain why SYN and FIN consume sequence numbers even though they carry no payload.

**Answer:** So a bare SYN is distinguishable from a retransmission of that same SYN. Without consuming a sequence number, you couldn't tell if seq=1000 is new or a retransmit. The ACK acknowledges the ISN, not the data.

---

**Question 32:** What is the purpose of listen(server_fd, 1) in a TCP server? What does the "1" mean?

**Answer:** listen() marks the socket as listening. The "1" is the accept queue depth (backlog), not the connection limit. It means the server can queue 1 incoming connection waiting to be accepted.

---

**Question 33:** Why did the PDF say "seven syscalls make a server" when there are actually more?

**Answer:** The core six are socket/bind/listen/accept/read/write. The seventh mentioned is close(). The "seven syscalls" refers to the essential flow; additional syscalls (setsockopt, etc.) are address bookkeeping.

---

**Question 34:** Describe the difference between in-band and out-of-band signaling.

**Answer:** In-band: voice and control signals on same channel (pre-SS7). Problem: anyone making the sound could manipulate the network. Out-of-band: voice and signaling on separate networks. Benefit: complete separation, security.

---

**Question 35:** Why can you send 160 characters with GSM-7 but only 70 with UCS-2, both in 140 octets?

**Answer:** GSM-7 uses 7 bits per character (140 × 8 ÷ 7 = 160). UCS-2 uses 2 bytes (16 bits) per character (140 ÷ 2 = 70).

---

**Question 36:** What is SYN cookie, and why does it prevent SYN floods?

**Answer:** SYN cookie encodes the connection state (4-tuple, timestamp, MSS) into the server's ISN itself. When the client ACKs, the server recomputes the hash and validates it. No backlog entry is ever stored, so the queue can't be filled.

---

**Question 37:** Explain the difference between QUIC/HTTP/3 and HTTP/2 in terms of head-of-line blocking.

**Answer:** HTTP/2 streams multiplex over one TCP connection, but TCP is an ordered byte stream, so one lost packet stalls all streams. QUIC gives each stream independent sequencing, so loss affects only that stream.

---

**Question 38:** Why is PORT 587 recommended for SMTP client submissions instead of port 25?

**Answer:** Port 25 is for server-to-server relay (plaintext). Port 587 is submission with STARTTLS encryption support. Port 465 is SMTPS (implicit TLS). Port 587 is the modern standard for clients.

---

**Question 39:** What is the relationship between SMS's 140-byte limit and SS7's MTP2 limit?

**Answer:** MTP2 hard limit is 272 octets (SIF). MAP uses ~200 octets. SMS TP-UD is limited to 140 octets so the entire MAP operation (with all headers) fits in one Message Signal Unit, enabling stateless transmission.

---

**Question 40:** Why does TCP use SYN-ACK instead of separate SYN and ACK packets?

**Answer:** Both are flags in the same TCP segment. The segment includes ack=1001 (acknowledging client's SYN) and seq=5000 (server's new ISN), so they're combined into one segment.

---

**Question 41:** What does "address already in use" error mean after closing a TCP connection, and how do you fix it?

**Answer:** The connection enters TIME_WAIT (2 MSL) before fully closing, so the (src IP, src port, dst IP, dst port) tuple is still reserved. Fix: use SO_REUSEADDR socket option.

---

**Question 42:** Explain why BBR congestion control works better on wireless networks than CUBIC.

**Answer:** CUBIC grows until packet loss, then cuts window. On wireless, packets drop for non-congestion reasons (interference, fading), so CUBIC crawls. BBR measures actual bandwidth and RTT, keeping the queue nearly empty, so it thrives on lossy links.

---

**Question 43:** In FTP, how does the client decode the PASV response "227 (127,0,0,1,117,48)"?

**Answer:** First four octets are the IP (127.0.0.1). Last two octets are the port as big-endian pair: 117 × 256 + 48 = 30000.

---

**Question 44:** What are the three independent length limits that determine SMS payload size, and which is the bottleneck?

**Answer:** (1) MTP2 SIF 272 octets, (2) MAP sm-RP-UI ~200 octets, (3) SMS TP-UD 140 octets. The smallest (140) wins, so one SMS is always one signaling packet.

---

**Question 45:** Why can't Wi-Fi detect collisions like Ethernet can?

**Answer:** Radio transmitter drowns out the receiver when transmitting. The radio can't listen to the channel while sending, so it can't detect if a collision happened. Therefore, Wi-Fi must avoid collisions (CSMA/CA) instead of detecting them (CSMA/CD).

---

## PART 3: EXPLAIN THE DIFFERENCE (10 Questions)

**Question 46:** TCP connection-oriented vs UDP connectionless

**Answer:** TCP establishes a connection with a 3-way handshake before any data flows. Both sides agree on sequence numbers. UDP just sends datagrams without any setup. TCP guarantees in-order delivery; UDP does not.

---

**Question 47:** POP3 (pulls) vs IMAP (pushes)

**Answer:** POP3 downloads mail from server to client, then deletes from server. Client sees nothing on other devices. IMAP keeps mail on server, synchronizes state across devices, and supports server-side search. POP3 is stateless; IMAP is stateful.

---

**Question 48:** SS7 per-hop reliability vs TCP end-to-end reliability

**Answer:** SS7 ensures every hop is reliable (adjacent signaling points). TCP only ensures endpoints are reliable; middle hops don't guarantee anything. SS7 was right for the small, controlled telephone network. TCP was right for the large, heterogeneous internet.

---

**Question 49:** FTP active mode vs FTP passive mode

**Answer:** Active: server connects back to client (port 20) for data. Blocked by NAT/firewalls. Passive: client connects to server's assigned port for data. Works with NAT. Passive is the modern standard.

---

**Question 50:** MAIL FROM vs From: in SMTP

**Answer:** MAIL FROM is the envelope sender (used for routing and bounces). From: is a header inside the message body (display only, what mail client shows). They don't have to match.

---

**Question 51:** delimiter-based framing vs length-based framing

**Answer:** Delimiter: agreed-upon byte sequence marks end (SMTP "."). Human-readable, streams without knowing size, but must escape delimiters. Length: size in front (HTTP Content-Length). No escaping, but must know size before starting.

---

**Question 52:** HTTP/1.1 vs HTTP/2 vs HTTP/3

**Answer:** HTTP/1.1: text, one request/response per connection. HTTP/2: binary, multiplexed streams over TCP, but head-of-line blocking. HTTP/3: multiplexed streams over QUIC, independent sequencing per stream, 1 RTT setup.

---

**Question 53:** SYN vs ACK in TCP

**Answer:** SYN initiates connection (carries ISN). ACK acknowledges receipt of a segment (carries ack number). Both can be flags in the same segment (SYN-ACK). Both consume sequence numbers when sent alone.

---

**Question 54:** CLOSE_WAIT vs TIME_WAIT in TCP

**Answer:** CLOSE_WAIT: server received FIN but hasn't sent its own close yet (application bug if stuck). TIME_WAIT: sent ACK to peer's FIN, waiting 2 MSL before fully closing (prevents confused packets on tuple reuse).

---

**Question 55:** Encryption at L6 vs L7

**Answer:** L6 (presentation): TLS encryption of data. L7 (application): unencrypted application data (HTTP, SMTP). TLS sits between L4 and L7, encrypting at L6.

---

## PART 4: SEQUENCE/ORDER QUESTIONS (10 Questions)

**Question 56:** Put these in order: TCP 3-way handshake

**Answer:**
1. Client sends SYN (seq=1000)
2. Server sends SYN-ACK (seq=5000, ack=1001)
3. Client sends ACK (seq=1001, ack=5001)

---

**Question 57:** Put these in order: TCP 4-way close

**Answer:**
1. Active closer sends FIN-ACK
2. Passive closer sends ACK
3. Passive closer sends FIN-ACK
4. Active closer sends ACK (enters TIME_WAIT)

---

**Question 58:** SMS encapsulation: order the layers from outermost to innermost

**Answer:**
1. MTP2 MSU (outermost)
2. MTP3
3. SCCP
4. TCAP
5. Invoke
6. MAP
7. SMS-SUBMIT TPDU
8. TP-UD ("Hello World!" innermost)

---

**Question 59:** SMTP message flow from client to delivery

**Answer:**
1. Client connects to port 587
2. MAIL FROM (envelope sender)
3. RCPT TO (envelope recipient)
4. DATA (headers + body)
5. Lone dot (end message)
6. Server stores

---

**Question 60:** POP3 full session from login to reading mail

**Answer:**
1. USER <username>
2. PASS <password>
3. STAT (check message count)
4. LIST (list all messages)
5. RETR 1 (retrieve message 1)
6. DELE 1 (mark for deletion)
7. QUIT (deletions take effect)

---

**Question 61:** FTP PASV-mode transfer (client perspective)

**Answer:**
1. Open control connection (port 21)
2. Send PASV command
3. Receive passive port from PASV reply
4. Open data connection to that port
5. Send RETR <filename>
6. Receive file bytes over data connection
7. Send QUIT

---

**Question 62:** TCP RTT overhead progression (historical)

**Answer:**
1. TCP alone: 1 RTT
2. TCP + TLS 1.2: 3 RTTs
3. TCP + TLS 1.3: 2 RTTs
4. TCP Fast Open: 1 RTT (repeat connections)
5. QUIC + HTTP/3: 1 RTT (even first)

---

**Question 63:** Socket creation on server side

**Answer:**
1. socket() - create fd
2. bind() - assign address
3. listen() - mark listening
4. accept() - wait for client
5. read() - receive data
6. write() - send data
7. close() - terminate

---

**Question 64:** SS7 call setup with ISUP (A calls B)

**Answer:**
1. Phone A off-hook, dials
2. IAM (Initial Address Message) → B's MSC
3. ACM (Address Complete) ← B's MSC (ringing)
4. Phone B answers
5. ANM (Answer Message) → voice path cut
6. Conversation flows (signaling network idle)
7. Phone A hangs up
8. REL (Release) → RLC (Release Complete)

---

**Question 65:** Message framing in protocol stack (soup to nuts)

**Answer:**
1. Application data (GET / HTTP/1.1)
2. TCP segment (add TCP header)
3. IP packet (add IP header)
4. Ethernet frame (add MAC + FCS)
5. Physical layer (transmit bits)

---

## PART 5: FILL IN THE BLANK (10 Questions)

**Question 66-75:** Fill-in-the-blank

66. The TCP 3-way handshake uses **SYN**, **SYN-ACK**, and **ACK** flags.

67. The port for SMTP client submission is **587** (with STARTTLS).

68. SMS can hold **160** characters using GSM-7 encoding in 140 octets.

69. SMS with emoji (UCS-2) can hold **70** characters in the same 140 octets.

70. The smallest three length limits for SMS are **272** (SIF), **~200** (MAP), and **140** (TP-UD) octets.

71. TCP uses a **sliding window** for flow control, UDP uses **none**.

72. QUIC runs over **UDP**, not TCP.

73. The SMTP message delimiter is a lone **"."** on its own line.

74. FTP PASV mode port is calculated as: **high_byte × 256 + low_byte**.

75. Wi-Fi medium access uses **CSMA/CA** (not CSMA/CD like Ethernet) because radios cannot listen while transmitting.

---

## ANSWER KEY SUMMARY

| Section | Questions | Topics |
|---------|-----------|--------|
| MCQs | 1-30 | All core concepts |
| Short Answer | 31-45 | Why/how design decisions |
| Explain Difference | 46-55 | Comparisons |
| Sequence/Order | 56-65 | Protocol flows |
| Fill-in-blank | 66-75 | Key terms & numbers |

**Total: 75 quiz questions**

**Estimated study time:** 1-2 hours (reading + quizzing)

**Success metric:** 70%+ on MCQs, all short answers answered, correct sequence order

