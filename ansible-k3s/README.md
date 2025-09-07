# SMS Bridge K3s Deployment

This folder contains Ansible playbooks for deploying the SMS Bridge infrastructure using K3s (lightweight Kubernetes).

## Files

- `setup_sms_bridge_k3s.yml` - Main K3s deployment playbook
- `restart_sms_bridge_k3s.yml` - Restart all K3s services
- `stop_sms_bridge_k3s.yml` - Stop all K3s services (deletes namespace)
- `uninstall_k3s.yml` - Completely remove K3s and cleanup
- `inventory.txt` - Ansible inventory file

## Shared Files (from parent directory)

The playbooks reference these shared files from the parent directory:
- `../vault.yml` - Encrypted secrets file
- `../schema.sql` - Database schema
- `../sms_server.py` - Main SMS processing application
- `../checks/` - Validation check modules

## Prerequisites

1. **Ansible Collections**: Install required collections
   ```bash
   ansible-galaxy collection install kubernetes.core community.general
   ```

2. **Python Dependencies**: Install Kubernetes Python client
   ```bash
   pip install kubernetes pyyaml
   ```

3. **Vault File**: Ensure `../vault.yml` contains required secrets

## Quick Start

### Deploy SMS Bridge with K3s
```bash
cd ansible-k3s
ansible-playbook -i inventory.txt setup_sms_bridge_k3s.yml --ask-vault-pass
```

### Manage the Deployment
```bash
# Restart all services
ansible-playbook -i inventory.txt restart_sms_bridge_k3s.yml

# Stop all services (keeps K3s running)
ansible-playbook -i inventory.txt stop_sms_bridge_k3s.yml

# Completely remove K3s
ansible-playbook -i inventory.txt uninstall_k3s.yml
```

## Service Access

After deployment, services will be available at:

- **SMS Receiver**: http://localhost:8080
- **Grafana**: http://localhost:3001 (admin/your_grafana_password)
- **Prometheus**: http://localhost:9090

## Kubernetes Management

Once K3s is installed, you can use standard kubectl commands:

```bash
# Set up kubectl alias (added automatically to ~/.bashrc)
alias kubectl='k3s kubectl'

# View all pods
kubectl get pods -n sms-bridge

# View services
kubectl get services -n sms-bridge

# View logs
kubectl logs -f deployment/sms-receiver -n sms-bridge

# Access a pod shell
kubectl exec -it deployment/sms-receiver -n sms-bridge -- /bin/bash

# View resource usage
kubectl top pods -n sms-bridge
```

## Architecture

The K3s deployment creates the following resources:

### Namespace
- `sms-bridge` - Isolated namespace for all SMS Bridge resources

### Storage
- `postgres-pv` - PersistentVolume for PostgreSQL data
- `postgres-pvc` - PersistentVolumeClaim

### Secrets & ConfigMaps
- `sms-bridge-secrets` - All sensitive data (passwords, API keys)
- `postgres-init` - Database initialization scripts
- `prometheus-config` - Prometheus configuration
- `grafana-*` - Grafana datasources and dashboards

### Deployments & Services
- `postgres` + service - PostgreSQL database
- `redis` + service - Redis cache
- `pgbouncer` + service - PostgreSQL connection pooler
- `prometheus` + NodePort service - Metrics collection
- `grafana` + NodePort service - Monitoring dashboard
- `postgres-exporter` + service - PostgreSQL metrics
- `redis-exporter` + service - Redis metrics
- `sms-receiver` + NodePort service - Main SMS processing application

## Benefits of K3s vs Docker

### Advantages
1. **Native orchestration**: Built-in service discovery, load balancing, health checks
2. **Resource management**: CPU/memory limits and requests
3. **Rolling updates**: Zero-downtime deployments
4. **Secret management**: Secure handling of sensitive data
5. **Scaling**: Easy horizontal scaling of services
6. **Monitoring**: Built-in metrics and observability
7. **Production-ready**: Industry-standard container orchestration

### K3s Specific Benefits
1. **Lightweight**: Single binary, minimal resource overhead
2. **Edge-friendly**: Designed for edge and IoT deployments
3. **Easy installation**: No complex setup required
4. **Battery included**: Comes with Traefik, local storage, etc.

## Troubleshooting

### Check K3s Status
```bash
sudo systemctl status k3s
```

### View Cluster Info
```bash
k3s kubectl cluster-info
k3s kubectl get nodes
```

### Debug Pod Issues
```bash
k3s kubectl describe pod <pod-name> -n sms-bridge
k3s kubectl logs <pod-name> -n sms-bridge
```

### Common Issues

1. **Image not found**: If SMS receiver image build fails, rebuild manually:
   ```bash
   cd ~/sms_bridge
   docker build -t sms_receiver_image:latest .
   k3s ctr images import --label io.cri-containerd.image=managed <(docker save sms_receiver_image:latest)
   ```

2. **Permission issues**: Ensure proper file ownership:
   ```bash
   sudo chown -R $USER:$USER ~/sms_bridge
   ```

3. **Port conflicts**: Check if ports are already in use:
   ```bash
   sudo netstat -tulpn | grep -E ':(3001|8080|9090)'
   ```

## Migration from Docker

To migrate from the Docker setup to K3s:

1. Stop Docker containers:
   ```bash
   cd ../ansible-docker
   ansible-playbook -i inventory.txt stop_sms_bridge.yml
   ```

2. Deploy K3s version:
   ```bash
   cd ../ansible-k3s
   ansible-playbook -i inventory.txt setup_sms_bridge_k3s.yml --ask-vault-pass
   ```

The K3s version will reuse the same configuration and data directories.
