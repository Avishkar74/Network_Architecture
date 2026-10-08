#include "common/protocol.hpp"

#include <arpa/inet.h>
#include <cerrno>
#include <csignal>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sys/socket.h>
#include <unistd.h>

namespace fs = std::filesystem;

namespace {

bool valid_path(const std::string& request_path, fs::path& relative_path) {
    if (request_path.empty() || request_path[0] != '/' ||
        request_path.find('\\') != std::string::npos) {
        return false;
    }

    relative_path = fs::path(request_path).relative_path();
    for (const fs::path& part : relative_path) {
        if (part == "." || part == "..") {
            return false;
        }
    }
    return !relative_path.empty();
}

bool is_under_root(const fs::path& root, const fs::path& file) {
    const fs::path relative_path = file.lexically_relative(root);
    const std::string relative_text = relative_path.generic_string();
    return !relative_path.empty() && relative_text != ".." &&
           relative_text.rfind("../", 0) != 0;
}

void send_response(int client_fd, uint16_t status, const std::string& message,
                   const std::vector<uint8_t>& body = {}) {
    const std::vector<nap::Header> headers = {
        {nap::HeaderName::content_type, "application/octet-stream", ""},
        {nap::HeaderName::message, message, ""},
    };
    const nap::Frame response = nap::response_frame(status, headers, body);
    (void)nap::send_frame(client_fd, response);
}

void handle_client(int client_fd, const fs::path& root) {
    for (;;) {
        nap::Frame frame;
        const nap::ReadFrame frame_result = nap::read_frame(client_fd, frame);

        if (frame_result == nap::ReadFrame::eof) {
            return;
        }
        if (frame_result != nap::ReadFrame::ok) {
            send_response(client_fd, 400, "malformed frame");
            return;
        }
        if (frame.type != nap::REQUEST) {
            // The payload has already been read, so the stream remains aligned.
            continue;
        }

        std::string request_path;
        fs::path relative_path;
        if (!nap::parse_request(frame, request_path) ||
            !valid_path(request_path, relative_path)) {
            send_response(client_fd, 400, "invalid request");
            continue;
        }

        std::error_code error;
        const fs::path file = fs::canonical(root / relative_path, error);
        if (error || !is_under_root(root, file) || !fs::is_regular_file(file, error)) {
            send_response(client_fd, 404, "not found");
            continue;
        }

        std::ifstream input(file, std::ios::binary);
        if (!input) {
            send_response(client_fd, 500, "cannot read file");
            continue;
        }

        std::vector<uint8_t> body((std::istreambuf_iterator<char>(input)), {});
        if (body.size() > nap::MAX_PAYLOAD - 128) {
            send_response(client_fd, 500, "file too large");
            continue;
        }
        send_response(client_fd, 200, "ok", body);
    }
}

bool parse_port(const char* text, uint16_t& port) {
    char* end = nullptr;
    const long value = std::strtol(text, &end, 10);
    if (end == nullptr || *end != '\0' || value < 1 || value > 65535) {
        return false;
    }
    port = static_cast<uint16_t>(value);
    return true;
}

int create_listening_socket(uint16_t port) {
    const int socket_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (socket_fd < 0) {
        return -1;
    }

    const int enabled = 1;
    setsockopt(socket_fd, SOL_SOCKET, SO_REUSEADDR, &enabled, sizeof(enabled));

    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_ANY);
    address.sin_port = htons(port);
    if (bind(socket_fd, reinterpret_cast<sockaddr*>(&address), sizeof(address)) != 0 ||
        listen(socket_fd, 16) != 0) {
        close(socket_fd);
        return -1;
    }
    return socket_fd;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: bserve <www-root> <port>\n";
        return 2;
    }

    uint16_t port = 0;
    if (!parse_port(argv[2], port)) {
        std::cerr << "invalid port\n";
        return 2;
    }

    std::error_code error;
    const fs::path root = fs::canonical(argv[1], error);
    if (error || !fs::is_directory(root)) {
        std::cerr << "invalid www root\n";
        return 2;
    }

    std::signal(SIGPIPE, SIG_IGN);
    const int listen_fd = create_listening_socket(port);
    if (listen_fd < 0) {
        perror("bind/listen");
        return 1;
    }

    for (;;) {
        const int client_fd = accept(listen_fd, nullptr, nullptr);
        if (client_fd < 0) {
            if (errno == EINTR) {
                continue;
            }
            perror("accept");
            break;
        }

        handle_client(client_fd, root);
        close(client_fd);
    }

    close(listen_fd);
    return 1;
}
