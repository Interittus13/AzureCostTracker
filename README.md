# AzureCostTracker - ACT

**Azure Cost Tracker** is a Python-based tool that tracks **Azure subscription costs**, generates **HTML reports**, and sends notifications via **email** or **webhooks (Microsoft Teams, Slack, etc.)**.

---

## **🚀 Features**
✅ Fetches **daily and monthly** cost reports for Azure subscriptions.  
✅ Supports **custom billing periods** per subscription.  
✅ Sends notifications via **email and webhook** (Microsoft Teams, Slack, etc.).  
✅ Allows **previewing email reports** before sending.  
✅ Follows **best-practice Python project structure**.

---

## **📂 Project Structure**
```
azure-cost-tracker/
│── src/
│   ├── main.py               # Main script
│   ├── config.py             # Configurations (subscriptions, billing periods)
│   ├── services/
│   │   ├── azure_auth.py     # Fetch and Manages Access Token
│   │   ├── azure_billing.py  # Fetch Azure subscription's billing details
│   │   ├── azure_cost.py     # Fetch Azure cost data
│   │   ├── email_service.py  # Preview HTML reports
│   │   ├── html_renderer.py  # Render HTML reports
│   │   ├── notifications.py  # Send email and webhook notifications
│   ├── utils/
│   │   ├── logger.py         # Logging setup
│   │   ├── utils.py          # Helper functions
│── templates/
│   ├── email_template.html   # Email template
│── .env                      # Environment variables
│── README.md                 # Project documentation
│── requirements.txt          # Dependencies
│── setup.py                  # Package setup
```

---

## **🔧 Setup Instructions**

### **1️⃣ Clone the Repository**
```bash
git clone https://github.com/interittus13/AzureCostTracker
cd azurecosttracker
```

### **2️⃣ Install Dependencies**
```bash
pip install -r requirements.txt
```

### **3️⃣ Configure `.env` File**
Create a `.env` file with your settings:
```
TENANT_ID=your-azure-tenant-id
CLIENT_ID=your-azure-client-id
CLIENT_SECRET=your-azure-client-secret
SUBSCRIPTION_IDS=subscription-id1,subscription-id2

EMAIL_FROM=your-email@example.com
EMAIL_TO=test@example.com,test2@yopmail.com
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_PASS=your-password

WEBHOOK_URL=https://your-teams-webhook-url
NOTIFY_METHOD=email  # Options: email, webhook, both
```

---

## **📊 Running the Script**

### **Run Manually**
```bash
python -m src.main
```

### **Using CLI Command (if installed via setup.py)**
```bash
azure-cost-tracker
```

---

## **📤 Notification Methods**

### **1️⃣ Email Notification**  
- Sends a **formatted HTML report** via Outlook.
- Supports **multiple recipients** (comma-separated in `.env`).
- Email preview before sending.

### **2️⃣ Webhook Notification (e.g., Microsoft Teams, Slack)**
- Sends a **summary message** via webhook.
- Supports **Teams, Slack, and custom webhooks**.
- Uses `WEBHOOK_URL` from `.env`.

### **3️⃣ Both (Email + Webhook)**
- Sends both **email and webhook** notifications when `NOTIFY=both`.

---

## **📡 How to Set Up a Microsoft Teams Webhook**
1️⃣ Go to **Microsoft Teams** → **Your Channel** → Click `...` → `Connectors`.  
2️⃣ Search for **"Incoming Webhook"** → Click `Add`.  
3️⃣ Name the webhook (e.g., `Azure Cost Alerts`).  
4️⃣ Copy the generated **Webhook URL**.  
5️⃣ Add it to `.env`:
   ```
   WEBHOOK_URL=https://your-teams-webhook-url
   ```

---

## **📜 License**
This project is **open-source** under the **MIT License**.
