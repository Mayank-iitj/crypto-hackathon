# GitHub Actions Secrets Configuration Guide

This document explains the secrets required for the CI/CD pipeline in GitHub Actions.

## Setting Up GitHub Secrets

1. Go to Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add each secret from the table below

## Required Secrets

### Docker Registry (GHCR)

| Secret | Value | Purpose |
|--------|-------|---------|
| `GHCR_TOKEN` | GitHub Personal Access Token (PAT) | Push Docker images to GitHub Container Registry |

**How to create PAT:**
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Click "Generate new token"
3. Select scopes: `write:packages`, `read:packages`, `delete:packages`
4. Copy the token and add as `GHCR_TOKEN` secret

### Database (Staging)

| Secret | Value | Purpose |
|--------|-------|---------|
| `STAGING_DB_HOST` | Database host | Staging database server |
| `STAGING_DB_PASSWORD` | Database password | Staging database credentials |
| `STAGING_DB_USER` | Database user | Staging database user |

### Kubernetes (Staging)

| Secret | Value | Purpose |
|--------|-------|---------|
| `STAGING_KUBECONFIG` | kubeconfig file content | Kubernetes cluster access (staging) |
| `STAGING_REGISTRY_SECRET` | Docker registry secret | Pull images from private registry |

### Kubernetes (Production)

| Secret | Value | Purpose |
|--------|-------|---------|
| `PRODUCTION_KUBECONFIG` | kubeconfig file content | Kubernetes cluster access (production) |
| `PRODUCTION_REGISTRY_SECRET` | Docker registry secret | Pull images from private registry |

### OAuth Providers

| Secret | Value | Purpose |
|--------|-------|---------|
| `GOOGLE_CLIENT_ID_TEST` | Google OAuth Client ID | Testing Google authentication |
| `GOOGLE_CLIENT_SECRET_TEST` | Google OAuth Client Secret | Testing Google authentication |
| `GITHUB_CLIENT_ID_TEST` | GitHub OAuth App Client ID | Testing GitHub authentication |
| `GITHUB_CLIENT_SECRET_TEST` | GitHub OAuth App Client Secret | Testing GitHub authentication |

### Notifications

| Secret | Value | Purpose |
|--------|-------|---------|
| `SLACK_WEBHOOK` | Slack webhook URL | Send CI/CD notifications to Slack |
| `EMAIL_NOTIFICATION_SECRET` | Email service API key | Send test reports via email |

### Security & Scanning

| Secret | Value | Purpose |
|--------|-------|---------|
| `SNYK_TOKEN` | Snyk API token | Vulnerability scanning |
| `SONARQUBE_TOKEN` | SonarQube API token | Code quality analysis |
| `CODECOV_TOKEN` | Codecov API token | Coverage reports |

## Setting Secrets via CLI

```bash
# Using GitHub CLI
gh secret set GHCR_TOKEN --body "YOUR_TOKEN"

# Set multiple secrets
gh secret set STAGING_DB_PASSWORD --body "password"
gh secret set STAGING_KUBECONFIG --body "$(cat ~/.kube/config)"
```

## Using Secrets in Workflows

In `.github/workflows/ci.yml`:

```yaml
steps:
  - name: Login to GHCR
    uses: docker/login-action@v3
    with:
      registry: ghcr.io
      username: ${{ github.actor }}
      password: ${{ secrets.GHCR_TOKEN }}

  - name: Deploy to Staging
    env:
      KUBECONFIG_CONTENT: ${{ secrets.STAGING_KUBECONFIG }}
    run: |
      echo "$KUBECONFIG_CONTENT" > /tmp/kubeconfig
      kubectl --kubeconfig=/tmp/kubeconfig apply -f deployment/
```

## Security Best Practices

1. **Rotate Secrets Regularly** - Change passwords and tokens every 90 days
2. **Use Least Permissions** - Only grant needed access levels
3. **Never Log Secrets** - GitHub Actions masks secrets in logs
4. **Use Environment Secrets** - Limit access to specific environments
5. **Monitor Secret Usage** - Review audit logs for access
6. **Separate Dev/Prod** - Different secrets per environment
7. **Use Short Expiration** - PATs should have 90-day expiration

## Verifying Secrets

```bash
# List all secrets (shows only names, not values)
gh secret list

# Update a secret
gh secret set SECRET_NAME --body "new_value"

# Delete a secret
gh secret delete SECRET_NAME
```

## Troubleshooting

### Secret is masked but still showing in logs

Secrets are masked by GitHub, but ensure you're not echoing them:
```yaml
# ❌ Wrong - will show as ***
- run: echo ${{ secrets.MY_SECRET }}

# ✅ Correct - in environment variable
env:
  MY_SECRET: ${{ secrets.MY_SECRET }}
```

### Permission Denied when accessing secret

1. Verify secret exists: `gh secret list`
2. Check branch protection rules
3. Ensure workflow has access to environment

### Kubeconfig parsing errors

Ensure kubeconfig is properly formatted:
```bash
# Add kubeconfig as single line
cat ~/.kube/config | tr '\n' ' ' | sed 's/  */ /g'
```

## Next Steps

1. Create all required secrets in GitHub
2. Update `.github/workflows/ci.yml` with actual secret names
3. Test workflow by pushing to develop branch
4. Verify Docker images are built and pushed
5. Confirm Slack notifications are working

For more information:
- [GitHub Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [About Deployment Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments)
