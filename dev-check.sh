#!/bin/bash
# Development script for code quality checks and formatting

set -e

echo "=== Voice Transcription Service - Code Quality Check ==="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    print_warning "Virtual environment not detected. Activating venv..."
    if [ -d "venv" ]; then
        source venv/bin/activate
    else
        print_error "Virtual environment not found. Please run: python -m venv venv && source venv/bin/activate"
        exit 1
    fi
fi

# Install/upgrade development dependencies
print_status "Installing development dependencies..."
pip install -q -r requirements.txt

# Format code with black
print_status "Formatting code with black..."
black --check --diff main.py minimal-client.py tests/ || {
    print_warning "Code formatting issues found. Auto-formatting..."
    black main.py minimal-client.py tests/
}

# Sort imports with isort
print_status "Sorting imports with isort..."
isort --check-only --diff main.py minimal-client.py tests/ || {
    print_warning "Import sorting issues found. Auto-sorting..."
    isort main.py minimal-client.py tests/
}

# Lint with flake8
print_status "Linting with flake8..."
flake8 main.py minimal-client.py tests/ || {
    print_error "Linting issues found. Please fix them manually."
    exit 1
}

# Type checking with mypy
print_status "Type checking with mypy..."
mypy main.py || {
    print_warning "Type checking issues found. Please review mypy output."
}

# Run tests with coverage
print_status "Running tests with coverage..."
pytest --cov=main --cov-report=term-missing --cov-report=html || {
    print_error "Tests failed. Please fix failing tests."
    exit 1
}

# Security check (if bandit is available)
if command -v bandit &> /dev/null; then
    print_status "Running security check with bandit..."
    bandit -r main.py minimal-client.py || {
        print_warning "Security issues found. Please review bandit output."
    }
fi

print_status "Code quality check completed successfully!"
print_status "Coverage report available in htmlcov/index.html"
