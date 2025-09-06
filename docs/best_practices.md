# SMS Gateway Best Practices

This document outlines best practices for operating and maintaining the SMS Gateway system, including cybersecurity, monitoring, and backup procedures.

## Cybersecurity Best Practices

### Credential Management
- Use Ansible Vault to encrypt sensitive credentials in `vault.yml`.
- Avoid hardcoding usernames, passwords, or API keys in configuration files.
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

For more details on the system setup, refer to the main Ansible playbook (`setup_sms_gateway.yml`) and configuration files.

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
