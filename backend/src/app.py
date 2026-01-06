from flask import Flask, jsonify, request
from engine.core import run_performance_test
from url_loader import validate_urls, load_urls_from_json
from config import CONCURRENCY_STEPS, PHASE_LENGTH, REQUEST_TIMEOUT


app = Flask(__name__)


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200


@app.route('/run', methods=['POST'])
def run_test():
    payload = request.get_json(silent=True) or {}

    urls = payload.get('urls', []) or load_urls_from_json()
    urls = validate_urls(urls)
    if not urls:
        return jsonify({"error": "No valid URLs provided."}), 400

    summary, _ = run_performance_test(
        urls=urls,
        concurrency_steps=payload.get('concurrency_steps', CONCURRENCY_STEPS),
        phase_length=payload.get('phase_length', PHASE_LENGTH),
        request_timeout=payload.get('request_timeout', REQUEST_TIMEOUT),
        save_to_s3=payload.get('save_to_s3', False),
        send_email=payload.get('send_email', False)
    )

    return jsonify({"summary": summary}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
