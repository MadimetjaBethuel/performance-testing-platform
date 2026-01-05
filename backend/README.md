# Backend - FastAPI migration

This backend previously ran as an AWS Lambda function. It now exposes a FastAPI application that wraps the same test logic and configuration.

## Run locally

Install dependencies (from the `backend` folder):

```bash
python -m venv .env
source .env/bin/activate
pip install -r requirements.txt
```

Run server using uvicorn:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8080
```

Health check:

```bash
curl http://localhost:8080/health
```

Run a synchronous test (blocks while test runs):

```bash
curl -X POST http://localhost:8080/run -H 'Content-Type: application/json' -d '{}'
```

Start test in the background:

```bash
curl -X POST http://localhost:8080/run -H 'Content-Type: application/json' -d '{"background": true}'
```

Override URLs or configuration:

```bash
curl -X POST http://localhost:8080/run -H 'Content-Type: application/json' -d '{"urls": ["https://example.com"], "concurrency_steps": [10, 20], "phase_length": 60, "background": false}'
```

## Docker

The `backend/Dockerfile` was updated to run the FastAPI app via uvicorn. Build and run the container:

```bash
# from project root
docker build -t perf-backend -f backend/Dockerfile ./backend
docker run -p 8080:8080 perf-backend
```

## Notes

- `src/main.py` provides the new FastAPI application with endpoints `/health` and `/run`.
- `src/lambda_handler.py` now supports runtime overrides passed via the `event` argument when called from the API.
- Long-running tests may block requests if run synchronously; use `background:true` in the POST body to run tests as a background task.
