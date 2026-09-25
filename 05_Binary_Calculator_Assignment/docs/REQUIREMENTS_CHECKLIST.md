# Requirement verification checklist

| Required item | Implementation | Evidence |
|---|---|---|
| Fixed, versioned binary frame | `app/protocol.py` 20-byte BLP/1 header | protocol unit/integration tests; `PROTOCOL_SPEC.md` |
| Read/write partial TCP data | `read_exact`, `write_all` | fragmented-frame test |
| Persistent single connection | server loop over accepted socket | six requests / one socket test |
| File server and 404 | `serve_request` | route test |
| Calculator examples and division by zero | `calculator` | route test |
| 400 / 405 behaviour | server validation | invalid-version, traversal, method tests |
| Unknown type skip | frame type branch | unknown frame amid six requests test |
| Path traversal protection | resolved path must be below root | traversal test |
| Client, verbose hex, non-zero errors | `app/client.py` | manual commands in README |
| Formal protocol specification | `docs/PROTOCOL_SPEC.md` | includes offsets and actual hex |
| Personal explanation | `docs/LEARNING_GUIDE.md` | diagrams and implementation walk-through |

## Optional stretch features

Not implemented: explicit `Connection: close`, idle timeout, HTTP-style chunked
encoding, and pipelined response scheduling. The core server accepts coalesced
frames and responds in arrival order, but BLP/1 does not claim multiplexing.
