#!/bin/bash
# Jenkins Security Setup - Fail2ban Configuration
# Run this script on the production server to protect Jenkins from brute-force attacks

set -e

echo "=========================================="
echo "Jenkins Security Setup with Fail2ban"
echo "=========================================="
echo ""

# Install fail2ban
echo "[1/5] Installing fail2ban..."
sudo apt-get update
sudo apt-get install -y fail2ban

# Create fail2ban filter for Jenkins
echo "[2/5] Creating Jenkins fail2ban filter..."
sudo tee /etc/fail2ban/filter.d/jenkins.conf > /dev/null << 'EOF'
[Definition]
failregex = ^.*Failed login attempt .* from <HOST>.*$
            ^.*Invalid login attempt .* from <HOST>.*$
            ^.*Authentication failure .* from <HOST>.*$
ignoreregex =
EOF

# Create fail2ban jail configuration for Jenkins
echo "[3/5] Creating Jenkins jail configuration..."
sudo tee /etc/fail2ban/jail.d/jenkins.conf > /dev/null << 'EOF'
[jenkins]
enabled = true
port = 8080
filter = jenkins
logpath = /var/log/jenkins/jenkins.log
maxretry = 5
findtime = 600
bantime = 3600
action = iptables-allports[name=jenkins]
EOF

# Check if Jenkins log exists and create if needed
echo "[4/5] Checking Jenkins log configuration..."
if [ ! -f /var/log/jenkins/jenkins.log ]; then
    echo "Jenkins log not found at /var/log/jenkins/jenkins.log"
    echo "Please ensure Jenkins is logging to this location or update jail.d/jenkins.conf"
fi

# Start and enable fail2ban
echo "[5/5] Starting fail2ban service..."
sudo systemctl enable fail2ban
sudo systemctl restart fail2ban

# Show status
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Fail2ban is now protecting Jenkins with the following settings:"
echo "  - Max retries: 5 failed attempts"
echo "  - Time window: 10 minutes (600 seconds)"
echo "  - Ban duration: 1 hour (3600 seconds)"
echo ""
echo "Useful commands:"
echo "  sudo fail2ban-client status jenkins     # Check Jenkins jail status"
echo "  sudo fail2ban-client status             # List all active jails"
echo "  sudo fail2ban-client set jenkins unbanip <IP>  # Manually unban an IP"
echo "  sudo tail -f /var/log/fail2ban.log      # Monitor fail2ban activity"
echo "  sudo iptables -L -n | grep -A 10 f2b-jenkins  # View blocked IPs"
echo ""
