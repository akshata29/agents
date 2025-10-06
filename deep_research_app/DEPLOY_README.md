# Deep Research App - Deployment Guide

## Quick Deploy

### Prerequisites
- Azure CLI installed and logged in (`az login`)
- Docker Desktop running
- `.env` file configured in `backend/.env`

### Deploy to Azure

```powershell
.\deploy.ps1 `
    -ResourceGroup rg-agent-apps `
    -AcrName myagentsacr `
    -AppServicePlanName plan-agent-apps
```

### Update Configuration Only (No Rebuild)

```powershell
.\deploy.ps1 `
    -ResourceGroup rg-agent-apps `
    -AcrName myagentsacr `
    -AppServicePlanName plan-agent-apps `
    -SkipBuild
```

### Custom Web App Name

```powershell
.\deploy.ps1 `
    -ResourceGroup rg-agent-apps `
    -AcrName myagentsacr `
    -AppServicePlanName plan-agent-apps `
    -WebAppName my-custom-app-name
```

## What It Does

1. ✅ Reads all variables from `backend/.env`
2. ✅ Creates Azure resources (Resource Group, ACR, App Service Plan) if they don't exist
3. ✅ Builds Docker image (includes framework folder)
4. ✅ Pushes to Azure Container Registry
5. ✅ Creates/updates Azure Web App
6. ✅ Sets ALL environment variables from .env as App Service settings
7. ✅ Configures container and logging
8. ✅ Restarts the app

## Environment Setup

```powershell
# Copy example and edit
cp backend\.env.example backend\.env

# Edit backend\.env and fill in your Azure credentials:
# - AZURE_OPENAI_ENDPOINT
# - AZURE_OPENAI_API_KEY
# - AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
# - TAVILY_API_KEY (optional)
# etc.
```

## After Deployment

Access your app at:
```
https://app-deep-research-{your-rg}.azurewebsites.net
```

View logs:
```powershell
az webapp log tail --name app-deep-research-{your-rg} --resource-group {your-rg}
```

Check health:
```powershell
curl https://app-deep-research-{your-rg}.azurewebsites.net/health
```

## Notes

- The script builds from the **parent directory** to include the `framework` folder in the Docker context
- Frontend is built as static files and served from the backend
- All `.env` values are automatically synced to Azure App Service settings
