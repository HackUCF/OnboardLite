# Deployment Guide

This guide covers deploying OnboardLite to a production environment.

## Prerequisites

- A server with Ubuntu/Debian (recommended)
- Domain name with DNS configured
- AWS account (for DynamoDB)
- Stripe account (for payments)
- Discord application (for authentication)

## Step-by-Step Deployment

### 1. Server Setup

Deploy a server and ensure you have root access.

### 2. AWS Configuration

1. **Create an AWS user** with the following policies:
   - `AmazonDynamoDBFullAccess`
   - `PowerUserAccess` (or preferably, a custom policy with `dynamodb:*` and `sso:account:access` actions)

2. **Install the AWS CLI** on your server:
   ```bash
   # Follow the official guide: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
   ```

3. **Configure AWS CLI**:
   ```bash
   aws configure sso
   ```
   See [AWS SSO Configuration Guide](https://docs.aws.amazon.com/cli/latest/userguide/sso-configure-profile-token.html) for details.

4. **Create DynamoDB table**:
   - Table name: `hackucf_members` (default)
   - Partition key: `id`

### 3. Stripe Configuration

1. **Set up webhook**:
   - Create a webhook at `$YOUR_DOMAIN/pay/webhook/validate`
   - Include events: `checkout.session.*`

2. **Create payment product**:
   - Create a product for dues payments in the Stripe dashboard
   - Price: $10 + $0.60 (to account for Stripe fees)

3. **Activate account**: Ensure your Stripe account is fully activated for live transactions.

### 4. System Dependencies

Install required system packages:
```bash
sudo apt update
sudo apt install -y nginx certbot build-essential python3.11 python3.11-dev redis
```

You may need to install pip separately:
```bash
# If pip3.11 is not available, use:
wget https://bootstrap.pypa.io/get-pip.py
python3.11 get-pip.py
```

### 5. Application Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/HackUCF/OnboardLite.git
   cd OnboardLite
   ```

2. **Install Python dependencies**:
   ```bash
   python3.11 -m pip install -r requirements.txt
   ```

3. **Configure the application**:
   - Request a configuration file with all necessary secrets for AWS, Stripe, Discord, and other services
   - Place the configuration file at `config/options.yml`

### 6. Web Server Configuration

#### Nginx Setup

Create a new site configuration. Replace `join.hackucf.org` with your domain:

```bash
sudo nano /etc/nginx/sites-available/onboardlite
```

Add the following configuration:
```nginx
server {
    listen 80;
    listen [::]:80;

    server_name your-domain.com;

    proxy_set_header X-Forwarded-For $proxy_protocol_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Host $host;

    root /var/www/html;
    index index.html;

    location ^~ / {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/onboardlite /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### HTTPS Configuration

Set up HTTPS with Let's Encrypt:
```bash
sudo certbot --nginx -d your-domain.com
```

**Important**: If using Cloudflare, configure SSL/TLS settings appropriately to avoid certificate conflicts.

### 7. Application Service

Create a systemd service file. Replace paths as appropriate:

```bash
sudo nano /etc/systemd/system/onboardlite.service
```

Add the following configuration:
```ini
[Unit]
Description=Uvicorn instance to serve OnboardLite
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/onboard-user/OnboardLite/
Environment="PATH=/home/onboard-user/OnboardLite/"
ExecStart=python3.11 -m uvicorn index:app --host 127.0.0.1 --port 8000 --workers 2

[Install]
WantedBy=multi-user.target
```

Start and enable the service:
```bash
sudo systemctl daemon-reload
sudo systemctl start onboardlite
sudo systemctl enable onboardlite
sudo systemctl status onboardlite
```

### 8. Redis Setup

Start and enable Redis:
```bash
sudo systemctl start redis
sudo systemctl enable redis
```

### 9. Apple Wallet Configuration (Optional)

If using Apple Wallet features:

1. Generate Apple Wallet secrets following [this tutorial](https://github.com/alexandercerutti/passkit-generator/wiki/Generating-Certificates)
2. Place the certificates in `config/pki/`

### 10. Content Security Policy

Configure appropriate security headers in your Nginx configuration. Add to the `server` block:

```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https:; connect-src 'self' https:;";
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header Referrer-Policy strict-origin-when-cross-origin;
```

### 11. Cloudflare (Optional)

If using Cloudflare:
1. Configure DNS settings to proxy through Cloudflare
2. Set up appropriate SSL/TLS settings
3. Configure security rules as needed

## Post-Deployment Configuration

### Administrator Setup

The initial administrator must be set via DynamoDB's web interface:

1. Go to the AWS DynamoDB console
2. Find your `hackucf_members` table
3. Create/edit a user record to set administrator privileges

**Note**: Administrators should be FERPA-trained by UCF (either using RSO training or general TA training).

### Security Considerations

1. **Administrators vs. Executives**: Administrators are trusted Operations members who can view roster logs, not the same as Executives.

2. **FERPA Compliance**: Ensure all administrators are properly FERPA-trained.

3. **Regular Updates**: Keep all system packages and dependencies updated.

4. **Backup Strategy**: Implement regular backups of your DynamoDB data.

5. **Monitoring**: Set up monitoring for the application and server health.

## Maintenance

### Log Monitoring

Monitor application logs:
```bash
sudo journalctl -u onboardlite -f
```

Monitor Nginx logs:
```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Updates

To update the application:
1. Pull the latest code: `git pull`
2. Install any new dependencies: `python3.11 -m pip install -r requirements.txt`
3. Restart the service: `sudo systemctl restart onboardlite`

### SSL Certificate Renewal

Certbot should automatically renew certificates, but you can test renewal:
```bash
sudo certbot renew --dry-run
```

## Troubleshooting

### Common Issues

1. **Service won't start**: Check logs with `sudo journalctl -u onboardlite`
2. **Database connection issues**: Verify AWS credentials and DynamoDB table configuration
3. **Nginx errors**: Check configuration with `sudo nginx -t`
4. **SSL issues**: Verify certificate status with `sudo certbot certificates`

### Security Incident Response

If you discover a security vulnerability, please report it to `execs@hackucf.org` immediately.

## Monitoring and Alerting

Consider setting up:
- Application performance monitoring (APM)
- Server monitoring (CPU, memory, disk usage)
- Uptime monitoring
- Log aggregation and alerting
- Database monitoring

## Scaling Considerations

For high-traffic deployments, consider:
- Load balancing with multiple application instances
- Database read replicas
- CDN for static assets
- Caching layer (Redis/Memcached)
- Container orchestration (Docker + Kubernetes)