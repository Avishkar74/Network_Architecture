#include "common/io.hpp"

#include <cerrno>
#include <cstdio>
#include <sys/socket.h>
#include <unistd.h>

namespace nap {

IoResult read_exact(int socket_fd, void* buffer, size_t byte_count) {
    auto* bytes = static_cast<uint8_t*>(buffer);
    size_t received = 0;

    while (received < byte_count) {
        const ssize_t result = recv(socket_fd, bytes + received,
                                    byte_count - received, 0);
        if (result == 0) {
            return received == 0 ? IoResult::eof : IoResult::error;
        }
        if (result < 0) {
            if (errno == EINTR) {
                continue;
            }
            return IoResult::error;
        }
        received += static_cast<size_t>(result);
    }
    return IoResult::ok;
}

bool write_all(int socket_fd, const void* buffer, size_t byte_count) {
    const auto* bytes = static_cast<const uint8_t*>(buffer);
    size_t sent = 0;

    while (sent < byte_count) {
        const ssize_t result = send(socket_fd, bytes + sent,
                                    byte_count - sent, MSG_NOSIGNAL);
        if (result < 0) {
            if (errno == EINTR) {
                continue;
            }
            return false;
        }
        if (result == 0) {
            return false;
        }
        sent += static_cast<size_t>(result);
    }
    return true;
}

void hex_dump(const char* label, const std::vector<uint8_t>& bytes) {
    std::fprintf(stderr, "%s (%zu bytes)\n", label, bytes.size());

    for (size_t index = 0; index < bytes.size(); ++index) {
        const bool end_of_line = index % 16 == 15 || index + 1 == bytes.size();
        std::fprintf(stderr, "%02X%s", bytes[index], end_of_line ? "\n" : " ");
    }
}

}  // namespace nap
