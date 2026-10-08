CXX ?= g++
CXXFLAGS ?= -std=c++17 -Wall -Wextra -Wpedantic -Werror -O2
COMMON = common/protocol.cpp common/io.cpp

.PHONY: all clean test
all: bserve bcurl
bserve: server/main.cpp $(COMMON) common/protocol.hpp common/io.hpp
	$(CXX) $(CXXFLAGS) -I. -o $@ server/main.cpp $(COMMON)
bcurl: client/main.cpp $(COMMON) common/protocol.hpp common/io.hpp
	$(CXX) $(CXXFLAGS) -I. -o $@ client/main.cpp $(COMMON)
test: all
	python3 tests/test_protocol.py
clean:
	rm -f bserve bcurl
