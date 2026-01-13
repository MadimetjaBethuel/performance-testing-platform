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
  gettext \
  git \
  libpq-dev

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