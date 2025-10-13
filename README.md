# Performance Testing Platform

A Docker-based performance testing platform that performs ramp tests on URLs and sends detailed reports via email. The platform supports concurrent load testing with configurable ramp-up patterns and integrates with AWS S3 for result storage.

## Project Structure

```
performance-testing-platform/
│
├── Dockerfile                    # Docker container configuration
├── docker-compose.yml           # Docker Compose for easy deployment
├── .dockerignore                # Files to exclude from Docker build
├── .env.example                 # Environment variables template
├── requirements.txt             # Python dependencies
├── serverless.yml              # Serverless configuration
├── data/
│   └── input.json              # URLs to test
├── src/
│   ├── config.py               # Configuration settings
│   ├── email_sender.py         # Email functionality
│   ├── lambda_handler.py       # Main application logic
│   └── url_loader.py           # URL loading utilities
└── templates/
    └── email_template.html     # HTML email template
```

## Docker Setup

### Prerequisites

- Docker and Docker Compose installed on your system
- AWS credentials configured (for S3 and SES integration)

### Quick Start with Docker

1. **Clone the repository** (or ensure you have the project files)

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your actual configuration values
   ```

3. **Build and run with Docker Compose**:
   ```bash
   # Build and run the application
   docker-compose up --build

   # Run in background
   docker-compose up -d --build
   ```

4. **For development** (with shell access):
   ```bash
   # Start development container
   docker-compose --profile dev up -d performance-dev

   # Access the container shell
   docker-compose exec performance-dev bash
   ```

### Manual Docker Commands

```bash
# Build the Docker image
docker build -t performance-testing-platform .

# Run the container with environment variables
docker run --env-file .env performance-testing-platform

# Run with mounted volumes for development
docker run -v $(pwd)/data:/app/data -v $(pwd)/src:/app/src --env-file .env performance-testing-platform
```

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example` with the following variables:

```bash
# AWS Configuration
OUTPUT_BUCKET=your-performance-results-bucket
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1

# Email Configuration
SENDER_EMAIL=performance-tests@yourcompany.com
RECIPIENT_EMAILS=team@yourcompany.com,admin@yourcompany.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

### Input Data

Ensure your `data/input.json` file contains the URLs to test:

```json
{
  "urls": [
    {"url": "https://example.com", "name": "Example Site"},
    {"url": "https://api.example.com/health", "name": "API Health Check"}
  ]
}
```

## Usage

### Running Performance Tests

The application automatically runs when the Docker container starts. It will:

1. Load URLs from `data/input.json`
2. Execute ramp tests with the configured concurrency patterns
3. Store results in AWS S3
4. Send email reports to configured recipients

### Development and Testing

```bash
# Start development environment
docker-compose --profile dev up -d

# Access container for debugging
docker-compose exec performance-dev bash

# View logs
docker-compose logs -f performance-testing

# Stop services
docker-compose down
```

## Traditional Setup (Without Docker)

If you prefer to run without Docker:

1. **Create virtual environment**:
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables** and **run**:
   ```bash
   export OUTPUT_BUCKET=your-bucket
   # ... other environment variables
   python -m src.lambda_handler
   ```

## AWS Configuration

1. **S3 Bucket**: Create a bucket for storing test results
2. **SES Setup**: Verify sender email in Amazon SES
3. **IAM Permissions**: Ensure AWS credentials have access to S3 and SES

## Features

- **Ramp Testing**: Configurable concurrency patterns for load testing
- **Multi-URL Support**: Test multiple endpoints simultaneously
- **Result Storage**: Automatic upload of results to AWS S3
- **Email Reports**: HTML and text email reports with detailed metrics
- **Docker Support**: Easy deployment and scaling with Docker
- **Concurrent Execution**: Thread-based concurrent request handling
- **Error Handling**: Comprehensive error tracking and reporting

## Monitoring and Logs

```bash
# View application logs
docker-compose logs -f performance-testing

# Check container status
docker-compose ps

# View resource usage
docker stats
```

### Step 2: `input.json`

Ensure that your `input.json` file is in the project directory. This file contains the URLs you want to test.

### Step 3: `lambda.py`

Here’s a sample `lambda.py` script that reads the URLs from `input.json`, performs a ramp test, and sends the report via email. This example uses the `boto3` library to send emails via Amazon SES (Simple Email Service) and the `requests` library to perform HTTP requests.

```python
import json
import requests
import boto3
from botocore.exceptions import ClientError

# Load URLs from input.json
def load_urls(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

# Perform ramp test
def ramp_test(urls):
    results = {}
    for url in urls:
        response_times = []
        for i in range(1, 11):  # Ramp up to 10 requests
            response = requests.get(url['url'])
            response_times.append(response.elapsed.total_seconds())
            print(f"Request {i} to {url['url']} took {response_times[-1]} seconds")
        results[url['url']] = response_times
    return results

# Send email report
def send_email_report(subject, body, recipient):
    ses_client = boto3.client('ses', region_name='us-east-1')  # Change to your region
    try:
        response = ses_client.send_email(
            Source='your_email@example.com',  # Change to your verified email
            Destination={
                'ToAddresses': [recipient],
            },
            Message={
                'Subject': {
                    'Data': subject,
                },
                'Body': {
                    'Text': {
                        'Data': body,
                    },
                },
            }
        )
    except ClientError as e:
        print(f"Failed to send email: {e.response['Error']['Message']}")
    else:
        print(f"Email sent! Message ID: {response['MessageId']}")

# Main function
def main():
    urls = load_urls('input.json')
    results = ramp_test(urls)
    
    # Prepare email report
    report = "Ramp Test Results:\n\n"
    for url, times in results.items():
        report += f"URL: {url}\nResponse Times: {times}\n\n"
    
    send_email_report("Ramp Test Report", report, "recipient@example.com")  # Change to your recipient

if __name__ == "__main__":
    main()
```

### Step 4: `requirements.txt`

Create a `requirements.txt` file to specify the dependencies:

```
boto3
requests
```

### Step 5: Deployment

1. **Install Dependencies**: Run the following command to install the required libraries:

   ```bash
   pip install -r requirements.txt
   ```

2. **AWS Configuration**: Ensure that you have configured AWS credentials that have permissions to use SES. You can do this using the AWS CLI:

   ```bash
   aws configure
   ```

3. **Verify Email**: Make sure that the sender email (`your_email@example.com`) is verified in Amazon SES.

4. **Run the Script**: You can run the script locally to test it:

   ```bash
   python lambda.py
   ```

### Step 6: Deploy to AWS Lambda (Optional)

If you want to deploy this script to AWS Lambda:

1. **Zip the Project**: Zip the project directory, including the `input.json`, `lambda.py`, and any dependencies.

2. **Create Lambda Function**: Go to the AWS Lambda console and create a new function. Upload the zip file.

3. **Set Environment Variables**: Set any necessary environment variables for your Lambda function, such as the email addresses.

4. **Test the Function**: Use the AWS Lambda console to test the function.

### Conclusion

This setup allows you to perform a ramp test on the URLs specified in `input.json` and send the results via email. Adjust the script as needed to fit your specific requirements.