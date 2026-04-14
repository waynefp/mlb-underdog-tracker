# Streamlit Dashboard — Deployment Guide

## Option A: Deploy on your Hostinger VPS (alongside n8n)

### 1. Google Service Account Setup

You need a service account so the app can read your Google Sheet.

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use existing)
3. Enable **Google Sheets API** and **Google Drive API**
4. Go to **Credentials → Create Credentials → Service Account**
5. Name it (e.g., "underdog-dashboard")
6. Download the JSON key file
7. **Share your Google Sheet** with the service account email
   (it looks like `name@project.iam.gserviceaccount.com`) — give it Viewer access

### 2. Upload to VPS

```bash
# SSH into your VPS
ssh user@your-vps-ip

# Create app directory
mkdir -p /opt/underdog-dashboard
cd /opt/underdog-dashboard

# Upload files (from your local machine)
# scp streamlit/app.py streamlit/requirements.txt user@your-vps-ip:/opt/underdog-dashboard/
# scp service_account.json user@your-vps-ip:/opt/underdog-dashboard/
```

### 3. Install & Run

```bash
cd /opt/underdog-dashboard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Test it
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

### 4. Run as a Service (persistent)

Create `/etc/systemd/systemd/underdog-dashboard.service`:

```ini
[Unit]
Description=MLB Underdog Dashboard
After=network.target

[Service]
User=root
WorkingDirectory=/opt/underdog-dashboard
ExecStart=/opt/underdog-dashboard/venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Restart=always
Environment="SHEET_NAME=MLB Underdog Tracker"

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable underdog-dashboard
sudo systemctl start underdog-dashboard
```

Access at: `http://your-vps-ip:8501`

### 5. Optional: Reverse Proxy with nginx

If you want a clean URL (e.g., underdogs.yourdomain.com):

```nginx
server {
    listen 80;
    server_name underdogs.yourdomain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Option B: Deploy on Streamlit Community Cloud (free)

1. Push the `streamlit/` folder to a GitHub repo
2. Go to [share.streamlit.io](https://share.streamlit.io/)
3. Connect your GitHub repo
4. Add secrets in Streamlit Cloud settings:
   - Go to app settings → Secrets
   - Paste your service account JSON as:
     ```toml
     [gcp_service_account]
     type = "service_account"
     project_id = "your-project-id"
     private_key_id = "..."
     private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
     client_email = "...@...iam.gserviceaccount.com"
     client_id = "..."
     auth_uri = "https://accounts.google.com/o/oauth2/auth"
     token_uri = "https://oauth2.googleapis.com/token"
     ```
5. Deploy — you get a public URL like `https://your-app.streamlit.app`

This is the fastest path if you don't want to manage infrastructure.

---

## Either way, the dashboard shows:

- **Top metrics**: Record, P/L, ROI at a glance
- **Cumulative P/L chart**: Trending up or down over time
- **Bucket performance**: Win rate vs. break-even rate per odds bucket
- **Home vs Away**: Do home underdogs outperform?
- **Best sportsbook**: Which book consistently has best underdog prices
- **Recent results**: Last 10 games with color-coded wins/losses
- **Pending games**: Today's picks waiting for results

All auto-refreshes every 5 minutes. Works great on mobile browsers.
