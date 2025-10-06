# Deploy Yahoo Finance MCP Server to Azure Container Apps
# 
# This script deploys the MCP server as a container app in Azure.
# The MCP server URL will be used by the finagent backend.
#
# Usage:
#   .\deploy_mcp.ps1 -ResourceGroup <rg-name> -AcrName <acr-name> -ContainerAppName <app-name> -Environment <env-name>

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,
    
    [Parameter(Mandatory=$true)]
    [string]$AcrName,
    
    [Parameter(Mandatory=$true)]
    [string]$ContainerAppName,
    
    [Parameter(Mandatory=$true)]
    [string]$Environment,
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "eastus",
    
    [Parameter(Mandatory=$false)]
    [string]$McpApiKey = ""
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Yahoo Finance MCP Server Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$ImageName = "yahoo-finance-mcp"
$ImageTag = "latest"
$FullImageName = "$AcrName.azurecr.io/${ImageName}:${ImageTag}"

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Resource Group: $ResourceGroup"
Write-Host "  ACR Name: $AcrName"
Write-Host "  Container App: $ContainerAppName"
Write-Host "  Environment: $Environment"
Write-Host "  Image: $FullImageName"
Write-Host ""

# Step 1: Build and push Docker image
Write-Host "Step 1: Building and pushing Docker image..." -ForegroundColor Green
Write-Host "----------------------------------------" -ForegroundColor Gray

# Navigate to mcp_servers directory
Push-Location -Path "backend\mcp_servers"

try {
    # Build the image
    Write-Host "Building Docker image..." -ForegroundColor Yellow
    docker build -t ${ImageName}:${ImageTag} .
    
    if ($LASTEXITCODE -ne 0) {
        throw "Docker build failed"
    }
    
    # Login to ACR
    Write-Host "Logging in to Azure Container Registry..." -ForegroundColor Yellow
    az acr login --name $AcrName
    
    if ($LASTEXITCODE -ne 0) {
        throw "ACR login failed"
    }
    
    # Tag the image
    Write-Host "Tagging image..." -ForegroundColor Yellow
    docker tag ${ImageName}:${ImageTag} $FullImageName
    
    # Push to ACR
    Write-Host "Pushing image to ACR..." -ForegroundColor Yellow
    docker push $FullImageName
    
    if ($LASTEXITCODE -ne 0) {
        throw "Docker push failed"
    }
    
    Write-Host "✓ Image built and pushed successfully" -ForegroundColor Green
    Write-Host ""
} finally {
    Pop-Location
}

# Step 2: Create Container Apps Environment (if it doesn't exist)
Write-Host "Step 2: Ensuring Container Apps Environment exists..." -ForegroundColor Green
Write-Host "----------------------------------------" -ForegroundColor Gray

$envExists = az containerapp env show `
    --name $Environment `
    --resource-group $ResourceGroup `
    2>$null

if (-not $envExists) {
    Write-Host "Creating Container Apps Environment..." -ForegroundColor Yellow
    az containerapp env create `
        --name $Environment `
        --resource-group $ResourceGroup `
        --location $Location
    
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create Container Apps Environment"
    }
    Write-Host "✓ Environment created" -ForegroundColor Green
} else {
    Write-Host "✓ Environment already exists" -ForegroundColor Green
}
Write-Host ""

# Step 3: Deploy Container App
Write-Host "Step 3: Deploying Container App..." -ForegroundColor Green
Write-Host "----------------------------------------" -ForegroundColor Gray

# Check if container app exists
$appExists = az containerapp show `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    2>$null

$envVars = @()
if ($McpApiKey) {
    $envVars += "MCP_API_KEY=$McpApiKey"
}

if (-not $appExists) {
    # Create new container app
    Write-Host "Creating new Container App..." -ForegroundColor Yellow
    
    $createArgs = @(
        "containerapp", "create",
        "--name", $ContainerAppName,
        "--resource-group", $ResourceGroup,
        "--environment", $Environment,
        "--image", $FullImageName,
        "--target-port", "8000",
        "--ingress", "external",
        "--cpu", "0.5",
        "--memory", "1Gi",
        "--min-replicas", "1",
        "--max-replicas", "3"
    )
    
    if ($envVars.Count -gt 0) {
        $createArgs += "--env-vars"
        $createArgs += $envVars
    }
    
    az @createArgs
    
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create Container App"
    }
} else {
    # Update existing container app
    Write-Host "Updating existing Container App..." -ForegroundColor Yellow
    
    $updateArgs = @(
        "containerapp", "update",
        "--name", $ContainerAppName,
        "--resource-group", $ResourceGroup,
        "--image", $FullImageName
    )
    
    if ($envVars.Count -gt 0) {
        $updateArgs += "--set-env-vars"
        $updateArgs += $envVars
    }
    
    az @updateArgs
    
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to update Container App"
    }
}

Write-Host "✓ Container App deployed successfully" -ForegroundColor Green
Write-Host ""

# Step 4: Get the FQDN
Write-Host "Step 4: Retrieving application URL..." -ForegroundColor Green
Write-Host "----------------------------------------" -ForegroundColor Gray

$fqdn = az containerapp show `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --query "properties.configuration.ingress.fqdn" `
    --output tsv

if ($fqdn) {
    $mcpServerUrl = "https://$fqdn"
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Deployment Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "MCP Server URL: $mcpServerUrl" -ForegroundColor Yellow
    Write-Host "SSE Endpoint:   ${mcpServerUrl}/sse" -ForegroundColor Yellow
    Write-Host "Health Check:   ${mcpServerUrl}/health" -ForegroundColor Yellow
    Write-Host "API Docs:       ${mcpServerUrl}/docs" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Add this to your backend .env file:" -ForegroundColor Cyan
    Write-Host "MCP_SERVER_URL=${mcpServerUrl}" -ForegroundColor White
    if ($McpApiKey) {
        Write-Host "MCP_API_KEY=$McpApiKey" -ForegroundColor White
    }
    Write-Host ""
} else {
    Write-Warning "Could not retrieve FQDN. Check Azure Portal for details."
}

Write-Host "========================================" -ForegroundColor Cyan
