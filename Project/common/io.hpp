#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

namespace nap {

enum class IoResult { ok, eof, error };

IoResult read_exact(int socket_fd, void* buffer, size_t byte_count);
bool write_all(int socket_fd, const void* buffer, size_t byte_count);
void hex_dump(const char* label, const std::vector<uint8_t>& bytes);

}  // namespace nap
