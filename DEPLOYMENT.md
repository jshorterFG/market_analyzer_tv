# Market Analyzer - Deployment Guide

## Quick Deploy to Google Cloud Run

### Prerequisites
- Google Cloud SDK installed (`gcloud`)
- Authenticated with your GCP account
- Project: `sp500trading`

### Deploy

```bash
./deploy.sh
```

This will:
1. Build a Docker container from your code
2. Deploy to Cloud Run in `us-central1`
3. Provide instructions for setting up authentication

### Restrict Access to Your Email

After deployment, run these commands to restrict access to only `jshorter@fluidgenius.com`:

```bash
# 1. Disable public access
gcloud run services update market-analyzer \
  --project=sp500trading \
  --region=us-central1 \
  --no-allow-unauthenticated

# 2. Grant access to your email
gcloud run services add-iam-policy-binding market-analyzer \
  --project=sp500trading \
  --region=us-central1 \
  --member='user:jshorter@fluidgenius.com' \
  --role='roles/run.invoker'
```

### Access Your App

After authentication is set up, you'll need to:
1. Visit the Cloud Run URL
2. Sign in with your Google account (jshorter@fluidgenius.com)
3. The app will verify your identity before allowing access

### Update/Redeploy

To update the app after making changes:
```bash
./deploy.sh
```

### Environment Variables

The app uses Application Default Credentials for Vertex AI, which are automatically available in Cloud Run when deployed to the same project.

### Costs

- Cloud Run: Pay per use (free tier available)
- Vertex AI API: Pay per request
- Estimated: ~$5-20/month depending on usage

### Troubleshooting

**If deployment fails:**
```bash
# Check Cloud Run logs
gcloud run services logs read market-analyzer \
  --project=sp500trading \
  --region=us-central1
```

**If authentication doesn't work:**
- Verify you're signed in with jshorter@fluidgenius.com
- Check IAM permissions in GCP Console
- Ensure the service is set to require authentication

**If you see "Permission artifactregistry.repositories.uploadArtifacts denied":**
This often happens when the Compute Engine default service account is missing permissions.
Run this command to fix it:
```bash
gcloud projects add-iam-policy-binding sp500trading \
  --member="serviceAccount:$(gcloud projects describe sp500trading --format='value(projectNumber)')-compute@developer.gserviceaccount.com" \
  --role="roles/artifactregistry.admin"
```
