#!/bin/bash

# Configuration
PROJECT_ID="sp500trading"
SERVICE_NAME="market-analyzer"
REGION="us-central1"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo "🚀 Building and deploying Market Analyzer..."

# Build Docker image locally
echo "📦 Building Docker image..."
docker build -t $IMAGE_NAME .

# Push to Google Container Registry
echo "⬆️  Pushing to Container Registry..."
docker push $IMAGE_NAME

# Deploy to Cloud Run
echo "🌐 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image=$IMAGE_NAME \
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
echo "🔐 Now restricting access to jshorter@fluidgenius.com..."

# Restrict access
gcloud run services update $SERVICE_NAME \
  --project=$PROJECT_ID \
  --region=$REGION \
  --no-allow-unauthenticated

gcloud run services add-iam-policy-binding $SERVICE_NAME \
  --project=$PROJECT_ID \
  --region=$REGION \
  --member='user:jshorter@fluidgenius.com' \
  --role='roles/run.invoker'

echo ""
echo "✅ Access restricted to jshorter@fluidgenius.com"
echo "📍 Access your app at: $SERVICE_URL"
echo "🔐 You'll need to sign in with your Google account"
