#!/bin/bash
# Validation script for RAG Parser Service

echo "=== RAG Parser Service Validation ==="
echo ""

echo "1. Checking Python file syntax..."
find app cmd tests -name "*.py" -type f | xargs python -m py_compile && echo "✓ All Python files compile successfully" || echo "✗ Syntax errors found"
echo ""

echo "2. Checking required files..."
for file in requirements.txt requirements-dev.txt Dockerfile docker-compose.yml .env.example README.md pytest.ini alembic.ini; do
    if [ -f "$file" ]; then
        echo "✓ $file exists"
    else
        echo "✗ $file missing"
    fi
done
echo ""

echo "3. Checking directory structure..."
for dir in app/parsers app/services app/kafka app/models app/utils cmd/worker tests/unit tests/integration alembic/versions; do
    if [ -d "$dir" ]; then
        echo "✓ $dir exists"
    else
        echo "✗ $dir missing"
    fi
done
echo ""

echo "4. Checking parsers..."
for parser in app/parsers/docx_parser.py app/parsers/pdf_parser.py app/parsers/pptx_parser.py app/parsers/xlsx_parser.py app/parsers/factory.py; do
    if [ -f "$parser" ]; then
        echo "✓ $parser exists"
    else
        echo "✗ $parser missing"
    fi
done
echo ""

echo "5. Checking key services..."
for service in app/services/storage.py app/services/document.py app/services/worker_pool.py; do
    if [ -f "$service" ]; then
        echo "✓ $service exists"
    else
        echo "✗ $service missing"
    fi
done
echo ""

echo "6. Checking Kafka integration..."
for kafka in app/kafka/consumer.py app/kafka/producer.py app/kafka/schemas.py; do
    if [ -f "$kafka" ]; then
        echo "✓ $kafka exists"
    else
        echo "✗ $kafka missing"
    fi
done
echo ""

echo "7. Checking observability..."
if [ -f "app/utils/logging.py" ] && [ -f "app/utils/metrics.py" ] && [ -f "app/api.py" ]; then
    echo "✓ Logging, metrics, and API endpoints implemented"
else
    echo "✗ Missing observability components"
fi
echo ""

echo "8. File counts..."
echo "  - Python files: $(find . -name '*.py' -type f | wc -l)"
echo "  - Test files: $(find tests -name 'test_*.py' -type f | wc -l)"
echo "  - Parser implementations: $(find app/parsers -name '*_parser.py' -type f | wc -l)"
echo ""

echo "=== Validation Complete ==="
