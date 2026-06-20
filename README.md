# AzureCostTracker - ACT

**Azure Cost Tracker** (ACT) is a professional cost management and reporting utility. It tracks **Azure subscription costs**, generates **interactive glassmorphic dashboard reports**, compiles professional **PDF attachments** using WeasyPrint, and sends notifications via **email** or **webhooks (Slack, MS Teams, etc.)**.

### 📊 Feature Preview:
<img src="static/images/report_screenshot.png" width="90%" alt="Report Screenshot"></img>

---

## 🌟 Upgraded Features

* **Dual-Mode Execution**:
  * 🌐 **Server Mode (`--server`)**: Launches a local FastAPI server (`http://localhost:8000`) with an interactive, real-time dashboard. Features background task queues for on-demand email/webhook reports, thread-safe memory caching, and dynamic **Chart.js** doughnut charts.
  * 🖥️ **CI/CD Mode (Default)**: Runs completely headless and in-memory. Fetches billing API data, generates the HTML/PDF reports, dispatches notifications, and exits silently without polluting the workspace filesystem.
  * 👁️ **Preview Mode (`--preview`)**: Compiles a static HTML copy to `output/preview.html` and automatically launches the native system web browser for rapid inspection.
* 📄 **Automated PDF Export**: Automatically compiles the highly styled cost reports into professional, printable PDF attachments using **WeasyPrint** to accompany outbound emails.
* 💱 **Dynamic Billing Currency**: Automatically detects the billing currency (e.g., `USD`, `CAD`, `EUR`, `INR`) from the Azure Billing API response, dynamically mapping symbols (e.g., `$`, `€`, `£`, `₹`) across all tables, visual cards, charts, and webhook notifications.
* **Modular Template Architecture**: Refactored the monolithic report layout into clean, separate components in `templates/components/` (styles, header, tables, charts, scripts) for enhanced maintainability.
* **Email Client Compatible Layouts**: Switched from CSS Grid and CSS variables (which are stripped by email parsers) to robust inline tables and flexbox layouts, guaranteeing pixel-perfect layout rendering in both browser viewports and desktop/mobile webmail clients (like Gmail and Outlook).

---

## 📂 Project Structure

```
azure-cost-tracker/
│── src/
│   ├── main.py                        # CLI entrypoint (argument parsing & execution routes)
│   ├── app.py                         # FastAPI web server and backend API endpoints
│   ├── config.py                      # Configurations (.env variables, subscription lists)
│   ├── services/
│   │   ├── azure_auth.py              # Fetches and manages Access Token (includes Mock mode)
│   │   ├── azure_billing.py           # Fetches billing period/days
│   │   ├── azure_cost.py              # Queries cost APIs for daily, MTD, YTD & forecast numbers
│   │   ├── email_service.py           # Compiles MIME messages with file attachments
│   │   ├── html_renderer.py           # Jinja template rendering & WeasyPrint PDF compilation
│   │   ├── webhook_service.py         # Formats and posts markdown messages to webhooks
│   ├── utils/
│   │   ├── logger.py                  # Standardized console/file logger
│   │   ├── utils.py                   # Math, formatting, and currency mapping utilities
│── templates/
│   ├── report_template.html           # Main universal Jinja2 layout skeleton
│   ├── components/                    # Modular, reusable UI components
│   │   ├── control_bar.html           # Action controls for dashboard server
│   │   ├── header.html                # Header block with dynamic currency support
│   │   ├── summary_cards.html         # Daily, MTD, and forecast totals
│   │   ├── comparison_tables.html     # Subscription compare tables & inline progress bars
│   │   ├── service_breakdown.html     # MTD service breakdowns and chart canvases
│   │   ├── styles.html                # Email-client and PDF-compatible styling definitions
│   │   ├── scripts.html               # AJAX API triggers and Chart.js setup
│── tests/
│   ├── test_act_utils.py              # Pytest suite validating math & formatting logic
│   ├── test_services.py               # Pytest suite mocking SMTP and Webhook transmission
│── output/                            # Local previews and PDF archives (git ignored)
│── .env                               # Environment credentials
│── README.md                          # Project documentation
│── requirements.txt                   # Dependency list
│── setup.py                           # Package deployment configuration
```

---

## 🔧 Setup Instructions

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/interittus13/AzureCostTracker
cd AzureCostTracker
```

### 2️⃣ Configure Environment
Create a `.env` file in the root directory:
```env
TENANT_ID=your-azure-tenant-id
CLIENT_ID=your-azure-client-id
CLIENT_SECRET=your-azure-client-secret
SUBSCRIPTION_IDS=subscription-id1,subscription-id2

# Notification settings
EMAIL_FROM=your-email@example.com
EMAIL_TO=recipient1@example.com,recipient2@example.com
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_PASS=your-smtp-password

WEBHOOK_URL=https://your-teams-webhook-url
NOTIFY_METHOD=email  # Options: email, webhook, both
MOCK_AZURE=true       # Set to true for developer sandbox (runs without Azure credentials)
```

---

## 🚀 Execution Guide

Make sure your virtual environment is activated, then run:

### 1. Headless CI/CD Mode (Default)
Optimal for automated cron jobs or GitHub Actions runner:
```bash
python -m src.main
```
*Fetches billing metrics, builds the PDF, triggers email notifications with the PDF attachment, and exits silently.*

### 2. Developer Static Preview
Generates local files and opens the system browser:
```bash
python -m src.main --preview
```

### 3. Launch Interactive Dashboard Server
Spins up the FastAPI server on port 8000:
```bash
python -m src.main --server
```
Navigate to `http://localhost:8000` to interact with:
* **Manual Refresh**: Forces cache clearance and re-fetches Azure costs.
* **On-Demand Notification Triggers**: Triggers background email (with PDF attachment) or webhook notifications instantly.
* **Chart.js Donuts**: Inspect breakdown ratios with fully responsive tooltips.

### 4. Run Verification Tests
Runs both math helper tests and SMTP/HTTP mock assertion suites:
```bash
python -m pytest tests/
```

---

## 📡 Webhook Setup
1. Go to **Microsoft Teams** / **Slack** → **Your Channel** → Create an **Incoming Webhook**.
2. Copy the generated Webhook URL and paste it in `.env` under `WEBHOOK_URL`.
3. Webhook alerts will deliver formatted markdown breakdown logs.

---

## 📜 License
This project is open-source under the **MIT License**.
