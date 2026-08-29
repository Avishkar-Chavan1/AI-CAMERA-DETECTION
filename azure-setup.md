# Azure Deployment Guide

## Architecture
- **Azure Container Registry (ACR)** - Store Docker images
- **Azure App Service** - Run the application
- **Azure DevOps Pipelines** - CI/CD automation
- **Application Insights** - Monitoring and logging

## Prerequisites

1. **Azure Account** - Sign up at https://azure.microsoft.com
2. **Azure CLI** - Install from https://learn.microsoft.com/en-us/cli/azure/install-azure-cli
3. **Docker** - Already installed locally

## Step 1: Create Azure Resources

### 1.1 Create Resource Group
```bash
az group create `
  --name rg-industrial-safety `
  --location eastus
```

### 1.2 Create Container Registry
```bash
az acr create `
  --resource-group rg-industrial-safety `
  --name industrialsafetyai `
  --sku Basic
```

Get the login server URL (you'll need this):
```bash
az acr show `
  --resource-group rg-industrial-safety `
  --name industrialsafetyai `
  --query loginServer
```

### 1.3 Create App Service Plan
```bash
az appservice plan create `
  --name plan-industrial-safety `
  --resource-group rg-industrial-safety `
  --sku B2 `
  --is-linux
```

### 1.4 Create Application Insights (Optional but recommended)
```bash
az monitor app-insights component create `
  --app industrial-safety-insights `
  --location eastus `
  --resource-group rg-industrial-safety
```

### 1.5 Create App Service
```bash
az webapp create `
  --resource-group rg-industrial-safety `
  --plan plan-industrial-safety `
  --name industrial-safety-ai `
  --deployment-container-image-name industrialsafetyai.azurecr.io/industrial-safety-ai:latest
```

## Step 2: Configure App Service

### 2.1 Enable Admin Access to ACR
```bash
az acr update `
  --name industrialsafetyai `
  --admin-enabled true
```

Get credentials:
```bash
az acr credential show `
  --name industrialsafetyai `
  --resource-group rg-industrial-safety
```

### 2.2 Configure Container Settings
```bash
az webapp config container set `
  --name industrial-safety-ai `
  --resource-group rg-industrial-safety `
  --docker-custom-image-name industrialsafetyai.azurecr.io/industrial-safety-ai:latest `
  --docker-registry-server-url https://industrialsafetyai.azurecr.io `
  --docker-registry-server-user <USERNAME> `
  --docker-registry-server-password <PASSWORD>
```

### 2.3 Configure Application Settings

```bash
az webapp config appsettings set `
  --name industrial-safety-ai `
  --resource-group rg-industrial-safety `
  --settings `
    APP_ENV=production `
    LOG_JSON=true `
    LOG_LEVEL=INFO `
    API_AUTH_ENABLED=true `
    PORT=8000 `
    WEBSITES_ENABLE_APP_SERVICE_STORAGE=false `
    WEBSITES_PORT=8000
```

**Important**: Set these securely (don't commit to repo):
```bash
az webapp config appsettings set `
  --name industrial-safety-ai `
  --resource-group rg-industrial-safety `
  --settings `
    API_KEY=$(openssl rand -base64 32)
```

## Step 3: Build and Push Docker Image

### 3.1 Login to ACR
```bash
az acr login --name industrialsafetyai
```

### 3.2 Build and Push Image
```powershell
# From repository root
docker build `
  -f docker/Dockerfile.api `
  -t industrialsafetyai.azurecr.io/industrial-safety-ai:latest `
  .

docker push industrialsafetyai.azurecr.io/industrial-safety-ai:latest
```

## Step 4: Deploy Application

### 4.1 Deploy from ACR
```bash
az webapp deployment container config `
  --name industrial-safety-ai `
  --resource-group rg-industrial-safety `
  --enable-cd true
```

### 4.2 Restart App Service
```bash
az webapp restart `
  --name industrial-safety-ai `
  --resource-group rg-industrial-safety
```

### 4.3 Get Application URL
```bash
az webapp show `
  --name industrial-safety-ai `
  --resource-group rg-industrial-safety `
  --query defaultHostName
```

Your API will be available at: `https://<app-name>.azurewebsites.net`

## Step 5: Setup CI/CD Pipeline (Optional)

### 5.1 Create Azure DevOps Project
1. Go to https://dev.azure.com
2. Create a new project
3. Connect your GitHub repository

### 5.2 Create Pipeline
1. In Azure DevOps, go to Pipelines
2. Create new pipeline
3. Select GitHub and your repository
4. Use the `azure-deploy.yml` file from this repository
5. Configure variables:
   - `acrName`: industrialsafetyai
   - `acrUsername`: (from Step 2.1)
   - `acrPassword`: (from Step 2.1)

## Step 6: Monitor Application

### 6.1 View Logs
```bash
az webapp log tail `
  --name industrial-safety-ai `
  --resource-group rg-industrial-safety
```

### 6.2 Check Health
```powershell
# API health check
Invoke-WebRequest `
  -Uri "https://industrial-safety-ai.azurewebsites.net/api/v1/health" `
  -Headers @{"X-API-Key" = "your-api-key"}
```

## Scaling Configuration

### Scale Up (Better Hardware)
```bash
az appservice plan update `
  --name plan-industrial-safety `
  --sku S1 `
  --resource-group rg-industrial-safety
```

### Scale Out (More Instances)
```bash
az appservice plan update `
  --name plan-industrial-safety `
  --number-of-workers 2 `
  --resource-group rg-industrial-safety
```

## Cost Optimization

- **B2 Plan**: ~$50-70/month for small workloads
- **S1 Plan**: ~$75-100/month for production
- **Container Registry**: ~$5/month (Basic tier)
- **Application Insights**: First 5GB free per month

Consider using:
- **Spot Instances** for testing
- **Reserved Instances** for consistent workloads
- **Azure Container Instances** for sporadic inference

## Troubleshooting

### Container Won't Start
```bash
az webapp log config `
  --name industrial-safety-ai `
  --resource-group rg-industrial-safety `
  --docker-container-logging filesystem
```

### Health Check Failing
1. SSH into container:
```bash
az webapp ssh `
  --name industrial-safety-ai `
  --resource-group rg-industrial-safety
```

2. Check logs:
```bash
curl http://localhost:8000/api/v1/health
```

### Insufficient Memory
- Upgrade to S1 or P1 plan (more RAM)
- Reduce `API_MAX_VIDEO_FRAMES` to lower memory usage

## Security Best Practices

1. ✅ Enable API authentication: `API_AUTH_ENABLED=true`
2. ✅ Store `API_KEY` in Azure Key Vault
3. ✅ Use HTTPS only
4. ✅ Enable WAF (Web Application Firewall)
5. ✅ Restrict CORS origins
6. ✅ Enable logs to Application Insights

## Next Steps

1. Deploy dashboard to separate App Service or use Streamlit Cloud
2. Setup Application Insights for monitoring
3. Configure Azure Key Vault for secrets
4. Setup Azure SQL or Cosmos DB for persistent event logging
5. Enable auto-scaling based on CPU/memory metrics
