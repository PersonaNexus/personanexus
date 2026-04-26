# 🌐 PersonaNexus Web UI - Deployment Guide

The Identity Lab is a Streamlit-based web application with five modes: **Studio**, **Playground**, **Setup Wizard**, **Analyze**, and **Evolution Lab**. Studio is the premium visual workspace for the agent gallery, persona canvas, motifs, and personality signatures. This guide covers deployment options from local development to production hosting.

## 📋 Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- PersonaNexus framework installed (`pip install personanexus` or local development setup)

### Local Setup
```bash
# From the personanexus root directory
cd web

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Run the Streamlit app
streamlit run app.py

# App will be available at http://localhost:8501
```

### Development with Live Reload
```bash
# For development with auto-reload on file changes
streamlit run app.py --server.runOnSave true
```

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

Create `docker-compose.yml` in the web directory:

```yaml
version: '3.8'

services:
  identity-lab:
    build: .
    ports:
      - "8501:8501"
    environment:
      - STREAMLIT_SERVER_PORT=8501
      - STREAMLIT_SERVER_ADDRESS=0.0.0.0
      - STREAMLIT_SERVER_HEADLESS=true
      - STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
    volumes:
      # Optional: Mount local examples directory
      - ../examples:/app/examples:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
```

Create `Dockerfile` in the web directory:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install personanexus package
# Option 1: Install from PyPI (when published)
RUN pip install personanexus

# Option 2: Install from source (development)
# COPY ../src /app/src
# COPY ../pyproject.toml /app/
# RUN pip install -e .

# Copy web application files
COPY *.py ./
COPY assets/ ./assets/

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose Streamlit port
EXPOSE 8501

# Configure Streamlit
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run the application
CMD ["streamlit", "run", "app.py"]
```

### Build and Run
```bash
# Build and start the service
docker-compose up -d

# View logs
docker-compose logs -f identity-lab

# Stop the service
docker-compose down
```

## ☁️ Streamlit Cloud Deployment

### Option 1: Direct from GitHub

1. **Fork or push to GitHub**: Ensure your personanexus repository is on GitHub
2. **Visit [share.streamlit.io](https://share.streamlit.io)**
3. **Create new app**:
   - Repository: `yourusername/personanexus`
   - Branch: `main` 
   - Main file path: `web/app.py`
   - Python version: `3.11`

### Option 2: Configuration File

Create `web/.streamlit/config.toml`:

```toml
[server]
port = 8501
headless = true

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
```

Create `web/packages.txt` (if system dependencies needed):
```
curl
```

### Streamlit Cloud Environment Variables
Set these in your Streamlit Cloud app settings:
- `PYTHONPATH=/app`
- Any API keys if using external services

## 🌐 Production Deployment

### Option 1: Traditional VPS/Server

#### Using systemd (Ubuntu/Debian)

Create `/etc/systemd/system/identity-lab.service`:

```ini
[Unit]
Description=PersonaNexus Lab Web UI
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/personanexus/web
Environment=PATH=/opt/personanexus/venv/bin
Environment=PYTHONPATH=/opt/personanexus
ExecStart=/opt/personanexus/venv/bin/streamlit run app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Setup commands:
```bash
# Create application directory
sudo mkdir -p /opt/personanexus
sudo chown www-data:www-data /opt/personanexus

# Clone and setup (as www-data user)
sudo -u www-data git clone https://github.com/yourusername/personanexus.git /opt/personanexus
cd /opt/personanexus

# Create virtual environment
sudo -u www-data python3 -m venv venv
sudo -u www-data ./venv/bin/pip install -e .
sudo -u www-data ./venv/bin/pip install -r web/requirements.txt

# Enable and start service
sudo systemctl enable identity-lab
sudo systemctl start identity-lab
sudo systemctl status identity-lab
```

#### Nginx Reverse Proxy

Create `/etc/nginx/sites-available/identity-lab`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # WebSocket support for Streamlit
        proxy_read_timeout 86400;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/identity-lab /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Option 2: Cloud Platforms

#### Google Cloud Run

Create `web/Dockerfile` (optimized for Cloud Run):

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install personanexus

# Copy application
COPY *.py ./

# Use Cloud Run port
ENV PORT 8080
ENV STREAMLIT_SERVER_PORT=$PORT
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true

EXPOSE $PORT

CMD streamlit run app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
```

Deploy commands:
```bash
# Build and push to Google Container Registry
docker build -t gcr.io/your-project/identity-lab ./web
docker push gcr.io/your-project/identity-lab

# Deploy to Cloud Run
gcloud run deploy identity-lab \
    --image gcr.io/your-project/identity-lab \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --max-instances 10
```

#### AWS ECS/Fargate

Create `web/task-definition.json`:

```json
{
  "family": "identity-lab",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "identity-lab",
      "image": "your-account.dkr.ecr.region.amazonaws.com/identity-lab:latest",
      "portMappings": [
        {
          "containerPort": 8501,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "STREAMLIT_SERVER_PORT",
          "value": "8501"
        },
        {
          "name": "STREAMLIT_SERVER_ADDRESS", 
          "value": "0.0.0.0"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/identity-lab",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

## 🔧 Configuration & Customization

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STREAMLIT_SERVER_PORT` | `8501` | Port for the web server |
| `STREAMLIT_SERVER_ADDRESS` | `localhost` | Bind address (use `0.0.0.0` for public) |
| `STREAMLIT_SERVER_HEADLESS` | `false` | Run without opening browser |
| `STREAMLIT_BROWSER_GATHER_USAGE_STATS` | `true` | Disable Streamlit usage tracking |
| `STREAMLIT_THEME_PRIMARY_COLOR` | `#FF6B6B` | Primary theme color |

### Custom Configuration

Create `web/.streamlit/config.toml`:

```toml
[server]
port = 8501
headless = true
maxUploadSize = 50

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"

[global]
developmentMode = false
```

### Adding Custom Archetypes

```python
# In web/app.py or separate config file
CUSTOM_ARCHETYPES = {
    "my_archetype": {
        "name": "My Custom Archetype",
        "description": "Description of the archetype",
        "traits": {
            "warmth": 0.8,
            "rigor": 0.9
            # ... other traits
        }
    }
}
```

## 📊 Monitoring & Logging

### Application Logs

```bash
# Docker Compose
docker-compose logs -f identity-lab

# systemd
sudo journalctl -u identity-lab -f

# Streamlit specific logs
streamlit run app.py --logger.level debug
```

### Health Checks

The application provides several health check endpoints:

- `/_stcore/health` - Streamlit internal health check
- Custom health check can be added to `app.py`:

```python
# Add to app.py
def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "version": "1.3.0"}

# Register with Streamlit
st.experimental_set_query_params(health=health_check)
```

### Performance Monitoring

For production deployments, consider:

- **Application Performance Monitoring (APM)**: New Relic, DataDog
- **Log aggregation**: ELK Stack, Grafana Loki
- **Metrics**: Prometheus + Grafana
- **Uptime monitoring**: Pingdom, UptimeRobot

## 🛡️ Security Considerations

### HTTPS/TLS

Always use HTTPS in production:

```bash
# With Let's Encrypt (Certbot)
sudo certbot --nginx -d your-domain.com
```

### Access Control

For private deployments, add authentication:

```python
# Add to app.py
import streamlit_authenticator as stauth

# Simple password protection
def check_password():
    def password_entered():
        if st.session_state["password"] == "your_secret_password":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Password", type="password", 
                     on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Password", type="password", 
                     on_change=password_entered, key="password")
        st.error("Password incorrect")
        return False
    else:
        return True

# Use at the top of your main app
if not check_password():
    st.stop()
```

### File Upload Security

Limit file types and sizes:

```python
# In analyze mode file upload
uploaded_file = st.file_uploader(
    "Upload personality file",
    type=['yaml', 'yml', 'md', 'json'],
    max_size_mb=10
)
```

## 🔄 Updates & Maintenance

### Updating the Application

```bash
# Docker Compose
docker-compose pull && docker-compose up -d

# systemd deployment
sudo -u www-data git pull
sudo -u www-data ./venv/bin/pip install -e .
sudo systemctl restart identity-lab
```

### Database/State Persistence

Streamlit is stateless by default. For persistent data:

- Use external databases (PostgreSQL, MongoDB)
- Mount volumes for file storage
- Consider Redis for session state

### Backup Strategy

```bash
# Backup user-generated content (if any)
# Examples, configurations, uploaded files
tar -czf identity-lab-backup-$(date +%Y%m%d).tar.gz \
    /opt/personanexus/examples \
    /opt/personanexus/user-uploads
```

## 🚨 Troubleshooting

### Common Issues

**Port already in use:**
```bash
# Find process using port 8501
lsof -ti:8501
# Kill the process
kill -9 $(lsof -ti:8501)
```

**Module not found:**
```bash
# Ensure personanexus is installed
pip list | grep personanexus
# Reinstall if needed
pip install -e .
```

**Streamlit connection errors:**
- Check firewall settings
- Verify bind address (0.0.0.0 vs localhost)
- Confirm port accessibility

**Memory issues:**
- Increase container/system memory
- Check for memory leaks in analyze mode
- Implement file size limits

### Debug Mode

```bash
# Run with debug logging
streamlit run app.py --logger.level debug

# Or set environment variable
export STREAMLIT_LOGGER_LEVEL=debug
streamlit run app.py
```

## 📞 Support

For deployment issues:
1. Check the logs first
2. Verify all dependencies are installed
3. Test with minimal configuration
4. Check network connectivity and firewall rules
5. Report issues with full error messages and configuration details

---

**The Identity Lab Web UI provides an intuitive interface for exploring agent personalities, building team configurations, and analyzing existing personality files. Choose the deployment option that best fits your infrastructure and security requirements.**