# Unified Finagent Dynamic App Deployment Script
# Deploys MCP Server + Backend + Frontend in one automated flow

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,
    
    [Parameter(Mandatory=$true)]
    [string]$AcrName,
    
    [Parameter(Mandatory=$true)]
    [string]$AppServicePlanName,
    
    [Parameter(Mandatory=$true)]
    [string]$WebAppName,
    
    [Parameter(Mandatory=$false)]
    [string]$McpContainerAppName = "yahoo-finance-mcp-fda",
    
    [Parameter(Mandatory=$false)]
    [string]$McpEnvironmentName = "finagent-dynamic-mcp-env",
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "eastus",
    
    [Parameter(Mandatory=$false)]
    [string]$McpApiKey = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipMcpDeployment = $false
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Finagent Dynamic App - Unified Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Change to script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Check if logged into Azure
Write-Host "Checking Azure login status..." -ForegroundColor Yellow
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "Not logged into Azure. Please login..." -ForegroundColor Red
    az login
    $account = az account show | ConvertFrom-Json
}
Write-Host "✓ Logged in as: $($account.user.name)" -ForegroundColor Green
Write-Host "✓ Subscription: $($account.name)" -ForegroundColor Green
Write-Host ""

# Check if resource group exists
Write-Host "Checking resource group..." -ForegroundColor Yellow
$rgExists = az group exists --name $ResourceGroup
if ($rgExists -eq "false") {
    Write-Host "Creating resource group: $ResourceGroup" -ForegroundColor Yellow
    az group create --name $ResourceGroup --location $Location
    Write-Host "✓ Resource group created" -ForegroundColor Green
} else {
    Write-Host "✓ Resource group exists" -ForegroundColor Green
}
Write-Host ""

# Check if ACR exists
Write-Host "Checking Azure Container Registry..." -ForegroundColor Yellow
$acrExists = az acr show --name $AcrName --resource-group $ResourceGroup 2>$null
if (-not $acrExists) {
    Write-Host "Creating Azure Container Registry: $AcrName" -ForegroundColor Yellow
    az acr create --resource-group $ResourceGroup --name $AcrName --sku Basic --location $Location
    Write-Host "✓ ACR created" -ForegroundColor Green
} else {
    Write-Host "✓ ACR exists" -ForegroundColor Green
}
Write-Host ""

# Login to ACR
Write-Host "Logging into ACR..." -ForegroundColor Yellow
az acr login --name $AcrName
Write-Host "✓ Logged into ACR" -ForegroundColor Green
Write-Host ""

# ========================================
# STEP 1: Deploy MCP Server
# ========================================
$mcpServerUrl = ""

if (-not $SkipMcpDeployment) {
    Write-Host "========================================" -ForegroundColor Magenta
    Write-Host "STEP 1: Deploying MCP Server" -ForegroundColor Magenta
    Write-Host "========================================" -ForegroundColor Magenta
    Write-Host ""

    Set-Location "$ScriptDir\backend\mcp_servers"

    # Build MCP Docker image
    Write-Host "Building MCP server Docker image..." -ForegroundColor Yellow
    $McpImageName = "yahoo-finance-mcp"
    $McpImageTag = "latest"
    $FullMcpImageName = "$AcrName.azurecr.io/$McpImageName`:$McpImageTag"

    docker build -t $McpImageName`:$McpImageTag .
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ MCP Docker build failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ MCP image built" -ForegroundColor Green

    # Push MCP image to ACR
    Write-Host "Pushing MCP image to ACR..." -ForegroundColor Yellow
    docker tag $McpImageName`:$McpImageTag $FullMcpImageName
    docker push $FullMcpImageName
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ MCP image push failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ MCP image pushed to ACR" -ForegroundColor Green
    Write-Host ""

    # Check if Container Apps extension is installed
    Write-Host "Checking Azure CLI extensions..." -ForegroundColor Yellow
    $extensions = az extension list | ConvertFrom-Json
    $containerAppExt = $extensions | Where-Object { $_.name -eq "containerapp" }
    if (-not $containerAppExt) {
        Write-Host "Installing containerapp extension..." -ForegroundColor Yellow
        az extension add --name containerapp
    }
    Write-Host "✓ Extensions ready" -ForegroundColor Green
    Write-Host ""

    # Check if Container Apps environment exists
    Write-Host "Checking Container Apps Environment..." -ForegroundColor Yellow
    $envExists = az containerapp env show --name $McpEnvironmentName --resource-group $ResourceGroup 2>$null
    if (-not $envExists) {
        Write-Host "Creating Container Apps Environment: $McpEnvironmentName" -ForegroundColor Yellow
        az containerapp env create `
            --name $McpEnvironmentName `
            --resource-group $ResourceGroup `
            --location $Location
        Write-Host "✓ Container Apps Environment created" -ForegroundColor Green
    } else {
        Write-Host "✓ Container Apps Environment exists" -ForegroundColor Green
    }
    Write-Host ""

    # Enable admin user on ACR for Container Apps
    az acr update --name $AcrName --admin-enabled true
    $acrCreds = az acr credential show --name $AcrName | ConvertFrom-Json
    $acrServer = "$AcrName.azurecr.io"
    $acrUsername = $acrCreds.username
    $acrPassword = $acrCreds.passwords[0].value

    # Check if Container App exists
    Write-Host "Checking MCP Container App..." -ForegroundColor Yellow
    $mcpAppExists = az containerapp show --name $McpContainerAppName --resource-group $ResourceGroup 2>$null
    
    if (-not $mcpAppExists) {
        Write-Host "Creating MCP Container App: $McpContainerAppName" -ForegroundColor Yellow
        
        # Prepare environment variables
        $mcpEnvVars = @()
        if ($McpApiKey) {
            $mcpEnvVars = @("MCP_API_KEY=$McpApiKey")
        }
        
        $createArgs = @(
            "containerapp", "create",
            "--name", $McpContainerAppName,
            "--resource-group", $ResourceGroup,
            "--environment", $McpEnvironmentName,
            "--image", $FullMcpImageName,
            "--target-port", "8000",
            "--ingress", "external",
            "--registry-server", $acrServer,
            "--registry-username", $acrUsername,
            "--registry-password", $acrPassword,
            "--cpu", "0.5",
            "--memory", "1Gi",
            "--min-replicas", "1",
            "--max-replicas", "3"
        )
        
        if ($mcpEnvVars.Count -gt 0) {
            $createArgs += "--env-vars"
            $createArgs += $mcpEnvVars
        }
        
        az @createArgs
        Write-Host "✓ MCP Container App created" -ForegroundColor Green
    } else {
        Write-Host "✓ MCP Container App exists, updating..." -ForegroundColor Yellow
        
        # Update existing container app
        $updateArgs = @(
            "containerapp", "update",
            "--name", $McpContainerAppName,
            "--resource-group", $ResourceGroup,
            "--image", $FullMcpImageName
        )
        
        if ($McpApiKey) {
            $updateArgs += "--set-env-vars"
            $updateArgs += "MCP_API_KEY=$McpApiKey"
        }
        
        az @updateArgs
        Write-Host "✓ MCP Container App updated" -ForegroundColor Green
    }
    Write-Host ""

    # Get MCP Server URL
    Write-Host "Retrieving MCP Server URL..." -ForegroundColor Yellow
    $mcpApp = az containerapp show --name $McpContainerAppName --resource-group $ResourceGroup | ConvertFrom-Json
    $mcpServerUrl = "https://$($mcpApp.properties.configuration.ingress.fqdn)"
    Write-Host "✓ MCP Server URL: $mcpServerUrl" -ForegroundColor Green
    Write-Host ""
    
    # Return to script directory
    Set-Location $ScriptDir

} else {
    Write-Host "Skipping MCP deployment (use existing MCP server)" -ForegroundColor Yellow
    Write-Host ""
}

# ========================================
# STEP 2: Deploy Main Application
# ========================================
Write-Host "========================================" -ForegroundColor Magenta
Write-Host "STEP 2: Deploying Main Application" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Write-Host ""

$BackendImageName = "finagent-dynamic-backend"
$BackendImageTag = "latest"
$FullBackendImageName = "$AcrName.azurecr.io/$BackendImageName`:$BackendImageTag"

# Build from parent directory to include framework folder (like multimodal)
$parentDir = Split-Path $ScriptDir -Parent

# Build Docker image with multi-stage build (includes frontend + backend)
Write-Host "Building Docker image with multi-stage build (frontend + backend)..." -ForegroundColor Yellow
Set-Location $parentDir
docker build -f finagent_dynamic_app/Dockerfile -t $BackendImageName`:$BackendImageTag .
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Docker build failed" -ForegroundColor Red
    exit 1
}
docker tag $BackendImageName`:$BackendImageTag $FullBackendImageName
docker push $FullBackendImageName
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Docker push failed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Final image built and pushed to ACR" -ForegroundColor Green
Write-Host ""

# Return to script directory
Set-Location $ScriptDir

# Check if App Service Plan exists
Write-Host "Checking App Service Plan..." -ForegroundColor Yellow
$planExists = az appservice plan show --name $AppServicePlanName --resource-group $ResourceGroup 2>$null
if (-not $planExists) {
    Write-Host "Creating App Service Plan: $AppServicePlanName" -ForegroundColor Yellow
    az appservice plan create `
        --name $AppServicePlanName `
        --resource-group $ResourceGroup `
        --is-linux `
        --sku B1 `
        --location $Location
    Write-Host "✓ App Service Plan created" -ForegroundColor Green
} else {
    Write-Host "✓ App Service Plan exists" -ForegroundColor Green
}
Write-Host ""

# Enable admin user on ACR
Write-Host "Enabling ACR admin user..." -ForegroundColor Yellow
az acr update --name $AcrName --admin-enabled true
$acrCreds = az acr credential show --name $AcrName | ConvertFrom-Json
$acrUsername = $acrCreds.username
$acrPassword = $acrCreds.passwords[0].value
Write-Host "✓ ACR admin enabled" -ForegroundColor Green
Write-Host ""

# Check if Web App exists
Write-Host "Checking Web App..." -ForegroundColor Yellow
$webAppExists = az webapp show --name $WebAppName --resource-group $ResourceGroup 2>$null
if (-not $webAppExists) {
    Write-Host "Creating Web App: $WebAppName" -ForegroundColor Yellow
    az webapp create `
        --resource-group $ResourceGroup `
        --plan $AppServicePlanName `
        --name $WebAppName `
        --deployment-container-image-name $FullBackendImageName
    Write-Host "✓ Web App created" -ForegroundColor Green
} else {
    Write-Host "✓ Web App exists" -ForegroundColor Green
}
Write-Host ""

# Configure container registry credentials
Write-Host "Configuring container registry credentials..." -ForegroundColor Yellow
az webapp config container set `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --docker-custom-image-name $FullBackendImageName `
    --docker-registry-server-url "https://$AcrName.azurecr.io" `
    --docker-registry-server-user $acrUsername `
    --docker-registry-server-password $acrPassword
Write-Host "✓ Container configured" -ForegroundColor Green
Write-Host ""

# Load environment variables from .env file
Write-Host "Loading environment variables from .env file..." -ForegroundColor Yellow
$envVars = @(
    "PORT=8000"
)

$envFilePath = "$ScriptDir\backend\.env"
if (Test-Path $envFilePath) {
    Write-Host "✓ Found .env file: $envFilePath" -ForegroundColor Green
    
    # Read and parse .env file
    $envLines = Get-Content $envFilePath
    foreach ($line in $envLines) {
        # Skip empty lines and comments
        if ($line -match '^\s*$' -or $line -match '^\s*#') {
            continue
        }
        
        # Parse KEY=VALUE format
        if ($line -match '^([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            
            # Remove quotes if present
            $value = $value -replace '^["'']|["'']$', ''
            
            # Skip PORT (we set it explicitly)
            if ($key -eq "PORT") {
                continue
            }
            
            # Add to envVars array
            $envVars += "$key=$value"
            Write-Host "  • Loaded: $key" -ForegroundColor Gray
        }
    }
    Write-Host "✓ Loaded $($envVars.Count - 1) variables from .env file" -ForegroundColor Green
} else {
    Write-Host "⚠️  No .env file found at $envFilePath" -ForegroundColor Yellow
    Write-Host "   Continuing with minimal configuration..." -ForegroundColor Yellow
}
Write-Host ""

# Add MCP configuration (overrides .env if present)
if ($mcpServerUrl) {
    # Remove existing MCP_SERVER_URL and YAHOO_FINANCE_MCP_URL if loaded from .env
    $envVars = $envVars | Where-Object { $_ -notmatch '^MCP_SERVER_URL=' -and $_ -notmatch '^YAHOO_FINANCE_MCP_URL=' -and $_ -notmatch '^YAHOO_FINANCE_ENABLED=' }
    $envVars += "MCP_SERVER_URL=$mcpServerUrl"
    $envVars += "YAHOO_FINANCE_MCP_URL=$mcpServerUrl"
    $envVars += "YAHOO_FINANCE_ENABLED=true"
    Write-Host "✓ MCP_SERVER_URL configured: $mcpServerUrl" -ForegroundColor Green
    Write-Host "✓ YAHOO_FINANCE_MCP_URL configured: $mcpServerUrl" -ForegroundColor Green
    Write-Host "✓ YAHOO_FINANCE_ENABLED set to true" -ForegroundColor Green
}

if ($McpApiKey) {
    # Remove existing MCP_API_KEY if loaded from .env
    $envVars = $envVars | Where-Object { $_ -notmatch '^MCP_API_KEY=' }
    $envVars += "MCP_API_KEY=$McpApiKey"
    Write-Host "✓ MCP_API_KEY configured from parameter" -ForegroundColor Green
}
Write-Host ""

# Configure environment variables in Azure
Write-Host "Applying environment variables to Azure Web App..." -ForegroundColor Yellow

az webapp config appsettings set `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --settings $envVars

Write-Host "✓ Environment variables configured" -ForegroundColor Green
Write-Host ""

# Enable continuous deployment (webhook)
Write-Host "Enabling continuous deployment..." -ForegroundColor Yellow
az webapp deployment container config `
    --name $WebAppName `
    --resource-group $ResourceGroup `
    --enable-cd true
Write-Host "✓ Continuous deployment enabled" -ForegroundColor Green
Write-Host ""

# Restart web app
Write-Host "Restarting web app..." -ForegroundColor Yellow
az webapp restart --name $WebAppName --resource-group $ResourceGroup
Write-Host "✓ Web app restarted" -ForegroundColor Green
Write-Host ""

# Get Web App URL
$webAppUrl = "https://$WebAppName.azurewebsites.net"

Write-Host "========================================" -ForegroundColor Green
Write-Host "✓ DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "📦 Deployed Components:" -ForegroundColor Cyan
Write-Host "  • MCP Server:      $mcpServerUrl" -ForegroundColor White
Write-Host "  • Web Application: $webAppUrl" -ForegroundColor White
Write-Host ""
Write-Host "🔧 Environment Variables Configured:" -ForegroundColor Cyan
Write-Host "  • YAHOO_FINANCE_MCP_URL: $mcpServerUrl" -ForegroundColor White
Write-Host "  • YAHOO_FINANCE_ENABLED: true" -ForegroundColor White
Write-Host "  • MCP_SERVER_URL: $mcpServerUrl" -ForegroundColor White
Write-Host ""
Write-Host "🔧 Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Configure authentication (Azure AD) in Azure Portal" -ForegroundColor White
Write-Host "  2. Update CORS settings if needed" -ForegroundColor White
Write-Host "  3. Test MCP connection: curl $mcpServerUrl/health" -ForegroundColor White
Write-Host "  4. Monitor logs: az webapp log tail --name $WebAppName --resource-group $ResourceGroup" -ForegroundColor White
Write-Host ""
Write-Host "📊 Resource Group: $ResourceGroup" -ForegroundColor Cyan
Write-Host ""

Set-Location $ScriptDir
