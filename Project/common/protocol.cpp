#include "common/protocol.hpp"
#include "common/io.hpp"
#include <arpa/inet.h>
#include <cstring>

namespace nap {
namespace {

void append_u16(std::vector<uint8_t>& bytes, uint16_t value) {
    value = htons(value);
    const auto* encoded = reinterpret_cast<const uint8_t*>(&value);
    bytes.insert(bytes.end(), encoded, encoded + sizeof(value));
}

void append_u32(std::vector<uint8_t>& bytes, uint32_t value) {
    value = htonl(value);
    const auto* encoded = reinterpret_cast<const uint8_t*>(&value);
    bytes.insert(bytes.end(), encoded, encoded + sizeof(value));
}

uint16_t read_u16(const uint8_t* bytes) {
    uint16_t value;
    std::memcpy(&value, bytes, sizeof(value));
    return ntohs(value);
}

uint32_t read_u32(const uint8_t* bytes) {
    uint32_t value;
    std::memcpy(&value, bytes, sizeof(value));
    return ntohl(value);
}

bool append_header(std::vector<uint8_t>& payload, const Header& header) {
    if (header.value.size() > UINT16_MAX ||
        (header.name == HeaderName::custom && header.custom_name.size() > UINT8_MAX)) {
        return false;
    }

    payload.push_back(static_cast<uint8_t>(header.name));
    if (header.name == HeaderName::custom) {
        payload.push_back(static_cast<uint8_t>(header.custom_name.size()));
        payload.insert(payload.end(), header.custom_name.begin(), header.custom_name.end());
    }
    append_u16(payload, static_cast<uint16_t>(header.value.size()));
    payload.insert(payload.end(), header.value.begin(), header.value.end());
    return true;
}

}  // namespace

bool send_frame(int socket_fd, const Frame& frame, std::vector<uint8_t>* encoded) {
    if (frame.payload.size() > MAX_PAYLOAD) {
        return false;
    }

    std::vector<uint8_t> bytes;
    bytes.reserve(8 + frame.payload.size());
    bytes.push_back(frame.version);
    bytes.push_back(frame.type);
    append_u16(bytes, frame.flags);
    append_u32(bytes, static_cast<uint32_t>(frame.payload.size()));
    bytes.insert(bytes.end(), frame.payload.begin(), frame.payload.end());

    if (encoded != nullptr) {
        *encoded = bytes;
    }
    return socket_fd < 0 || write_all(socket_fd, bytes.data(), bytes.size());
}

ReadFrame read_frame(int socket_fd, Frame& frame) {
    uint8_t header[8];
    const IoResult header_result = read_exact(socket_fd, header, sizeof(header));
    if (header_result == IoResult::eof) {
        return ReadFrame::eof;
    }
    if (header_result != IoResult::ok) {
        return ReadFrame::io_error;
    }

    const uint32_t payload_length = read_u32(header + 4);
    if (payload_length > MAX_PAYLOAD) {
        return ReadFrame::malformed;
    }

    frame.version = header[0];
    frame.type = header[1];
    frame.flags = read_u16(header + 2);
    frame.payload.resize(payload_length);

    if (payload_length != 0 &&
        read_exact(socket_fd, frame.payload.data(), payload_length) != IoResult::ok) {
        return ReadFrame::io_error;
    }
    return frame.version == VERSION ? ReadFrame::ok : ReadFrame::malformed;
}

Frame request_frame(const std::string& path) {
    Frame frame;
    frame.type = REQUEST;
    frame.payload.assign(path.begin(), path.end());
    return frame;
}

bool parse_request(const Frame& frame, std::string& path) {
    if (frame.type != REQUEST || frame.flags != 0 || frame.payload.empty() ||
        frame.payload.size() > 4096) {
        return false;
    }

    path.assign(frame.payload.begin(), frame.payload.end());
    return path.find('\0') == std::string::npos;
}

Frame response_frame(uint16_t status, const std::vector<Header>& headers,
                     const std::vector<uint8_t>& body) {
    Frame frame;
    frame.type = RESPONSE;
    append_u16(frame.payload, status);
    append_u16(frame.payload, static_cast<uint16_t>(headers.size()));
    for (const Header& header : headers) {
        if (!append_header(frame.payload, header)) {
            frame.payload.clear();
            return frame;
        }
    }
    frame.payload.insert(frame.payload.end(), body.begin(), body.end());
    return frame;
}

bool parse_response(const Frame& frame, uint16_t& status,
                    std::vector<Header>& headers, std::vector<uint8_t>& body) {
    if (frame.type != RESPONSE || frame.flags != 0 || frame.payload.size() < 4) {
        return false;
    }

    status = read_u16(frame.payload.data());
    const uint16_t header_count = read_u16(frame.payload.data() + 2);
    size_t offset = 4;
    headers.clear();

    for (uint16_t index = 0; index < header_count; ++index) {
        if (offset >= frame.payload.size()) {
            return false;
        }

        Header header{static_cast<HeaderName>(frame.payload[offset++]), "", ""};
        if (header.name == HeaderName::custom) {
            if (offset >= frame.payload.size()) {
                return false;
            }
            const uint8_t name_length = frame.payload[offset++];
            if (name_length > frame.payload.size() - offset) {
                return false;
            }
            header.custom_name.assign(
                reinterpret_cast<const char*>(frame.payload.data() + offset), name_length);
            offset += name_length;
        }

        if (frame.payload.size() - offset < 2) {
            return false;
        }
        const uint16_t value_length = read_u16(frame.payload.data() + offset);
        offset += 2;
        if (value_length > frame.payload.size() - offset) {
            return false;
        }
        header.value.assign(
            reinterpret_cast<const char*>(frame.payload.data() + offset), value_length);
        offset += value_length;
        headers.push_back(std::move(header));
    }

    body.assign(frame.payload.begin() + static_cast<std::ptrdiff_t>(offset),
                frame.payload.end());
    return true;
}

std::string header_name(const Header& header) {
    switch (header.name) {
        case HeaderName::content_type:
            return "Content-Type";
        case HeaderName::message:
            return "Message";
        case HeaderName::custom:
            return header.custom_name;
        default:
            return "Unknown-Header-" + std::to_string(static_cast<uint8_t>(header.name));
    }
}

}  // namespace nap
