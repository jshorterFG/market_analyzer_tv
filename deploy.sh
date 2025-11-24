#!/bin/bash

# Configuration
PROJECT_ID="sp500trading"
SERVICE_NAME="market-analyzer"
REGION="us-central1"
AUTHORIZED_USER="jshorter@fluidgenius.com"

echo "🚀 Deploying Market Analyzer to Google Cloud Run..."

# Build and deploy
gcloud run deploy $SERVICE_NAME \
  --source . \
  --project=$PROJECT_ID \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=300 \
  --max-instances=1 \
  --min-instances=0

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --project=$PROJECT_ID \
  --region=$REGION \
  --format='value(status.url)')

echo ""
echo "✅ Deployment complete!"
echo "📍 Service URL: $SERVICE_URL"
echo ""
echo "🔐 Setting up IAP (Identity-Aware Proxy) for authentication..."
echo "Note: IAP requires manual setup in the GCP Console for Cloud Run."
echo ""
echo "To restrict access to $AUTHORIZED_USER:"
echo "1. Go to: https://console.cloud.google.com/security/iap?project=$PROJECT_ID"
echo "2. Enable IAP for your Cloud Run service"
echo "3. Add $AUTHORIZED_USER as an authorized user"
echo ""
echo "Alternative: Use Cloud Run authentication (simpler):"
echo "Run this command to restrict to authenticated users only:"
echo ""
echo "gcloud run services update $SERVICE_NAME \\"
echo "  --project=$PROJECT_ID \\"
echo "  --region=$REGION \\"
echo "  --no-allow-unauthenticated"
echo ""
echo "Then add IAM policy:"
echo "gcloud run services add-iam-policy-binding $SERVICE_NAME \\"
echo "  --project=$PROJECT_ID \\"
echo "  --region=$REGION \\"
echo "  --member='user:$AUTHORIZED_USER' \\"
echo "  --role='roles/run.invoker'"
