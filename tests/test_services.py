from unittest.mock import patch, MagicMock
from src.services.email_service import send_email_notification
from src.services.webhook_service import send_webhook_notification

@patch("src.services.email_service.smtplib.SMTP")
def test_send_email_notification(mock_smtp):
    # Mock SMTP context manager and instance
    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server

    # Patch config variables within local test environment
    with patch("src.services.email_service.EMAIL_TO", "recipient@test.com"), \
         patch("src.services.email_service.EMAIL_FROM", "sender@test.com"), \
         patch("src.services.email_service.SMTP_SERVER", "smtp.test.com"), \
         patch("src.services.email_service.SMTP_PORT", 587), \
         patch("src.services.email_service.SMTP_PASS", "mypassword"):
        
        send_email_notification("Test Subject", "<p>Test Content</p>", attachments=[])
        
    # Verify SMTP handshake, authentication, and transmission
    mock_smtp.assert_called_once_with("smtp.test.com", 587)
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("sender@test.com", "mypassword")
    mock_server.sendmail.assert_called_once()

@patch("src.services.webhook_service.requests.post")
def test_send_webhook_notification(mock_post):
    # Mock HTTP response
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    mock_data = {
        "report_for": "2026-06-18",
        "report_generated_on": "2026-06-19",
        "currency_symbol": "$",
        "subscriptions": [
            {
                "subscription_name": "Dev Sub",
                "daily_cost": 10.0,
                "month_to_day": 100.0,
                "month_forecast": 150.0,
                "service_breakdown": [
                    {"service": "Virtual Machines", "cost": "$100.00"}
                ]
            }
        ]
    }

    # Patch WEBHOOK_URL
    with patch("src.services.webhook_service.WEBHOOK_URL", "http://webhook.test.com"):
        send_webhook_notification(mock_data)

    # Verify requests.post call targets correct URL and holds Markdown payload
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "http://webhook.test.com"
    assert "text" in kwargs["json"]
    assert "Azure Cost Tracker Report" in kwargs["json"]["text"]
    assert "Dev Sub" in kwargs["json"]["text"]
