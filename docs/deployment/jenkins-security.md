# Jenkins Security Configuration

## Overview
This document covers the security hardening of Jenkins against brute-force login attempts using fail2ban.

## fail2ban Setup

### Installation
Run the setup script on the production server:

```bash
# Copy the script to the server
scp docs/deployment/setup-jenkins-security.sh tmsanity_admin@165.73.87.59:~

# SSH to the server
ssh tmsanity_admin@165.73.87.59

# Make executable and run
chmod +x setup-jenkins-security.sh
./setup-jenkins-security.sh
```

### Configuration Details

**Protection Settings:**
- **Max retries:** 5 failed login attempts
- **Time window:** 10 minutes (600 seconds)
- **Ban duration:** 1 hour (3600 seconds)
- **Action:** Block all ports from offending IP using iptables

**Monitored Log:** `/var/log/jenkins/jenkins.log`

**Filter Patterns:** Matches failed login attempts, invalid logins, and authentication failures

### Management Commands

```bash
# Check Jenkins jail status
sudo fail2ban-client status jenkins

# View all active jails
sudo fail2ban-client status

# Manually unban an IP address
sudo fail2ban-client set jenkins unbanip <IP_ADDRESS>

# Monitor fail2ban activity in real-time
sudo tail -f /var/log/fail2ban.log

# View currently blocked IPs
sudo iptables -L -n | grep -A 10 f2b-jenkins

# Restart fail2ban service
sudo systemctl restart fail2ban

# Check fail2ban service status
sudo systemctl status fail2ban
```

### Adjusting Settings

To modify ban duration, max retries, or time window:

1. Edit the jail configuration:
   ```bash
   sudo nano /etc/fail2ban/jail.d/jenkins.conf
   ```

2. Modify the values:
   ```ini
   [jenkins]
   maxretry = 5      # Number of failures before ban
   findtime = 600    # Time window in seconds
   bantime = 3600    # Ban duration in seconds
   ```

3. Restart fail2ban:
   ```bash
   sudo systemctl restart fail2ban
   ```

### Common Adjustments

**Permanent ban for persistent attackers:**
```ini
bantime = -1  # Never unban
```

**Stricter protection:**
```ini
maxretry = 3      # Ban after 3 attempts
bantime = 86400   # Ban for 24 hours
```

**More lenient for legitimate users:**
```ini
maxretry = 10     # Allow 10 attempts
findtime = 1800   # Within 30 minutes
bantime = 600     # Ban for 10 minutes only
```

## Monitoring Alerts

Current alert is coming from Jenkins itself. After fail2ban is installed:
- Failed login attempts will trigger IP bans automatically
- Banned IPs are logged in `/var/log/fail2ban.log`
- You can monitor trends to identify persistent attackers

### Recommended Monitoring

1. **Check banned IPs weekly:**
   ```bash
   sudo fail2ban-client status jenkins
   ```

2. **Review fail2ban logs:**
   ```bash
   sudo grep "Ban" /var/log/fail2ban.log | tail -20
   ```

3. **Set up email notifications** (optional):
   Edit `/etc/fail2ban/jail.d/jenkins.conf`:
   ```ini
   [jenkins]
   destemail = your-email@example.com
   sender = fail2ban@your-server.com
   action = %(action_mwl)s
   ```

## Additional Security Recommendations

### 1. Change Jenkins Default Port
Edit `docker-compose.prod.yml` to use non-standard port:
```yaml
jenkins:
  ports:
    - "8888:8080"  # Use 8888 instead of 8080
```

### 2. Restrict Access by IP (if applicable)
If Jenkins is only accessed from specific IPs, use firewall rules:
```bash
# Allow only specific IPs
sudo ufw allow from 203.0.113.10 to any port 8080
sudo ufw deny 8080
```

### 3. Enable Two-Factor Authentication
In Jenkins:
1. Install "Google Login Plugin" or "OWASP Dependency-Check Plugin"
2. Configure 2FA for admin accounts
3. Require 2FA for all users

### 4. Regular Security Updates
```bash
# Update Jenkins container regularly
docker pull jenkins/jenkins:lts
docker-compose -f docker-compose.prod.yml up -d jenkins
```

## Troubleshooting

### fail2ban not blocking IPs

1. **Check if jail is active:**
   ```bash
   sudo fail2ban-client status jenkins
   ```

2. **Verify log path is correct:**
   ```bash
   ls -la /var/log/jenkins/jenkins.log
   ```

3. **Test the filter manually:**
   ```bash
   sudo fail2ban-regex /var/log/jenkins/jenkins.log /etc/fail2ban/filter.d/jenkins.conf
   ```

### Jenkins log location differs

If Jenkins logs are elsewhere, update the jail configuration:
```bash
sudo nano /etc/fail2ban/jail.d/jenkins.conf
# Change logpath to actual location
```

### Accidentally banned yourself

```bash
# Unban your IP immediately
sudo fail2ban-client set jenkins unbanip YOUR_IP_ADDRESS

# Or whitelist your IP permanently
sudo nano /etc/fail2ban/jail.d/jenkins.conf
# Add: ignoreip = 127.0.0.1 YOUR_IP_ADDRESS
```

## Current Alert Analysis

The alert you received shows:
- **15 failed login attempts** from suspicious IPs
- This is typical brute-force scanning behavior
- Once fail2ban is active, these IPs will be automatically banned after 5 attempts

After setup, you should see:
- Fewer alerts (most attackers banned before 15 attempts)
- Banned IPs in fail2ban logs
- Reduced load on Jenkins from repeated failed attempts

## References

- [fail2ban Documentation](https://github.com/fail2ban/fail2ban)
- [Jenkins Security Best Practices](https://www.jenkins.io/doc/book/security/)
- [OWASP Authentication Guidelines](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
