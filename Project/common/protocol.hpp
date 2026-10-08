#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace nap {

constexpr uint8_t VERSION = 1;
constexpr uint8_t REQUEST = 1;
constexpr uint8_t RESPONSE = 2;
constexpr uint32_t MAX_PAYLOAD = 16U * 1024U * 1024U;

struct Frame {
    uint8_t version = VERSION;
    uint8_t type = 0;
    uint16_t flags = 0;
    std::vector<uint8_t> payload;
};

// IDs make commonly used header names compact on the wire. ID 255 carries a
// length-prefixed custom name for later extensions.
enum class HeaderName : uint8_t {
    content_type = 1,
    message = 2,
    custom = 255,
};

struct Header {
    HeaderName name;
    std::string value;
    std::string custom_name;
};

enum class ReadFrame { ok, eof, malformed, io_error };

bool send_frame(int socket_fd, const Frame& frame,
                std::vector<uint8_t>* encoded = nullptr);
ReadFrame read_frame(int socket_fd, Frame& frame);
Frame request_frame(const std::string& path);
bool parse_request(const Frame& frame, std::string& path);
Frame response_frame(uint16_t status, const std::vector<Header>& headers,
                     const std::vector<uint8_t>& body);
bool parse_response(const Frame& frame, uint16_t& status,
                    std::vector<Header>& headers, std::vector<uint8_t>& body);
std::string header_name(const Header& header);

}  // namespace nap
