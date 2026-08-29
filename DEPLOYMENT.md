# Deployment Instructions

## Quick Start Deployment Options

### Option 1: Azure App Service (Recommended for Production)
- **Cost**: $50-100/month
- **Effort**: Moderate
- **Best For**: Production applications with monitoring
- **See**: [azure-setup.md](azure-setup.md)

### Option 2: Azure Container Instances (Quick Testing)
- **Cost**: Pay-per-second (~$0.002/sec)
- **Effort**: Low
- **Best For**: Testing and demos
- **Command**:
```bash
az container create `
  --resource-group rg-industrial-safety `
  --name industrial-safety-ai `
  --image industrialsafetyai.azurecr.io/industrial-safety-ai:latest `
  --port 8000 `
  --cpu 2 `
  --memory 4 `
  --registry-login-server industrialsafetyai.azurecr.io `
  --registry-username <username> `
  --registry-password <password> `
  --environment-variables `
    API_ENV=production `
    LOG_JSON=true
```

### Option 3: Docker Compose (Local Testing)
- **Cost**: Free
- **Effort**: Minimal
- **Best For**: Local development and testing
- **Command**:
```powershell
docker-compose -f docker-compose.yml up
```

### Option 4: Azure Kubernetes Service (High Scale)
- **Cost**: $75+/month
- **Effort**: High
- **Best For**: Large-scale deployments, auto-scaling
- **See**: Azure Kubernetes documentation

## Recommended Path for Production

1. **Setup Azure Resources** (15 min)
   - Create resource group
   - Create container registry
   - Create app service plan
   - Create app service

2. **Build & Push Docker Image** (5 min)
   - Build image locally
   - Push to Azure Container Registry

3. **Configure App Service** (10 min)
   - Set environment variables
   - Configure container settings
   - Enable monitoring

4. **Deploy & Test** (5 min)
   - Deploy container
   - Test API endpoints
   - Monitor logs

**Total Time**: ~35 minutes

## Files Included

- `azure-deploy.yml` - Azure DevOps CI/CD pipeline (optional)
- `azure-setup.md` - Detailed Azure deployment guide
- `docker-compose.yml` - Local testing
- `Dockerfile` - Main API container
- `docker/Dockerfile.dashboard` - Streamlit dashboard

## Environment Variables for Azure

Set these in App Service Configuration:
```
APP_ENV=production
LOG_JSON=true
LOG_LEVEL=INFO
API_AUTH_ENABLED=true
PORT=8000
API_BASE_URL=https://industrial-safety-ai.azurewebsites.net
API_CORS_ORIGINS=["https://industrial-safety-ai.azurewebsites.net"]
WEBSITES_ENABLE_APP_SERVICE_STORAGE=false
WEBSITES_PORT=8000
```

Store these securely (Azure Key Vault):
```
API_KEY=<generate-strong-random-key>
```

## Monitoring

### Application Insights Queries

**Error Rate**:
```kusto
requests
| where toint(resultCode) >= 400
| summarize FailureRate = round(100.0 * (todouble(sum(itemCount)) / todouble(sum(itemCount))), 1) by name
```

**Inference Performance**:
```kusto
customMetrics
| where name == "inference_seconds"
| summarize Avg = avg(value), Max = max(value), Min = min(value)
```

## Rollback Procedure

```bash
# Revert to previous image
az webapp config container set `
  --name industrial-safety-ai `
  --resource-group rg-industrial-safety `
  --docker-custom-image-name industrialsafetyai.azurecr.io/industrial-safety-ai:previous-tag
```

## Support & Troubleshooting

See [azure-setup.md](azure-setup.md) Troubleshooting section for common issues.
