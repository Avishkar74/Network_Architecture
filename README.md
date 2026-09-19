# Network Architecture

Personal study notes on computer networking and server architecture, from raw socket system calls up to how production servers like NGINX handle tens of thousands of concurrent connections. Notes from the Scaler computer networks course.

## Modules

### [01 - Network Programming 101](01_Network%20programming%20101)

Builds a TCP server and client from the seven system calls every framework wraps (socket, bind, listen, accept, read, write, close), then works through many clients, HTTP and TLS, protocol design, RPC and gRPC, and debugging. Seven parts plus a summary that ties the whole stack together.

### [02 - Computer Networking: Eagle Eye View](02_Computer%20Networking%20Eagle%20Eye%20View)

An eight-file study guide: sockets, the OSI model, SS7 and telephone signaling, TCP vs UDP vs QUIC, and text protocols (SMTP, POP3, IMAP, FTP), followed by a cheat sheet, a 75-question quiz, and a final-revision doc. See the module's own [README](02_Computer%20Networking%20Eagle%20Eye%20View/README.md) for study plans by time available.

### [03 - One Process, Many Clients: Scaling Servers](03_One%20Process,%20Many%20Clients%20Scaling%20Servers)

The central question: how one box serves ten thousand clients. Covers fork-per-request, thread-per-request, and the event-loop model with select and epoll, then CGI, FastCGI, servlets, scaling limits, and real-world architectures (Apache MPMs, HAProxy, Varnish). Ends with revision notes and MCQs.

### [04 - NGINX Deep Dive](04_NGINX_deep_dive)

Web server history and the C10K problem, NGINX's master/worker process model and event loop, core features, and advanced topics. Includes a cheat sheet, revision short notes, and 30 quiz questions.

## How the notes are organized

Every module follows the same pattern: numbered deep-dive notes first, then quick-review material (cheat sheet or revision doc) and self-test questions (quiz or MCQs). Read the numbered parts in order; use the cheat sheets and quizzes for exam or interview prep.

## Status

Work in progress. New modules are added as the course continues.
