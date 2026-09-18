# 1. SOCKETS

## What is a Socket?

A socket is an endpoint for network communication. Everything above sockets is a **convention** (software-level abstraction), and everything below is **somebody else's problem** (hardware/OS-level concerns).

A TCP socket represents one side of a bidirectional communication channel.

---

## TCP Server Socket Flow

A TCP server requires exactly **six system calls** to accept a connection:

```
socket() → bind() → listen() → accept() → read() → write() → close()
```

### The Six Syscalls Explained

#### 1. **socket(AF_INET, SOCK_STREAM, 0)**
- Creates a socket file descriptor
- `AF_INET` = IPv4 address family
- `SOCK_STREAM` = TCP (reliable, ordered, connection-oriented)
- Returns: `server_fd` (file descriptor)

#### 2. **bind(server_fd, address, size)**
- Associates the socket with a local IP address and port
- Server address setup:
  ```c
  struct sockaddr_in addr = {0};
  addr.sin_family = AF_INET;           // IPv4
  addr.sin_addr.s_addr = INADDR_ANY;   // Listen on all interfaces
  addr.sin_port = htons(2026);         // Port 2026 (network byte order)
  ```
- Must be done before listen()

#### 3. **listen(server_fd, backlog)**
- Marks the socket as listening for incoming connections
- `backlog` parameter = accept queue depth (NOT connection limit)
- Example: `listen(server_fd, 1)` means queue depth of 1
- This parameter is critical for understanding SYN floods

#### 4. **accept(server_fd, NULL, NULL)**
- Blocks until a client connects
- Returns: `client_fd` (a new socket for that specific client)
- Note: The server_fd remains listening; accept() returns a separate fd for the new client

#### 5. **read(client_fd, buffer, size)**
- Reads data from the connected client
- Returns number of bytes read

#### 6. **write(client_fd, buffer, size)**
- Sends data to the connected client
- Returns number of bytes written

#### 7. **close(client_fd)**
- Closes the connection with that client
- Server loops back to accept() for the next client

---

## TCP Client Socket Flow

The client uses the **same calls as the server, but mirrored**:

```
socket() → [NO bind/listen] → connect() → write() → read() → close()
```

### Key Differences from Server

#### **No bind(), no listen()**
- The kernel automatically assigns an **ephemeral source port** for the client
- This happens implicitly

#### **connect(fd, server_address, size)**
- Initiates the 3-way handshake with the server
- Blocks until the handshake is complete
- If successful, the socket is ready for read/write

---

## htons() — Host to Network Short

**htons** = "Host To Network Short"

- Converts a 16-bit integer from **host byte order** to **network byte order**
- The wire is **big-endian** (most significant byte first)
- Most laptops are **little-endian**
- Required to ensure the port number is sent correctly

Example:
```c
addr.sin_port = htons(2026);  // Convert port 2026 to network byte order
```

---

## SO_LINGER and Connection Termination

### Normal Close: FIN (Polite Goodbye)

When you call `close()` normally:
- Sends a **FIN** (finish) segment
- Socket enters **TIME_WAIT** state for **2 MSL** (Maximum Segment Lifetime)
- Server can still send pending data
- Allows graceful completion of the connection

### Abortive Close: RST (Immediate Teardown)

Set `SO_LINGER` with zero timeout:
```c
struct linger l = { 1, 0 };  // Enable linger with 0 timeout
setsockopt(fd, SOL_SOCKET, SO_LINGER, &l, sizeof(l));
close(fd);
```

**What happens:**
- Sends a **RST** (reset) segment instead of FIN
- Connection is torn down **immediately**
- **No TIME_WAIT** state
- Any unsent data is **discarded**

**Key difference:**
| Aspect | FIN (Normal) | RST (SO_LINGER {1,0}) |
|--------|-------------|----------------------|
| Politeness | Graceful goodbye | Immediate termination |
| TIME_WAIT | Yes, 2 MSL duration | No |
| Unsent data | Can be completed | Discarded |
| Use case | Normal operation | Demo/testing |
| Production use | Yes | No (lossy) |

---

## Common Socket Confusions

### 1. **accept() returns a new fd, not a connection**
- `server_fd` continues listening
- Each call to `accept()` returns a different `client_fd`
- Each client gets its own file descriptor

### 2. **listen(fd, 1) is queue depth, not connection limit**
- The `1` is the **accept queue depth**, not the maximum simultaneous connections
- If the queue is full, new connections are dropped
- This is important for understanding SYN flood attacks

### 3. **bind() is for servers, not clients**
- Servers bind() to a known address so clients can find them
- Clients get an ephemeral port automatically
- The kernel picks the source port for the client

### 4. **socket() vs fd**
- `socket()` is the syscall
- Returns a **file descriptor** (an integer)
- Same descriptor can be used with read(), write(), close()

### 5. **Blocking vs non-blocking**
- By default, all these syscalls block
- accept() waits for a connection
- read() waits for data
- connect() waits for the handshake to complete

---

## Complete Server Code Example

```c
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>

int main() {
    // 1. socket()
    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    
    // 2. bind()
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(2026);
    bind(server_fd, (struct sockaddr*)&addr, sizeof(addr));
    
    // 3. listen()
    listen(server_fd, 1);
    
    // 4-7. Accept and echo
    while (1) {
        int client_fd = accept(server_fd, NULL, NULL);
        char buf[4096];
        int n = read(client_fd, buf, sizeof(buf));
        write(client_fd, buf, n);
        close(client_fd);
    }
}
```

---

## Complete Client Code Example

```c
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>

int main() {
    // 1. socket()
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    
    // 2. address setup (NO bind)
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = inet_addr("127.0.0.1");
    addr.sin_port = htons(8080);
    
    // 3. connect() - initiates 3-way handshake
    connect(fd, (struct sockaddr*)&addr, sizeof(addr));
    
    // 4. write/read
    write(fd, "hello", 5);
    
    // 5. abortive close with SO_LINGER
    struct linger l = { 1, 0 };
    setsockopt(fd, SOL_SOCKET, SO_LINGER, &l, sizeof(l));
    close(fd);
    
    return 0;
}
```

---

## Summary Table: Socket Syscalls

| Syscall | Purpose | Return | Who uses? |
|---------|---------|--------|-----------|
| socket() | Create endpoint | fd | Both |
| bind() | Assign local address | 0/-1 | Server only |
| listen() | Mark as listening | 0/-1 | Server only |
| accept() | Wait for client | client_fd | Server only |
| connect() | Connect to server | 0/-1 | Client only |
| read() | Receive data | bytes read | Both |
| write() | Send data | bytes written | Both |
| close() | Terminate connection | 0/-1 | Both |
| setsockopt() | Set socket options | 0/-1 | Both |

