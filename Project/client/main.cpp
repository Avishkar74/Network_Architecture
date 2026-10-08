#include "common/protocol.hpp"
#include "common/io.hpp"

#include <netdb.h>
#include <iostream>
#include <sys/socket.h>
#include <unistd.h>

namespace {

struct UrlParts {
    std::string host;
    std::string port;
    std::string path;
};

bool parse_url(const std::string& url, UrlParts& parts) {
    const size_t slash = url.find('/');
    const size_t colon = url.rfind(':');
    if (colon == std::string::npos || slash == std::string::npos ||
        colon == 0 || colon >= slash) {
        return false;
    }
    parts.host = url.substr(0, colon);
    parts.port = url.substr(colon + 1, slash - colon - 1);
    parts.path = url.substr(slash);
    return !parts.port.empty();
}

int connect_to_server(const UrlParts& parts) {
    addrinfo hints{};
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;

    addrinfo* addresses = nullptr;
    if (getaddrinfo(parts.host.c_str(), parts.port.c_str(), &hints, &addresses) != 0) {
        return -1;
    }

    int socket_fd = -1;
    for (addrinfo* address = addresses; address != nullptr; address = address->ai_next) {
        socket_fd = socket(address->ai_family, address->ai_socktype, address->ai_protocol);
        if (socket_fd >= 0 && connect(socket_fd, address->ai_addr, address->ai_addrlen) == 0) {
            break;
        }
        if (socket_fd >= 0) {
            close(socket_fd);
        }
        socket_fd = -1;
    }
    freeaddrinfo(addresses);
    return socket_fd;
}

}  // namespace

int main(int argc, char** argv) {
    bool verbose = false;
    const char* url_argument = nullptr;
    if (argc == 3 && std::string(argv[1]) == "-v") {
        verbose = true;
        url_argument = argv[2];
    } else if (argc == 2) {
        url_argument = argv[1];
    } else {
        std::cerr << "usage: bcurl [-v] host:port/path\n";
        return 2;
    }

    UrlParts url;
    if (!parse_url(url_argument, url)) {
        std::cerr << "invalid URL\n";
        return 2;
    }

    const int socket_fd = connect_to_server(url);
    if (socket_fd < 0) {
        std::cerr << "cannot resolve or connect to host\n";
        return 1;
    }

    const nap::Frame request = nap::request_frame(url.path);
    std::vector<uint8_t> request_bytes;
    if (!nap::send_frame(socket_fd, request, verbose ? &request_bytes : nullptr)) {
        std::cerr << "send failed\n";
        close(socket_fd);
        return 1;
    }
    if (verbose) {
        nap::hex_dump("> REQUEST FRAME", request_bytes);
    }

    nap::Frame response;
    for (;;) {
        const nap::ReadFrame result = nap::read_frame(socket_fd, response);
        if (result != nap::ReadFrame::ok) {
            std::cerr << "invalid response\n";
            close(socket_fd);
            return 1;
        }
        if (verbose) {
            std::vector<uint8_t> response_bytes;
            nap::send_frame(-1, response, &response_bytes);
            nap::hex_dump(response.type == nap::RESPONSE ? "< RESPONSE FRAME" :
                          "< SKIPPED FRAME", response_bytes);
        }
        if (response.type == nap::RESPONSE) {
            break;
        }
        // Unknown extensions are consumed completely. Never reconnect.
    }
    close(socket_fd);

    uint16_t status = 0;
    std::vector<nap::Header> headers;
    std::vector<uint8_t> body;
    if (!nap::parse_response(response, status, headers, body)) {
        std::cerr << "malformed response\n";
        return 1;
    }

    if (verbose) {
        std::cerr << "Status: " << status << "\n";
        for (const nap::Header& header : headers) {
            std::cerr << nap::header_name(header) << ": " << header.value << "\n";
        }
    }

    std::cout.write(reinterpret_cast<const char*>(body.data()),
                    static_cast<std::streamsize>(body.size()));
    return status == 200 ? 0 : 1;
}
