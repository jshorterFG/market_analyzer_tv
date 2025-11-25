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
echo "🔐 App-level authentication is enabled."
echo "   Password: fluidgenius"
