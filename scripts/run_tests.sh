#!/bin/bash

# Test runner script for FS Reconciliation Agents
# This script runs all tests and generates reports

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TEST_DIR="tests"
REPORTS_DIR="test_reports"
COVERAGE_DIR="coverage"
PYTEST_OPTS="--verbose --tb=short --strict-markers"
COVERAGE_OPTS="--cov=src --cov-report=html --cov-report=term-missing"

# Create directories
mkdir -p "$REPORTS_DIR"
mkdir -p "$COVERAGE_DIR"

echo -e "${BLUE}🚀 Starting FS Reconciliation Agents Test Suite${NC}"
echo "=================================================="

# Function to run tests with coverage
run_tests_with_coverage() {
    local test_type=$1
    local test_path=$2
    local report_file="$REPORTS_DIR/${test_type}_test_report.xml"
    local coverage_file="$COVERAGE_DIR/${test_type}_coverage.xml"
    
    echo -e "${YELLOW}Running ${test_type} tests...${NC}"
    
    pytest "$test_path" \
        $PYTEST_OPTS \
        $COVERAGE_OPTS \
        --junitxml="$report_file" \
        --cov-report=xml:"$coverage_file" \
        --cov-append \
        --html="$REPORTS_DIR/${test_type}_test_report.html" \
        --self-contained-html
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ ${test_type} tests passed${NC}"
    else
        echo -e "${RED}❌ ${test_type} tests failed${NC}"
        return 1
    fi
}

# Function to run security tests
run_security_tests() {
    echo -e "${YELLOW}Running security tests...${NC}"
    
    # Run security-specific tests
    pytest "$TEST_DIR/unit/test_security.py" \
        $PYTEST_OPTS \
        --junitxml="$REPORTS_DIR/security_test_report.xml" \
        --html="$REPORTS_DIR/security_test_report.html" \
        --self-contained-html
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Security tests passed${NC}"
    else
        echo -e "${RED}❌ Security tests failed${NC}"
        return 1
    fi
}

# Function to run performance tests
run_performance_tests() {
    echo -e "${YELLOW}Running performance tests...${NC}"
    
    # Run performance-specific tests
    pytest "$TEST_DIR/unit/test_performance.py" \
        $PYTEST_OPTS \
        --junitxml="$REPORTS_DIR/performance_test_report.xml" \
        --html="$REPORTS_DIR/performance_test_report.html" \
        --self-contained-html
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Performance tests passed${NC}"
    else
        echo -e "${RED}❌ Performance tests failed${NC}"
        return 1
    fi
}

# Function to generate test summary
generate_test_summary() {
    echo -e "${BLUE}📊 Generating Test Summary${NC}"
    echo "================================"
    
    # Count test results
    local total_tests=0
    local passed_tests=0
    local failed_tests=0
    
    for report in "$REPORTS_DIR"/*_test_report.xml; do
        if [ -f "$report" ]; then
            local tests=$(grep -c '<testcase' "$report" 2>/dev/null || echo "0")
            local failures=$(grep -c '<failure' "$report" 2>/dev/null || echo "0")
            local passed=$((tests - failures))
            
            total_tests=$((total_tests + tests))
            passed_tests=$((passed_tests + passed))
            failed_tests=$((failed_tests + failures))
        fi
    done
    
    # Generate summary report
    cat > "$REPORTS_DIR/test_summary.md" << EOF
# Test Summary Report

**Generated:** $(date)

## Test Results

- **Total Tests:** $total_tests
- **Passed:** $passed_tests
- **Failed:** $failed_tests
- **Success Rate:** $((passed_tests * 100 / total_tests))%

## Test Categories

### Unit Tests
- API Endpoints
- Database Operations
- Business Logic
- Error Handling

### Integration Tests
- Database Integration
- Service Integration
- End-to-End Workflows

### Security Tests
- Authentication
- Authorization
- Input Validation
- Security Headers

### Performance Tests
- Response Time
- Memory Usage
- CPU Usage
- Load Testing

## Coverage Report

Coverage reports are available in the \`coverage/\` directory.

## Detailed Reports

- Unit Tests: [unit_test_report.html](unit_test_report.html)
- Integration Tests: [integration_test_report.html](integration_test_report.html)
- Security Tests: [security_test_report.html](security_test_report.html)
- Performance Tests: [performance_test_report.html](performance_test_report.html)

EOF
    
    echo -e "${GREEN}📄 Test summary generated: $REPORTS_DIR/test_summary.md${NC}"
}

# Function to check test dependencies
check_dependencies() {
    echo -e "${BLUE}🔍 Checking test dependencies...${NC}"
    
    # Check if pytest is installed
    if ! command -v pytest &> /dev/null; then
        echo -e "${RED}❌ pytest is not installed${NC}"
        echo "Install with: pip install pytest pytest-cov pytest-html"
        exit 1
    fi
    
    # Check if required packages are installed
    python -c "import psutil" 2>/dev/null || {
        echo -e "${RED}❌ psutil is not installed${NC}"
        echo "Install with: pip install psutil"
        exit 1
    }
    
    echo -e "${GREEN}✅ All dependencies are available${NC}"
}

# Function to clean up
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up...${NC}"
    
    # Remove temporary files
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Main execution
main() {
    local exit_code=0
    
    # Check dependencies
    check_dependencies
    
    # Clean up before running tests
    cleanup
    
    echo -e "${BLUE}🧪 Running Test Suite${NC}"
    echo "========================"
    
    # Run unit tests
    if run_tests_with_coverage "unit" "$TEST_DIR/unit"; then
        echo -e "${GREEN}✅ Unit tests completed successfully${NC}"
    else
        echo -e "${RED}❌ Unit tests failed${NC}"
        exit_code=1
    fi
    
    # Run integration tests
    if run_tests_with_coverage "integration" "$TEST_DIR/integration"; then
        echo -e "${GREEN}✅ Integration tests completed successfully${NC}"
    else
        echo -e "${RED}❌ Integration tests failed${NC}"
        exit_code=1
    fi
    
    # Run security tests
    if run_security_tests; then
        echo -e "${GREEN}✅ Security tests completed successfully${NC}"
    else
        echo -e "${RED}❌ Security tests failed${NC}"
        exit_code=1
    fi
    
    # Run performance tests
    if run_performance_tests; then
        echo -e "${GREEN}✅ Performance tests completed successfully${NC}"
    else
        echo -e "${RED}❌ Performance tests failed${NC}"
        exit_code=1
    fi
    
    # Generate test summary
    generate_test_summary
    
    # Display results
    echo -e "${BLUE}📋 Test Results Summary${NC}"
    echo "========================"
    
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}🎉 All tests passed!${NC}"
        echo -e "${GREEN}📁 Reports available in: $REPORTS_DIR${NC}"
        echo -e "${GREEN}📊 Coverage reports available in: $COVERAGE_DIR${NC}"
    else
        echo -e "${RED}💥 Some tests failed. Check the reports for details.${NC}"
        echo -e "${YELLOW}📁 Reports available in: $REPORTS_DIR${NC}"
    fi
    
    return $exit_code
}

# Handle command line arguments
case "${1:-}" in
    "unit")
        echo -e "${BLUE}🧪 Running Unit Tests Only${NC}"
        run_tests_with_coverage "unit" "$TEST_DIR/unit"
        ;;
    "integration")
        echo -e "${BLUE}🧪 Running Integration Tests Only${NC}"
        run_tests_with_coverage "integration" "$TEST_DIR/integration"
        ;;
    "security")
        echo -e "${BLUE}🔒 Running Security Tests Only${NC}"
        run_security_tests
        ;;
    "performance")
        echo -e "${BLUE}⚡ Running Performance Tests Only${NC}"
        run_performance_tests
        ;;
    "clean")
        echo -e "${BLUE}🧹 Cleaning up only${NC}"
        cleanup
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [unit|integration|security|performance|clean|help]"
        echo ""
        echo "Options:"
        echo "  unit         Run unit tests only"
        echo "  integration  Run integration tests only"
        echo "  security     Run security tests only"
        echo "  performance  Run performance tests only"
        echo "  clean        Clean up temporary files"
        echo "  help         Show this help message"
        echo ""
        echo "Default: Run all tests"
        exit 0
        ;;
    "")
        main
        ;;
    *)
        echo -e "${RED}❌ Unknown option: $1${NC}"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
