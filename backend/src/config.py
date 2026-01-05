import os

# Test Configuration
TOTAL_DURATION = 3600   # 1 hour (60 minutes total)
PHASE_LENGTH = 720      # 12 minutes per phase (3600 / 5 phases)
CONCURRENCY_STEPS = [1000, 3000, 5000, 10000]  # ramp-up and down pattern

# AWS Configuration
OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET", "performance-results-bucket")
OUTPUT_PREFIX = "ramp-test-results/"

# Email Configuration
SENDER_EMAIL = os.environ.get(
    "SENDER_EMAIL", "performance-tests@yourcompany.com")
RECIPIENT_EMAILS = os.environ.get(
    "RECIPIENT_EMAILS", "team@yourcompany.com").split(",")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")

# Request Configuration
REQUEST_TIMEOUT = 10
BATCH_SLEEP_MIN = 0.2
BATCH_SLEEP_MAX = 0.6

# Threading Configuration
MAX_THREAD_POOL_SIZE = 500  # Maximum threads per batch (system safety limit)
