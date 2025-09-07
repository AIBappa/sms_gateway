# SMS Bridge Consolidator

This software is an SMS Bridge Consolidator that works on a laptop connected to various older mobile devices on the same local Wi-Fi network.

## Project Structure

This project now provides two deployment options:

### 📁 ansible-docker/
Docker-based deployment using `community.docker` Ansible collection
- Simple container orchestration
- Good for development and testing
- See [ansible-docker/README.md](ansible-docker/README.md) for details

### 📁 ansible-k3s/
Kubernetes-based deployment using K3s and `kubernetes.core` Ansible collection
- Production-ready orchestration
- Built-in monitoring and scaling
- See [ansible-k3s/README.md](ansible-k3s/README.md) for details

### 📁 Shared Files
- `vault.yml` - Encrypted secrets (create from `docs/example_vault.yml`)
- `schema.sql` - Database schema
- `sms_server.py` - Main SMS processing application
- `checks/` - Validation modules
- `docs/` - Documentation and examples
- `tests/` - Testing utilities and sample data

## Concept

The idea is that older mobiles act as SMS receivers and the laptop aggregates all received SMSes in a PostgreSQL database. Duplicate SMSes are filtered and only unique SMS numbers are forwarded to the cloud database (example uses Cloudflare D1).

This method can verify mobile numbers that have been written to D1 via IP input. Users can send SMS to older mobile numbers to confirm their mobile numbers after submitting an onboarding application via IP/Ethernet network.

## Quick Start

### Choose Your Deployment Method

**For Development/Testing (Docker):**
```bash
cd ansible-docker
ansible-playbook -i inventory.txt setup_sms_bridge.yml --ask-vault-pass
```

**For Production (K3s):**
```bash
cd ansible-k3s
ansible-playbook -i inventory.txt setup_sms_bridge_k3s.yml --ask-vault-pass
```

## Prerequisites

### Common Requirements
- Linux laptop (tested on Ubuntu/Debian)
- Ansible installed
- Git (for cloning)

### Docker Deployment
- Docker and Docker Compose
- `community.docker` Ansible collection

### K3s Deployment  
- `kubernetes.core` and `community.general` Ansible collections
- Python kubernetes library

## Setup Steps

1. **Create Vault File**: Copy and customize the vault file
   ```bash
   cp docs/example_vault.yml vault.yml
   ansible-vault encrypt vault.yml
   ```

2. **Choose Deployment Method**: Navigate to either `ansible-docker/` or `ansible-k3s/`

3. **Run Setup**: Follow the README in your chosen deployment folder

4. **Verify**: Check that services are running and accessible

## Service Access

Both deployment methods provide access to:
- **SMS Receiver**: http://localhost:8080
- **Grafana Dashboard**: http://localhost:3001
- **Prometheus Metrics**: http://localhost:9090

## Mobile Setup Required

- Install SMS_Bridge app on older Android devices
- May require rooted device or developer mode
- Configure to send SMSes to laptop endpoint

## Planned Updates

- Support for multiple mobile devices
- Enhanced filtering and validation
- Mobile app improvements
- Cloud backend integration enhancements

## Documentation

- [Best Practices](docs/best_practices.md)
- [Functionality Overview](docs/functionality.md)
- [Example Vault Configuration](docs/example_vault.yml)

## Testing

See the `tests/` directory for testing utilities and sample data.

## Migration

To switch between deployment methods:

1. Stop current deployment
2. Navigate to the other deployment folder
3. Run the setup playbook

Both methods use the same data directories and configuration. 
