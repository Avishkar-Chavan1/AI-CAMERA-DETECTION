# Render Deployment Guide

## Prerequisites

1. **Render Account** - Sign up at https://render.com
2. **GitHub Repository** - Already configured ✅
3. **Docker** - Already installed locally

## Architecture

- **Render Web Service** - Runs your FastAPI API
- **GitHub Integration** - Auto-deploy on push to main
- **Persistent Disk** (optional) - For event logs and model files

## Step 1: Prepare Repository

### 1.1 Add render.yaml to Repository
✅ Already done! The `render.yaml` file is configured.

## Step 2: Deploy on Render

### 2.1 Connect GitHub to Render

1. Go to https://dashboard.render.com
2. Click **New +** → **Web Service**
3. Select **Deploy an existing repository**
4. Connect your GitHub account
5. Select repository: `Avishkar-Chavan1/AI-CAMERA-DETECTION`
6. Click **Connect**

### 2.2 Configure Web Service

**Basic Settings:**
- **Name**: `plantsync-api`
- **Environment**: `Docker`
- **Build Command**: (leave blank - uses Dockerfile)
- **Start Command**: (leave blank - uses Dockerfile CMD)
- **Instance Type**: `Standard` ($7/month) or `Pro` ($12/month)
- **Auto-Deploy**: Enable
- **Custom Domain**: `api.plantsync.in`

**Environment Variables:**

Add these manually in the Render dashboard under **Environment**:

```
APP_ENV=production
LOG_JSON=true
LOG_LEVEL=INFO
API_AUTH_ENABLED=true
PORT=8000
API_BASE_URL=https://api.plantsync.in
API_CORS_ORIGINS=["https://plantsync.in","https://www.plantsync.in","https://dashboard.plantsync.in"]
API_MAX_IMAGE_BYTES=20000000
API_MAX_VIDEO_BYTES=500000000
API_MAX_VIDEO_FRAMES=10000
API_RATE_LIMIT=30
API_RATE_WINDOW_SECONDS=60
API_INFERENCE_TIMEOUT_SECONDS=300
API_EVENT_LOG_PATH=/var/data/events.db
```

**Store securely in Render Secrets:**
```
API_KEY=<generate-strong-random-key>
```

### 2.3 Deploy

1. Click **Create Web Service**
2. Render will:
   - Build the Docker image
   - Start the container
   - Run health checks
   - Make it live at `https://industrial-safety-api.onrender.com`

**Deployment typically takes 3-5 minutes**

## Step 3: Deploy Dashboard (Optional)

For Streamlit dashboard on Render:

1. Create new **Web Service**
2. Use `docker/Dockerfile.dashboard`
3. Set environment variable:
   - `API_BASE_URL=https://api.plantsync.in`
4. Set **Custom Domain**: `dashboard.plantsync.in`
5. Dashboard will be at `https://dashboard.plantsync.in`

## Step 4: Monitor Deployment

### 4.1 View Logs
In Render Dashboard → Your Service → **Logs**

### 4.2 Check Health
```powershell
Invoke-WebRequest -Uri "https://api.plantsync.in/api/v1/health" `
  -Headers @{"X-API-Key" = "your-api-key"}
```

### 4.3 Auto-Deploy
- Push any changes to `main` branch
- Render automatically rebuilds and deploys
- Logs appear in dashboard

## Step 5: Configure Persistent Storage (Optional)

For event logs that persist across deployments:

1. In Render Dashboard → Service Settings → **Disk**
2. Click **Add Persistent Disk**
3. Mount path: `/var/data`
4. Size: 1 GB ($10/month)
5. Set environment: `API_EVENT_LOG_PATH=/var/data/events.db`

## Pricing

| Component | Cost |
|-----------|------|
| Web Service (Standard) | $7/month |
| Web Service (Pro) | $12/month |
| Persistent Disk (1GB) | $10/month |
| **Total (with disk)** | **$17-22/month** |

Free tier available but services sleep after 15 minutes of inactivity.

## Troubleshooting

### Build Fails

**Check build logs:**
```
Render Dashboard → Logs → Build logs
```

**Common issues:**
- Missing `best.pt` model file
- Python dependencies not installed
- Dockerfile CMD incorrect

### Health Check Failing

**Solution:**
1. SSH into container:
   - Dashboard → **Console** tab
2. Check if service is running:
   ```
   curl http://localhost:8000/api/v1/health
   ```
3. View application logs for errors

### Container Keeps Restarting

**Increase resources:**
- Dashboard → **Settings** → Instance Type → **Pro**
- Or add Persistent Disk to prevent out-of-memory

### Large File Upload Fails

**Increase limits:**
- Update `API_MAX_VIDEO_BYTES` (currently 500MB)
- Note: Max request timeout is 30 seconds on free tier

## Auto-Deploy Setup

Render automatically deploys when you:
1. Push to `main` branch
2. Changes detected in monitored paths
3. Docker image rebuilt
4. New deployment starts

**Disable auto-deploy:** Dashboard → Settings → Auto Deploy → Disable

## Custom Domain Setup

### For API (`api.plantsync.in`):
1. In Render Dashboard → Settings → **Custom Domain**
2. Add: `api.plantsync.in`
3. Update DNS at your registrar:
   - Type: `CNAME`
   - Name: `api`
   - Value: Render-provided CNAME (from dashboard)
4. SSL: Automatic with Render ✅

### For Dashboard (`dashboard.plantsync.in`):
1. Same process for dashboard service
2. Add: `dashboard.plantsync.in`
3. Update DNS accordingly

## Scaling

**If you need more performance:**
1. Upgrade to **Pro** instance type (+$5/month)
2. Add **Persistent Disk** for caching
3. Consider multiple services (API + Dashboard separate)

## Deployment Checklist

- [ ] GitHub repository connected to Render
- [ ] `render.yaml` committed and pushed
- [ ] Docker image builds successfully locally
- [ ] Environment variables configured
- [ ] API key generated and stored securely
- [ ] Health check passes
- [ ] API endpoints responding
- [ ] Logs accessible for debugging
- [ ] Auto-deploy enabled
- [ ] Custom domain configured (optional)

## Next Steps

1. Deploy API to Render
2. Deploy Dashboard to Render
3. Test end-to-end integration
4. Configure monitoring
5. Setup backup strategy for event logs

## Support

- **Render Docs**: https://render.com/docs
- **Render Status**: https://status.render.com
- **Contact Support**: support@render.com
