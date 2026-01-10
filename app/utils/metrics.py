from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

# Create a registry for metrics
registry = CollectorRegistry()

# Document parsing metrics
documents_parsed_total = Counter(
    "documents_parsed_total",
    "Total number of documents parsed",
    ["format", "status"],
    registry=registry,
)

parse_duration_seconds = Histogram(
    "parse_duration_seconds",
    "Time taken to parse documents",
    ["format"],
    registry=registry,
    buckets=(0.5, 1, 2, 5, 10, 30, 60, 120, 300),
)

parse_errors_total = Counter(
    "parse_errors_total",
    "Total number of parsing errors",
    ["format", "error_type"],
    registry=registry,
)

active_workers = Gauge(
    "active_workers",
    "Number of currently active worker threads",
    registry=registry,
)

kafka_consumer_lag = Gauge(
    "kafka_consumer_lag",
    "Kafka consumer lag",
    ["topic", "partition"],
    registry=registry,
)

# Additional operational metrics
kafka_messages_consumed = Counter(
    "kafka_messages_consumed_total",
    "Total Kafka messages consumed",
    ["topic"],
    registry=registry,
)

kafka_messages_produced = Counter(
    "kafka_messages_produced_total",
    "Total Kafka messages produced",
    ["topic"],
    registry=registry,
)

storage_download_errors = Counter(
    "storage_download_errors_total",
    "Total storage download errors",
    registry=registry,
)

database_operation_errors = Counter(
    "database_operation_errors_total",
    "Total database operation errors",
    ["operation"],
    registry=registry,
)
