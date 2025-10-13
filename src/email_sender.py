import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import boto3
from config import SENDER_EMAIL, RECIPIENT_EMAILS, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD

def create_email_body(summary, detailed_results=None):
    """Create HTML email body with test results."""
    
    # Calculate additional metrics
    success_rate = (summary['success_count'] / summary['total_requests'] * 100) if summary['total_requests'] > 0 else 0
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
            .summary {{ background-color: #e8f4fd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .metrics {{ display: flex; flex-wrap: wrap; gap: 20px; }}
            .metric {{ background-color: white; padding: 15px; border: 1px solid #ddd; border-radius: 5px; min-width: 200px; }}
            .metric-value {{ font-size: 24px; font-weight: bold; color: #2c5aa0; }}
            .metric-label {{ font-size: 12px; color: #666; }}
            .status-good {{ color: #28a745; }}
            .status-warning {{ color: #ffc107; }}
            .status-error {{ color: #dc3545; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Performance Test Results</h1>
            <p><strong>Test Completed:</strong> {summary['timestamp']}</p>
            <p><strong>Total Duration:</strong> {summary['duration_sec']} seconds</p>
        </div>
        
        <div class="summary">
            <h2>Test Summary</h2>
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value">{summary['total_requests']}</div>
                    <div class="metric-label">Total Requests</div>
                </div>
                <div class="metric">
                    <div class="metric-value status-good">{summary['success_count']}</div>
                    <div class="metric-label">Successful Requests</div>
                </div>
                <div class="metric">
                    <div class="metric-value {'status-error' if summary['error_count'] > 0 else 'status-good'}">{summary['error_count']}</div>
                    <div class="metric-label">Failed Requests</div>
                </div>
                <div class="metric">
                    <div class="metric-value {'status-good' if success_rate > 95 else 'status-warning' if success_rate > 90 else 'status-error'}">{success_rate:.1f}%</div>
                    <div class="metric-label">Success Rate</div>
                </div>
            </div>
        </div>
        
        <div class="summary">
            <h2>Response Time Metrics</h2>
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value">{summary.get('avg_time', 0):.3f}s</div>
                    <div class="metric-label">Average Response Time</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{summary.get('min_time', 0):.3f}s</div>
                    <div class="metric-label">Minimum Response Time</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{summary.get('max_time', 0):.3f}s</div>
                    <div class="metric-label">Maximum Response Time</div>
                </div>
            </div>
        </div>
        
        <div class="summary">
            <h2>Test Configuration</h2>
            <p><strong>Concurrency Pattern:</strong> [20, 50, 100, 60, 30] users per phase</p>
            <p><strong>Phase Duration:</strong> 2 minutes each</p>
            <p><strong>Total Test Duration:</strong> 10 minutes</p>
        </div>
        
        <hr>
        <p><small>This is an automated performance test report. For detailed logs, check the S3 bucket or CloudWatch logs.</small></p>
    </body>
    </html>
    """
    
    return html_body

def send_email_via_smtp(summary, detailed_results=None):
    """Send email via SMTP (for local testing or custom SMTP servers)."""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Performance Test Results - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        msg['From'] = SENDER_EMAIL
        msg['To'] = ", ".join(RECIPIENT_EMAILS)
        
        # Create HTML body
        html_body = create_email_body(summary, detailed_results)
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        # Connect to SMTP server and send
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"Email sent successfully to {RECIPIENT_EMAILS}")
        return True
        
    except Exception as e:
        print(f"Failed to send email via SMTP: {e}")
        return False

def send_email_via_ses(summary, detailed_results=None):
    """Send email via Amazon SES."""
    try:
        ses_client = boto3.client('ses')
        
        html_body = create_email_body(summary, detailed_results)
        
        response = ses_client.send_email(
            Source=SENDER_EMAIL,
            Destination={'ToAddresses': RECIPIENT_EMAILS},
            Message={
                'Subject': {'Data': f"Performance Test Results - {datetime.now().strftime('%Y-%m-%d %H:%M')}"},
                'Body': {
                    'Html': {'Data': html_body}
                }
            }
        )
        
        print(f"Email sent via SES successfully to {RECIPIENT_EMAILS}")
        return True
        
    except Exception as e:
        print(f"Failed to send email via SES: {e}")
        return False

def send_performance_report(summary, detailed_results=None, use_ses=True):
    """Main function to send performance test report."""
    if use_ses:
        success = send_email_via_ses(summary, detailed_results)
        if not success:
            print("SES failed, trying SMTP fallback...")
            success = send_email_via_smtp(summary, detailed_results)
    else:
        success = send_email_via_smtp(summary, detailed_results)
    
    return success