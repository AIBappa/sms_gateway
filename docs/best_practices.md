# SMS Bridge Best Practices

This document outlines best practices for operating and maintaining the SMS Bridge system, including cybersecurity, monitoring, and backup procedures.

## Cybersecurity Best Practices

### Credential Management
- Use Ansible Vault to encrypt sensitive credentials in `vault.yml`.
- Avoid hardcoding usernames, password#### Maintenance Operations
```bash
# === Secure Ansible-based Maintenance ===
# Navigate to project directory
cd /home/<user>/Documents/Software/SMS_Laptop_Setup/sms_gateway

# Restart system after configuration changes
ansible-playbook restart_sms_gateway.yml --ask-vault-passI keys in configuration files.
- Regularly rotate credentials and update the vault file.

### Database Security
- Implement custom database usernames instead of default users to reduce unauthorized access risks.
- Ensure proper privileges are granted to database users (e.g., sms_user) on required tables.
- Use PgBouncer for connection pooling to enhance security and performance.
- Disable or secure the default PostgreSQL user to prevent exploitation.

### General Security
- Run containers with minimal privileges and use Docker's security features.
- Implement network segmentation using Docker networks.
- Regularly update Docker images and dependencies to patch vulnerabilities.
- Monitor for suspicious activities using logs and alerts.

## Monitoring Best Practices

### Prometheus and Grafana Setup
- Use Prometheus to collect metrics from services like PostgreSQL, Redis, and the SMS receiver.
- Configure exporters (e.g., postgres_exporter, redis_exporter) for detailed monitoring.
- Set up Grafana dashboards for visualizing metrics, such as database performance, cache hits, and SMS processing rates.
- Define alerts in Prometheus for critical events, like high error rates or resource exhaustion.

#### Monitoring PostgreSQL with Prometheus and Grafana
- **Install postgres_exporter**: Deploy the postgres_exporter container to expose PostgreSQL metrics. Configure it with database credentials from Ansible Vault.
- **Prometheus Configuration**: Add a scrape job in prometheus.yml to target the postgres_exporter endpoint (e.g., `http://postgres_exporter:9187/metrics`).
- **Grafana Dashboards**: Import pre-built PostgreSQL dashboards (e.g., ID 9628) or create custom ones to visualize metrics like:
  - Active connections and connection pools.
  - Query execution time and slow queries.
  - Database size, table sizes, and index usage.
  - Transaction rates and lock waits.
- **Alerts in Prometheus**: Set up rules for alerts such as:
  - High number of active connections (e.g., >80% of max_connections).
  - Replication lag exceeding thresholds.
  - Increased error rates in queries.
  - Low disk space on database volumes.
- **Integration with PgBouncer**: Monitor connection pooling metrics to ensure efficient resource usage and detect bottlenecks.

#### Automated Grafana Setup (New in Setup Script)
The Ansible playbook now includes automated Grafana configuration:
- **Automatic Data Source**: Prometheus is automatically configured as the default data source.
- **Pre-built Dashboard**: A PostgreSQL monitoring dashboard is automatically imported showing database connections and size.
- **Access**: Open `http://localhost:3001`, log in with `admin` and your `grafana_admin_password` from vault.
- **Ready to Use**: No manual configuration needed - dashboards and data source are pre-configured.
- **Customization**: You can still import additional dashboards (like ID 9628) or create custom ones through the UI.

#### Deployment Status ✅
- **All Services Running**: PostgreSQL, Redis, Prometheus, Grafana, PgBouncer, and exporters are operational.
- **Health Checks**: SMS receiver health endpoint responds correctly at `http://localhost:8080/health`.
- **Metrics Available**: Both PostgreSQL (port 9187) and Redis (port 9121) exporters are providing metrics.
- **Grafana Ready**: Dashboard accessible at `http://localhost:3001` with automated configuration.
- **Database Schema**: All tables created successfully with `IF NOT EXISTS` protection against duplicates.

### Health Checks and Logging
- Implement health endpoints in services (e.g., /health in the SMS receiver) for automated monitoring.
- Use rotating log handlers in Python applications to manage log files efficiently.
- Mount host volumes for persistent logging to ensure logs are retained across container restarts.
- Monitor system health regularly to validate end-to-end SMS processing workflows.

### Key Metrics to Monitor
- Database connection pools and query performance.
- Redis cache hit/miss ratios and memory usage.
- SMS receiver throughput, error rates, and latency.
- Container resource usage (CPU, memory, disk).

### Useful Docker Commands for Monitoring
- Check running containers: `docker ps`
- View container logs: `docker logs <container_name>`
- Monitor real-time resource usage: `docker stats`
- Inspect container details: `docker inspect <container_name>`
- Access container shell for debugging: `docker exec -it <container_name> /bin/bash`

## Backup Best Practices

### PostgreSQL Backups
- Use `pg_dump` for logical backups of the database schema and data.
- Schedule regular backups (e.g., daily) and store them securely off-site or in cloud storage.
- Test backup restoration procedures periodically to ensure data integrity.
- Consider point-in-time recovery (PITR) for critical data.

### Redis Backups
- Enable RDB snapshots for automatic backups of Redis data.
- Configure snapshot intervals based on data volatility (e.g., every 15 minutes).
- Store backups in persistent volumes or external storage.
- Use `redis-cli` commands for manual backups if needed.

### General Backup Guidelines
- Automate backups using cron jobs or Ansible playbooks.
- Encrypt backups to protect sensitive data.
- Document backup and restoration processes in runbooks.
- Monitor backup success and alert on failures.

### Useful Docker Commands for Backup
- Backup PostgreSQL database: `docker exec <postgres_container> pg_dump -U <username> -h localhost <database> > backup.sql`
- Backup Redis data: `docker exec <redis_container> redis-cli save`
- Backup a Docker volume: `docker run --rm -v <volume_name>:/data -v $(pwd):/backup alpine tar czf /backup/backup.tar.gz -C /data .`
- Restore PostgreSQL from backup: `docker exec -i <postgres_container> psql -U <username> -d <database> < backup.sql`
- Restore Redis from RDB file: Copy the RDB file to the Redis container and restart.

## Additional Recommendations

- Regularly review and update Ansible playbooks for infrastructure changes.
- Perform security audits and penetration testing on the system.
- Document incident response procedures for handling breaches or failures.
- Ensure high availability by considering load balancers and failover mechanisms for production deployments.

For more details on the system setup, refer to the main Ansible playbook (`setup_sms_bridge.yml`) and configuration files.

## Access and Credentials

### Service Ports and Access Links
- **PostgreSQL Database**: Port 5432, access via `localhost:5432` (user: `postgres`, password: `pg_password` from vault).
- **PgBouncer**: Port 6432, access via `localhost:6432` (user: `postgres`, password: `pg_password` from vault).
- **Redis Cache**: Port 6379, access via `localhost:6379` (password: `redis_password` from vault).
- **Prometheus**: Port 9090, access via `http://localhost:9090` (no password).
- **Grafana**: Port 3001, access via `http://localhost:3001` (admin user: `admin`, password: `grafana_admin_password` from vault).
- **Python SMS Receiver**: Port 8080, access via `http://localhost:8080` (API key: `cf_api_key` from vault for external forwarding).
- **Postgres Exporter**: Port 9187, metrics at `http://localhost:9187/metrics`.
- **Redis Exporter**: Port 9121, metrics at `http://localhost:9121/metrics`.

### Retrieving Passwords from Vault
All passwords are encrypted in `vault.yml`. To access:
- Run `ansible-vault view vault.yml` to view decrypted contents in the terminal.
- Alternatively, use `ansible-vault edit vault.yml` to open the file in your default text editor (e.g., vim) for viewing/editing; it will decrypt temporarily and re-encrypt on save.
- Use the vault password you set during creation.
- Key variables: `pg_password`, `redis_password`, `grafana_admin_password`, `cf_api_key`, `cf_backend_url`, `hash_secret_key`.

#### Setting Up Default Text Editor
- **On Linux (Bash)**: Ansible uses the `EDITOR` environment variable. Set it temporarily with `export EDITOR=vim` or permanently by adding `export EDITOR=vim` to `~/.bashrc`. Common editors: `vim`, `nano`, `emacs`, `gedit`.
- **On Windows**: If using WSL, Git Bash, or Cygwin, set `export EDITOR=notepad` or `export EDITOR="C:/Program Files/Notepad++/notepad++.exe"`. Common editors: Notepad, Notepad++, VS Code. Note: Direct Windows Ansible may require adjustments.

## Testing and Validation

### Key Endpoint Tests
Use these curl commands to test all system endpoints and validate functionality:

#### 1. Health Check
```bash
curl -s http://localhost:8080/health
# Expected response: {"status":"healthy"}
```

#### 2. SMS Receiver - Send Test SMS
```bash
curl -X POST http://localhost:8080/sms/receive \
  -H "Content-Type: application/json" \
  -d '{
    "sender_number": "+1234567890",
    "sms_message": "This is a test SMS message from mobile 9876543210",
    "received_timestamp": "2025-09-06T12:00:00Z"
  }'
# Expected response: {"status":"received"}
```

#### 3. Prometheus Metrics
```bash
# Check if Prometheus is collecting metrics
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job, health}'

# Check specific PostgreSQL metrics
curl -s http://localhost:9187/metrics | grep -E "pg_stat_database|pg_up"

# Check Redis metrics
curl -s http://localhost:9121/metrics | grep -E "redis_up|redis_connected_clients"
```

#### 4. Database Connectivity Tests
```bash
# Test PostgreSQL direct connection
docker exec postgres psql -U postgres -d sms_bridge -c "SELECT COUNT(*) FROM input_sms;"

# Test PgBouncer connection
docker exec postgres psql -U postgres -h localhost -p 6432 -d sms_bridge -c "SELECT setting_key, setting_value FROM system_settings LIMIT 5;"
```

#### 5. Redis Connectivity Test
```bash
# Test Redis connection and check SMS numbers cache
# Note: You'll need to get the Redis password from vault manually
echo "Use 'ansible-vault view vault.yml' to get redis_password, then:"
echo "docker exec redis redis-cli -a <redis_password> SMEMBERS out_sms_numbers"
```

#### 6. SMS Processing Workflow Test
```bash
# Send multiple test SMS messages
for i in {1..3}; do
  curl -X POST http://localhost:8080/sms/receive \
    -H "Content-Type: application/json" \
    -d "{
      \"sender_number\": \"+12345678$i$i\",
      \"sms_message\": \"Test message $i with mobile 987654321$i\",
      \"received_timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
    }"
  echo " - SMS $i sent"
  sleep 2
done

# Check if messages were processed
echo "Checking processed messages..."
docker exec postgres psql -U postgres -d sms_bridge -c "SELECT COUNT(*) as total_input FROM input_sms;"
docker exec postgres psql -U postgres -d sms_bridge -c "SELECT COUNT(*) as total_output FROM out_sms;"
docker exec postgres psql -U postgres -d sms_bridge -c "SELECT overall_status, COUNT(*) FROM sms_monitor GROUP BY overall_status;"
```

#### 7. Grafana Dashboard Access
```bash
# Open Grafana in browser (manual step)
echo "Open http://localhost:3001 in your browser"
echo "Login: admin"
echo "Password: Use 'ansible-vault view vault.yml' to get grafana_admin_password"
```

### Validation Checklist
After running the tests above, verify:
- [ ] Health endpoint responds with 200 status
- [ ] SMS messages are accepted and stored in `input_sms` table
- [ ] Validation checks process messages (check `sms_monitor` table)
- [ ] Valid messages appear in `out_sms` table and Redis cache
- [ ] Prometheus scrapes metrics from all exporters
- [ ] Grafana displays PostgreSQL dashboard with live data
- [ ] All containers remain healthy after processing load

### Troubleshooting Commands
```bash
# Check container status
docker ps

# View recent logs for specific services
docker logs sms_receiver --tail=50
docker logs postgres --tail=50
docker logs redis --tail=50
docker logs grafana --tail=50

# Monitor real-time resource usage
docker stats

# Restart specific service using Ansible (secure method)
ansible-playbook restart_sms_bridge.yml --ask-vault-pass

# Check individual container status
docker inspect sms_receiver
docker inspect postgres
```

## Deployment Management

### Starting the SMS Bridge System

#### Using Ansible (Secure Method - Recommended)
```bash
# Navigate to project directory
cd /home/<user>/Documents/Software/SMS_Laptop_Setup/sms_bridge

# Start complete deployment with vault credentials
ansible-playbook setup_sms_bridge.yml --ask-vault-pass

# Start deployment with verbose output for debugging
ansible-playbook setup_sms_bridge.yml --ask-vault-pass -vvv
```

### Stopping the SMS Bridge System

#### Using Ansible (Secure Method)
```bash
# Navigate to project directory
cd /home/<user>/Documents/Software/SMS_Laptop_Setup/sms_bridge

# Stop all SMS Bridge containers
ansible-playbook stop_sms_bridge.yml

# Restart all SMS Bridge containers with vault credentials
ansible-playbook restart_sms_bridge.yml --ask-vault-pass
```

#### Emergency Stop (Direct Docker - Use with Caution)
```bash
# Force stop all SMS Bridge containers
docker stop postgres redis pgbouncer postgres_exporter redis_exporter prometheus grafana sms_receiver

# Force remove all SMS Bridge containers (DESTROYS DATA)
docker rm postgres redis pgbouncer postgres_exporter redis_exporter prometheus grafana sms_receiver
```

### Ansible-based Management Commands

#### Using Pre-created Ansible Playbooks (Secure Method)
The project includes dedicated Ansible playbooks for secure container management:

```bash
# Navigate to project directory
cd /home/<user>/Documents/Software/SMS_Laptop_Setup/sms_bridge

# Stop all SMS Bridge containers securely
ansible-playbook stop_sms_bridge.yml

# Restart all SMS Bridge containers with vault credentials
ansible-playbook restart_sms_bridge.yml --ask-vault-pass
```

#### Features of the Ansible Management Playbooks

**Stop Playbook (`stop_sms_bridge.yml`):**
- Gracefully stops all SMS Bridge containers using Ansible Docker modules
- Shows status of remaining containers for verification
- Provides clear feedback on operation completion
- No credential exposure in commands or logs

**Restart Playbook (`restart_sms_bridge.yml`):**
- Performs complete stop and restart cycle using vault-encrypted credentials
- Includes proper wait times for container lifecycle
- Shows container status after restart
- Tests health endpoint to verify SMS receiver is operational
- All passwords remain encrypted in vault.yml

### Quick Reference Commands

#### Daily Operations
```bash
# === Using Ansible (Secure Method - Recommended) ===
# Navigate to project directory first
cd /home/<user>/Documents/Software/SMS_Laptop_Setup/sms_bridge

# Stop SMS Bridge system
ansible-playbook stop_sms_bridge.yml

# Restart SMS Bridge system with vault credentials
ansible-playbook restart_sms_bridge.yml --ask-vault-pass

# === Direct Docker Commands (Use with Caution) ===
# Check container status
docker ps

# View logs from specific containers
docker logs postgres --tail=20
docker logs sms_receiver --tail=20

# Follow logs in real-time
docker logs -f sms_receiver
```

#### Maintenance Operations
```bash
# === Secure Ansible-based Maintenance ===
# Navigate to project directory
cd /home/<user>/Documents/Software/SMS_Laptop_Setup/sms_bridge

# Restart system after configuration changes
ansible-playbook restart_sms_bridge.yml --ask-vault-pass

# === Direct Docker Maintenance (Use with Caution) ===
# Clean up unused Docker resources
docker system prune -f

# Backup database before maintenance
docker exec postgres pg_dump -U postgres sms_bridge > backup_$(date +%Y%m%d_%H%M%S).sql

# Update individual container images
docker pull postgres:15
docker pull redis:7-alpine
docker pull grafana/grafana
```
