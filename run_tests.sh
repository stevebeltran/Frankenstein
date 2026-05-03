#!/bin/bash
# Test runner for DFR application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}================================${NC}"
echo -e "${YELLOW}DFR Application Test Suite${NC}"
echo -e "${YELLOW}================================${NC}"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}pytest is not installed${NC}"
    echo "Install with: pip install pytest"
    exit 1
fi

# Get test selection from arguments
TEST_TARGET="${1:-.}"
VERBOSE="${2:-}"

# Run tests
echo -e "${YELLOW}Running tests in: ${TEST_TARGET}${NC}"
echo ""

if [ -n "$VERBOSE" ]; then
    pytest "$TEST_TARGET" -v --tb=short --color=yes
else
    pytest "$TEST_TARGET" --tb=short --color=yes
fi

TEST_RESULT=$?

echo ""
echo -e "${YELLOW}================================${NC}"
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
fi
echo -e "${YELLOW}================================${NC}"

exit $TEST_RESULT
