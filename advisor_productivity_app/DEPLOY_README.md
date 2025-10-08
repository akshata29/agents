# Advisor Productivity Platform - Deployment Guide

## Azure Deployment

This guide covers deploying the Advisor Productivity Platform to Azure.

### Prerequisites

- Azure CLI installed and configured
- Docker installed
- Azure subscription with appropriate permissions
- GitHub repository (for CI/CD)

### Azure Resources Required

1. **Azure Container Apps** - Backend FastAPI service
2. **Azure Static Web Apps** - Frontend React application
3. **Azure OpenAI** - AI models (GPT-4)
4. **Azure Speech Services** - Speech transcription
5. **Azure Language Service** - Entity extraction and PII detection
6. **Azure Application Insights** - Monitoring and logging
7. **Azure Key Vault** - Secrets management

### Deployment Steps

#### 1. Set Environment Variables

```powershell
# Azure Configuration
$RESOURCE_GROUP = "advisor-productivity-rg"
$LOCATION = "eastus"
$APP_NAME = "advisor-productivity"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION
```

#### 2. Deploy Backend to Azure Container Apps

```powershell
# Build and push Docker image
docker build -t $APP_NAME-backend:latest -f Dockerfile .
az acr login --name myregistry
docker tag $APP_NAME-backend:latest myregistry.azurecr.io/$APP_NAME-backend:latest
docker push myregistry.azurecr.io/$APP_NAME-backend:latest

# Create Container App
az containerapp create `
  --name $APP_NAME-backend `
  --resource-group $RESOURCE_GROUP `
  --image myregistry.azurecr.io/$APP_NAME-backend:latest `
  --target-port 8000 `
  --ingress external `
  --query properties.configuration.ingress.fqdn
```

#### 3. Deploy Frontend to Azure Static Web Apps

```powershell
# Build frontend
cd frontend
npm run build

# Deploy to Static Web Apps
az staticwebapp create `
  --name $APP_NAME-frontend `
  --resource-group $RESOURCE_GROUP `
  --source ./dist `
  --location $LOCATION `
  --branch main `
  --app-location "frontend" `
  --output-location "dist"
```

#### 4. Configure Application Insights

```powershell
# Create Application Insights
az monitor app-insights component create `
  --app $APP_NAME-insights `
  --location $LOCATION `
  --resource-group $RESOURCE_GROUP `
  --application-type web

# Get instrumentation key
$INSTRUMENTATION_KEY = az monitor app-insights component show `
  --app $APP_NAME-insights `
  --resource-group $RESOURCE_GROUP `
  --query instrumentationKey -o tsv
```

#### 5. Configure Key Vault

```powershell
# Create Key Vault
az keyvault create `
  --name $APP_NAME-kv `
  --resource-group $RESOURCE_GROUP `
  --location $LOCATION

# Store secrets
az keyvault secret set --vault-name $APP_NAME-kv --name "AZURE-OPENAI-KEY" --value "your-key"
az keyvault secret set --vault-name $APP_NAME-kv --name "AZURE-SPEECH-KEY" --value "your-key"
az keyvault secret set --vault-name $APP_NAME-kv --name "AZURE-LANGUAGE-KEY" --value "your-key"
```

### Environment Configuration

Create `.env.production` with:

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=${AZURE_OPENAI_KEY}
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# Azure Speech Services
AZURE_SPEECH_KEY=${AZURE_SPEECH_KEY}
AZURE_SPEECH_REGION=eastus

# Azure Language Service
AZURE_LANGUAGE_KEY=${AZURE_LANGUAGE_KEY}
AZURE_LANGUAGE_ENDPOINT=https://your-language.cognitiveservices.azure.com/

# Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING=${INSTRUMENTATION_KEY}

# Backend URL
BACKEND_URL=https://advisor-productivity-backend.azurecontainerapps.io
```

### CI/CD with GitHub Actions

See `.github/workflows/deploy.yml` for automated deployment pipeline.

### Monitoring

- **Application Insights**: Real-time monitoring, performance metrics, error tracking
- **Container App Logs**: `az containerapp logs show --name $APP_NAME-backend --resource-group $RESOURCE_GROUP`
- **Health Checks**: `https://your-backend-url/health`

### Scaling

```powershell
# Scale backend
az containerapp update `
  --name $APP_NAME-backend `
  --resource-group $RESOURCE_GROUP `
  --min-replicas 1 `
  --max-replicas 10
```

### Cost Optimization

- Use **Basic** tier for development
- Use **Standard** tier for production
- Enable auto-scaling to minimize costs
- Set up budget alerts in Azure Cost Management

### Security Best Practices

1. Store all secrets in Azure Key Vault
2. Enable managed identity for Container Apps
3. Use Azure AD authentication for frontend
4. Enable CORS only for known domains
5. Use HTTPS for all communications
6. Regular security scans with Azure Security Center

### Troubleshooting

- Check Application Insights for errors
- Review Container App logs
- Verify environment variables
- Test health check endpoints
- Check network security groups

For more details, see the full documentation in `/docs`.
