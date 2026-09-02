CXX ?= g++
CXXFLAGS ?= -O3 -std=c++17 -DNDEBUG

.PHONY: all clean test
all: morph_v15 morph_qoblib_solver

morph_v15: src/morph_v15.cpp
	$(CXX) $(CXXFLAGS) -o $@ $<

morph_qoblib_solver: src/morph_qoblib_solver.cpp
	$(CXX) $(CXXFLAGS) -o $@ $<

test: all
	./scripts/smoke_test.sh

clean:
	rm -f morph_v15 morph_qoblib_solver
