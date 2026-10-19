CXX ?= g++
CXXFLAGS ?= -O3 -std=c++17 -DNDEBUG

.PHONY: all clean test
all: morph_v15 morph_qoblib_solver

morph_v15: src/morph_v15.cpp
	$(CXX) $(CXXFLAGS) -o $@ $<

morph_qoblib_solver: src/morph_qoblib_solver.cpp
	$(CXX) $(CXXFLAGS) -o $@ $<

test: all
	$(CXX) $(CXXFLAGS) -o test_improve12_v15 tests/test_improve12_v15.cpp
	$(CXX) $(CXXFLAGS) -o test_improve12_qoblib tests/test_improve12_qoblib.cpp
	./test_improve12_v15
	./test_improve12_qoblib
	bash ./scripts/smoke_test.sh
	rm -f test_improve12_v15 test_improve12_qoblib

clean:
	rm -f morph_v15 morph_qoblib_solver
