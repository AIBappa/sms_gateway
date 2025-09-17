Cloudflare Tunnel for SMS Bridge

This folder contains a minimal, non-invasive setup to run a Cloudflare Tunnel (using `cloudflared`) to expose an internal SMS Bridge backend (either local Docker or a K3s service) to the internet securely.

## Bidirectional Communication Flow

This setup enables two-way communication between your local K3s instance and the Cloudflare Hono backend:

1.  **Inbound Traffic (CF Hono Backend -> Local K3s):**
    *   The Cloudflare Tunnel securely exposes your local `sms_receiver` service to the internet.
    *   Your Cloudflare Worker at `https://validation.new-username.workers.dev/` can send requests to the public tunnel hostname (e.g., `https://sms.example.com`).
    *   **Use Case 1 (Onboarding - GET Hash):** The Hono backend sends a `GET` request to `https://sms.example.com/onboard/register?mobile_number=...` to retrieve a hash for a new mobile number. The tunnel forwards this to your local `sms_server`. This is exactly how the local test app works, but over the internet.
    *   **Use Case 2 (Receiving SMS - POST Data):** After a user is onboarded, the backend can `POST` SMS data to `https://sms.example.com/sms/receive`.
    *   `cloudflared` receives this traffic and forwards it to the internal K3s service (`http://sms-receiver.sms-bridge.svc.cluster.local:8080`).

2.  **Outbound Traffic (Local K3s -> CF Hono Backend):**
    *   The `sms_server.py` application can make direct outbound HTTP requests to `https://validation.new-username.workers.dev/sms-gateway`.
    *   This does **not** go through the tunnel. It is a standard egress connection from your K3s cluster to the public internet.
    *   This is used for sending validated SMS data or status updates from your local instance back to the Cloudflare backend.
    *   The `cf_backend_url` in your `vault.yml` should be set to this URL.

In summary:
- **Inbound**: Cloudflare Worker -> Tunnel -> Local K3s
- **Outbound**: Local K3s -> Direct HTTP -> Cloudflare Worker

Files included
- `docker-compose.yml` - example to run `cloudflared` as a container and mount tunnel credentials
- `config.yml` - example Cloudflared ingress rules mapping hostname to internal backend
- `run_tunnel.sh` - helper script to start/stop the tunnel using docker-compose
- `k3s-secrets.md` - notes for uploading credentials to K3s as a secret and running cloudflared as a pod

Important: This directory is standalone and will not change the existing repository code. It documents the steps you should follow and sample files to run a Cloudflare Tunnel for the SMS Bridge backend.

Prerequisites
- A Cloudflare account with a zone (domain) you control
- `cloudflared` or Docker installed (for container mode)
- Access to the zone API token or Cloudflare Teams to create a tunnel
- (Optional) `kubectl` access for K3s deployments

Quick Example: Expose local Docker backend at http://localhost:8080 to https://sms.example.com
1. Create a tunnel name and credentials using cloudflared (see below)
2. Place `credentials-file.json` into this directory (or mount it via docker-compose)
3. Update `config.yml` with your hostname (sms.example.com) and backend http://host.docker.internal:8080
4. Start the tunnel: `./run_tunnel.sh up`
5. Add a CNAME in Cloudflare DNS or use `cloudflared` to create the DNS record

Security notes
- Keep `credentials-file.json` private (do not commit)
- Use Cloudflare Access policies if you need authentication in front of the tunnel
- Use short-lived or scoped API tokens when possible

See other files for detailed instructions and examples.