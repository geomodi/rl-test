# Railway Deployment Guide

## 🚀 Quick Deploy Checklist

### Pre-Deployment
- [ ] Environment variables ready (CLAUDE_API_KEY, AIRTABLE_API_KEY)
- [ ] Code pushed to GitHub
- [ ] All files committed (especially railway.json, Procfile)

### Railway Setup
1. **Connect Repository**
   - Go to [Railway Dashboard](https://railway.app/dashboard)
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository

2. **Configure Environment Variables**
   ```
   CLAUDE_API_KEY=your_claude_api_key_here
   AIRTABLE_API_KEY=your_airtable_api_key_here
   ```

3. **Deploy**
   - Railway will automatically detect Python and use our configuration
   - Monitor the build logs for any issues

## 🏥 Health Check Endpoints

Railway will use these to monitor your app:

- **`/healthz`** - Simple health check (Railway uses this)
- **`/health`** - Detailed health check with component status

## 🔧 Configuration Files

### `Dockerfile`
- Uses Python 3.12 slim image
- Installs dependencies efficiently
- Built-in health check
- Optimized for Railway deployment

### `railway.json`
- Uses DOCKERFILE builder (more reliable than nixpacks)
- Health check on `/health` endpoint
- 300-second timeout for startup
- Restart on failure with 3 max retries

### `Procfile`
- Backup start command: `python server.py`

### Server Configuration
- Uses Railway's `PORT` environment variable
- Binds to `0.0.0.0` (required for Railway)
- Graceful error handling for missing env vars

## 🐛 Troubleshooting

### Common Issues

1. **Health Check Failures**
   - Check `/healthz` endpoint responds with 200
   - Verify server binds to 0.0.0.0, not 127.0.0.1
   - Ensure PORT environment variable is used

2. **Environment Variables**
   - Missing API keys will show in `/health` endpoint
   - App won't crash but will report unhealthy status

3. **Build Failures**
   - Check requirements.txt is valid
   - Verify Python version compatibility
   - Review Railway build logs

### Testing Locally

Run the test script:
```bash
python test_startup.py
```

This will:
- Start the server on port 8001
- Test both health endpoints
- Report any issues

## 📊 Monitoring

After deployment:

1. **Check Health Status**
   - Visit `https://your-app.railway.app/healthz`
   - Should return `{"status": "ok", "timestamp": "..."}`

2. **Detailed Status**
   - Visit `https://your-app.railway.app/health`
   - Shows component status (environment, filesystem, airtable)

3. **Application**
   - Visit `https://your-app.railway.app/`
   - Should load the Attribution Dashboard

## 🔄 Updates

For future updates:
1. Push changes to GitHub
2. Railway auto-deploys from main branch
3. Monitor deployment in Railway dashboard
4. Check health endpoints after deployment

## 🆘 Emergency

If deployment fails:
1. Check Railway logs in dashboard
2. Verify environment variables are set
3. Test health endpoints
4. Roll back to previous deployment if needed
