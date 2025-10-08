# Advisor Productivity Platform - Deployment Script
# PowerShell deployment script for Azure

param(
    [Parameter(Mandatory=$false)]
    [string]$Environment = "dev",
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroup = "advisor-productivity-rg",
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "eastus"
)

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Advisor Productivity Deployment" -ForegroundColor Cyan
Write-Host "Environment: $Environment" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

# Check if Azure CLI is installed
if (!(Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Azure CLI is not installed" -ForegroundColor Red
    exit 1
}

# Check if logged in to Azure
$account = az account show 2>$null
if (!$account) {
    Write-Host "Not logged in to Azure. Please run 'az login'" -ForegroundColor Yellow
    az login
}

# Variables
$AppName = "advisor-productivity-$Environment"
$ContainerRegistry = "advisorproductivityacr"
$BackendImage = "$ContainerRegistry.azurecr.io/advisor-productivity-backend:latest"

Write-Host "`n1. Creating Resource Group..." -ForegroundColor Green
az group create --name $ResourceGroup --location $Location

Write-Host "`n2. Creating Container Registry..." -ForegroundColor Green
az acr create `
    --resource-group $ResourceGroup `
    --name $ContainerRegistry `
    --sku Basic `
    --admin-enabled true

Write-Host "`n3. Building and Pushing Docker Image..." -ForegroundColor Green
az acr build `
    --registry $ContainerRegistry `
    --image advisor-productivity-backend:latest `
    --file Dockerfile .

Write-Host "`n4. Creating Container App Environment..." -ForegroundColor Green
az containerapp env create `
    --name $AppName-env `
    --resource-group $ResourceGroup `
    --location $Location

Write-Host "`n5. Creating Application Insights..." -ForegroundColor Green
az monitor app-insights component create `
    --app $AppName-insights `
    --location $Location `
    --resource-group $ResourceGroup `
    --application-type web

$InstrumentationKey = az monitor app-insights component show `
    --app $AppName-insights `
    --resource-group $ResourceGroup `
    --query instrumentationKey -o tsv

Write-Host "`n6. Creating Key Vault..." -ForegroundColor Green
az keyvault create `
    --name "$AppName-kv" `
    --resource-group $ResourceGroup `
    --location $Location

Write-Host "`n7. Deploying Backend Container App..." -ForegroundColor Green
az containerapp create `
    --name $AppName-backend `
    --resource-group $ResourceGroup `
    --environment $AppName-env `
    --image $BackendImage `
    --target-port 8000 `
    --ingress external `
    --min-replicas 1 `
    --max-replicas 5 `
    --cpu 1.0 `
    --memory 2.0Gi `
    --env-vars `
        "APPLICATIONINSIGHTS_CONNECTION_STRING=$InstrumentationKey"

$BackendUrl = az containerapp show `
    --name $AppName-backend `
    --resource-group $ResourceGroup `
    --query properties.configuration.ingress.fqdn -o tsv

Write-Host "`n8. Building Frontend..." -ForegroundColor Green
Set-Location frontend
npm install
$env:VITE_BACKEND_URL = "https://$BackendUrl"
npm run build
Set-Location ..

Write-Host "`n9. Deploying Frontend to Static Web App..." -ForegroundColor Green
az staticwebapp create `
    --name $AppName-frontend `
    --resource-group $ResourceGroup `
    --source ./frontend/dist `
    --location $Location

$FrontendUrl = az staticwebapp show `
    --name $AppName-frontend `
    --resource-group $ResourceGroup `
    --query defaultHostname -o tsv

Write-Host "`n==================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Backend URL: https://$BackendUrl" -ForegroundColor Yellow
Write-Host "Frontend URL: https://$FrontendUrl" -ForegroundColor Yellow
Write-Host "Health Check: https://$BackendUrl/health" -ForegroundColor Yellow
Write-Host "==================================" -ForegroundColor Cyan

Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. Configure secrets in Key Vault" -ForegroundColor White
Write-Host "2. Update environment variables in Container App" -ForegroundColor White
Write-Host "3. Test the deployment" -ForegroundColor White
Write-Host "4. Set up monitoring in Application Insights" -ForegroundColor White
