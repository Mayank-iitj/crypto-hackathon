# Oracle Always Free Deployment (Recommended)

This is the best fully free option to run the complete Q-Shield stack with Docker Compose.

## Why this target

- Runs full multi-service stack on one VM.
- No forced sleep behavior for always-on workloads.
- Keeps your architecture close to local development.

## Minimum VM shape

- Oracle Cloud Always Free ARM VM
- Ubuntu 22.04 LTS
- At least 2 OCPU and 12 GB RAM allocated (4 OCPU and 24 GB preferred)
- 80+ GB boot volume

## Network ingress to allow

- 22 (SSH)
- 3000 (Frontend)
- 8000 (API)
- 3001 (Grafana)
- 5601 (Kibana)
- 9090 (Prometheus)

## Deploy

1. Copy repository to VM.
2. Run:

```bash
cd /opt/qshield
chmod +x deployment/oracle-free/deploy.sh
./deployment/oracle-free/deploy.sh
```

3. Edit root .env if needed and re-run deploy script.

## Compose command used

```bash
docker compose -f docker-compose.yml -f deployment/oracle-free/docker-compose.oracle-free.yml up -d --build
```

## Verify

```bash
docker compose ps
curl -s http://localhost:8000/health
```

## Notes

- The Oracle override file reduces memory pressure for Elastic/Kibana on free resources.
- Existing local and production paths remain unchanged.
- For public internet exposure, place Nginx or Caddy in front and terminate TLS on 443.
