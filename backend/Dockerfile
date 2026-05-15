# backend/Dockerfile
FROM python:3.13-slim

# Install Poetry

# Configure Poetry to not create virtual environments (we're in a container)
ENV POETRY_VERSION=1.7.1 \
  POETRY_NO_INTERACTION=1 \
  POETRY_VIRTUALENVS_CREATE=false \
  POETRY_HOME='/etc/poetry' \
  POETRY_CACHE_DIR='/var/cache/pypoetry'

RUN apt-get update \
  && apt-get install --no-install-recommends -y \
  bash \
  build-essential \
  curl \
  default-jre-headless \
  gettext \
  git \
  libpq-dev \
  && rm -rf /var/lib/apt/lists/*

# Install Apache JMeter for scenario (.jmx) load + functional testing.
# Pinned version. Tries the CDN mirror first (fast, current versions only) and
# falls back to archive.apache.org (slow but has every historical version).
# Both are retried — Apache mirrors have been known to drop TLS connections.
ENV JMETER_VERSION=5.6.3 \
  JMETER_HOME=/opt/apache-jmeter-5.6.3
RUN (curl --retry 5 --retry-delay 10 --retry-connrefused -fsSL \
       "https://dlcdn.apache.org/jmeter/binaries/apache-jmeter-${JMETER_VERSION}.tgz" \
       -o /tmp/jmeter.tgz \
     || curl --retry 5 --retry-delay 10 --retry-connrefused -fsSL \
       "https://archive.apache.org/dist/jmeter/binaries/apache-jmeter-${JMETER_VERSION}.tgz" \
       -o /tmp/jmeter.tgz) \
  && tar -xzf /tmp/jmeter.tgz -C /opt \
  && rm /tmp/jmeter.tgz
ENV PATH="${JMETER_HOME}/bin:${PATH}"
RUN jmeter -v

# Install Taurus (bzt) — wraps JMeter under a YAML interface. Lets us accept
# .yaml exports from the BlazeMeter Chrome extension directly. Installed via
# pip (not poetry) because Taurus has many pinned transitive deps that fight
# with poetry's resolver and we only need it as a CLI tool, not an import.
RUN pip install --no-cache-dir --break-system-packages bzt \
  && bzt --help > /dev/null

RUN curl -sSL https://install.python-poetry.org | python -
ENV PATH="/root/.poetry/bin:root/.local/bin:$POETRY_HOME/bin:${PATH}"
RUN poetry --version


WORKDIR /app

# Copy dependency files
COPY poetry.lock pyproject.toml ./

# Install dependencies (without dev dependencies for production)
RUN poetry install --no-interaction --no-ansi --no-dev

# Copy application code
COPY . .

# Install the project itself if it's a package
RUN poetry install --no-dev --no-root --no-interaction

# Expose port
EXPOSE 5001

# Run the application
CMD ["python", "src/app.py"]