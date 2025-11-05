#!/bin/bash

# Crew Wallet Test Suite Runner
# This script runs all tests and generates an HTML report

echo "🧪 Running Crew Wallet Test Suite..."
echo "======================================"
echo ""

# Run pytest with detailed output and HTML report
python3 -m pytest tests/ -v --tb=short --html=test_report.html --self-contained-html

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    echo "📊 HTML report generated: test_report.html"
    echo ""
    echo "Test Summary:"
    echo "- Timezone conversion and crew departure filtering"
    echo "- Balance calculation with all split modes"
    echo "- Settlement algorithm accuracy"
    echo "- Core functionality (trips, crew, deposits, expenses)"
    echo "- Permissions and data scoping"
    echo ""
    echo "✅ Ready for production deployment!"
else
    echo ""
    echo "❌ Some tests failed. Please review the report."
    echo "📊 HTML report: test_report.html"
    echo ""
    echo "Do NOT deploy to production until all tests pass."
    exit 1
fi
