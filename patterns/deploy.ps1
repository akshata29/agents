#Requires -Version 7.0
<#
.SYNOPSIS
    Deploy Patterns App to Azure App Service as Docker container
    
.DESCRIPTION
    This script:
    1. Reads environment variables from backend/.env file
    2. Builds Docker image
    3. Pushes image to Azure Container Registry
    4. Deploys to Azure App Service
    5. Configures all environment variables from .env file
    
.PARAMETER ResourceGroup
    Azure Resource Group name
    
.PARAMETER AcrName
    Azure Container Registry name (without .azurecr.io)
    
.PARAMETER AppServicePlanName
    Azure App Service Plan name (will be created if doesn't exist)
    
.PARAMETER WebAppName
    Azure Web App name (optional, defaults to app-patterns-{rg})
    
.PARAMETER Location
    Azure region (default: eastus)
    
.PARAMETER SkipBuild
    Skip Docker build and push (useful for config-only updates)
    
.EXAMPLE
    .\deploy.ps1 -ResourceGroup rg-agent-apps -AcrName myacr -AppServicePlanName plan-agent-apps
    
.EXAMPLE
    .\deploy.ps1 -ResourceGroup rg-agent-apps -AcrName myacr -AppServicePlanName plan-agent-apps -SkipBuild
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,
    
    [Parameter(Mandatory=$true)]
    [string]$AcrName,
    
    [Parameter(Mandatory=$true)]
    [string]$AppServicePlanName,
    
    [Parameter(Mandatory=$false)]
    [string]$WebAppName,
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "eastus",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

# Color output functions
function Write-Info {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

# Function to read .env file and return hashtable
function Read-EnvFile {
    param([string]$EnvFilePath)
    
    if (-not (Test-Path $EnvFilePath)) {
        Write-Warning "Environment file not found: $EnvFilePath"
        return @{}
    }
    
    Write-Info "Reading environment file: $EnvFilePath"
    
    $envVars = @{}
    Get-Content $EnvFilePath | ForEach-Object {
        $line = $_.Trim()
        
        # Skip empty lines and comments
        if ($line -eq "" -or $line.StartsWith("#")) {
            return
        }
        
        # Parse KEY=VALUE
        if ($line -match '^([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            
            # Remove quotes if present
            $value = $value -replace '^["'']|["'']$', ''
            
            $envVars[$key] = $value
        }
    }
    
    Write-Success "Loaded $($envVars.Count) environment variables"
    return $envVars
}

try {
    Write-Info "========================================="
    Write-Info "Patterns App - Azure Deployment"
    Write-Info "========================================="
    Write-Info ""
    Write-Info "Resource Group: $ResourceGroup"
    Write-Info "ACR: $AcrName"
    Write-Info "App Service Plan: $AppServicePlanName"
    Write-Info "Location: $Location"
    Write-Info ""
    
    # Set default Web App name if not provided
    if ([string]::IsNullOrWhiteSpace($WebAppName)) {
        $WebAppName = "app-patterns-$($ResourceGroup.ToLower())"
        Write-Info "Web App Name (auto-generated): $WebAppName"
    }
    
    $ImageName = "patterns-app:latest"
    $EnvFilePath = Join-Path $PSScriptRoot "backend\.env"
    
    # Check if logged into Azure
    Write-Info "Checking Azure login status..."
    $account = az account show 2>$null | ConvertFrom-Json
    if (-not $account) {
        Write-ErrorMsg "Not logged into Azure. Please run 'az login'"
        exit 1
    }
    Write-Success "Logged in as: $($account.user.name)"
    
    # Check if Docker is running
    if (-not $SkipBuild) {
        Write-Info "Checking Docker status..."
        docker ps > $null 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-ErrorMsg "Docker is not running. Please start Docker Desktop"
            exit 1
        }
        Write-Success "Docker is running"
    }
    
    # Read environment variables
    $envVars = Read-EnvFile -EnvFilePath $EnvFilePath
    
    # Create or verify Resource Group
    Write-Info "Checking Resource Group: $ResourceGroup"
    $rgExists = az group show --name $ResourceGroup 2>$null
    if (-not $rgExists) {
        Write-Info "Creating Resource Group: $ResourceGroup"
        az group create --name $ResourceGroup --location $Location
        if ($LASTEXITCODE -ne 0) {
            throw "Resource Group creation failed"
        }
        Write-Success "Resource Group created"
    }
    else {
        Write-Success "Resource Group exists"
    }
    
    # Create or verify ACR
    Write-Info "Checking Azure Container Registry: $AcrName"
    $acrExists = az acr show --name $AcrName --resource-group $ResourceGroup 2>$null
    if (-not $acrExists) {
        Write-Info "Creating Azure Container Registry: $AcrName"
        az acr create --resource-group $ResourceGroup --name $AcrName --sku Basic
        if ($LASTEXITCODE -ne 0) {
            throw "ACR creation failed"
        }
        Write-Success "ACR created"
    }
    else {
        Write-Success "ACR exists"
    }
    
    # Create or verify App Service Plan
    Write-Info "Checking App Service Plan: $AppServicePlanName"
    $planExists = az appservice plan show --name $AppServicePlanName --resource-group $ResourceGroup 2>$null
    if (-not $planExists) {
        Write-Info "Creating App Service Plan: $AppServicePlanName (Linux, B2)"
        az appservice plan create `
            --name $AppServicePlanName `
            --resource-group $ResourceGroup `
            --location $Location `
            --is-linux `
            --sku B2
        
        if ($LASTEXITCODE -ne 0) {
            throw "App Service Plan creation failed"
        }
        Write-Success "App Service Plan created"
    }
    else {
        Write-Success "App Service Plan exists"
    }
    
    if (-not $SkipBuild) {
        # Build Docker image
        Write-Info "Building Docker image: $ImageName"
        Write-Info "Build context: Parent directory (includes framework)"
        
        # Change to parent directory to include framework in build context
        $parentDir = Split-Path $PSScriptRoot -Parent
        Push-Location $parentDir
        
        try {
            docker build -t $ImageName -f patterns/Dockerfile .
            if ($LASTEXITCODE -ne 0) {
                throw "Docker build failed"
            }
            Write-Success "Docker image built successfully"
        }
        finally {
            Pop-Location
        }
        
        # Tag and push to ACR
        $acrLoginServer = "$AcrName.azurecr.io"
        $fullImageName = "$acrLoginServer/$ImageName"
        
        Write-Info "Logging into Azure Container Registry..."
        az acr login --name $AcrName
        if ($LASTEXITCODE -ne 0) {
            throw "ACR login failed"
        }
        
        Write-Info "Tagging image: $fullImageName"
        docker tag $ImageName $fullImageName
        
        Write-Info "Pushing image to ACR..."
        docker push $fullImageName
        if ($LASTEXITCODE -ne 0) {
            throw "Docker push failed"
        }
        Write-Success "Image pushed to ACR successfully"
    }
    
    # Check if Web App exists
    Write-Info "Checking if Web App exists: $WebAppName"
    $webAppExists = az webapp show --name $WebAppName --resource-group $ResourceGroup 2>$null
    
    if (-not $webAppExists) {
        # Create Web App
        Write-Info "Creating Web App: $WebAppName"
        az webapp create `
            --resource-group $ResourceGroup `
            --plan $AppServicePlanName `
            --name $WebAppName `
            --deployment-container-image-name "$AcrName.azurecr.io/$ImageName"
        
        if ($LASTEXITCODE -ne 0) {
            throw "Web App creation failed"
        }
        Write-Success "Web App created successfully"
    }
    else {
        Write-Info "Web App already exists, updating configuration"
    }
    
    # Configure ACR credentials
    Write-Info "Configuring ACR credentials..."
    $acrCredentials = az acr credential show --name $AcrName | ConvertFrom-Json
    
    az webapp config container set `
        --name $WebAppName `
        --resource-group $ResourceGroup `
        --docker-custom-image-name "$AcrName.azurecr.io/$ImageName" `
        --docker-registry-server-url "https://$AcrName.azurecr.io" `
        --docker-registry-server-user $acrCredentials.username `
        --docker-registry-server-password $acrCredentials.passwords[0].value
    
    if ($LASTEXITCODE -ne 0) {
        throw "Container configuration failed"
    }
    Write-Success "Container configuration updated"
    
    # Configure environment variables from .env file
    Write-Info "Configuring environment variables from .env file..."
    
    # Build app settings from .env file
    $appSettings = @()
    foreach ($key in $envVars.Keys) {
        # Skip empty values
        if ([string]::IsNullOrWhiteSpace($envVars[$key])) {
            Write-Warning "Skipping empty variable: $key"
            continue
        }
        
        $appSettings += "$key=$($envVars[$key])"
    }
    
    # Add container-specific settings
    $appSettings += "WEBSITES_PORT=8000"
    $appSettings += "WEBSITES_CONTAINER_START_TIME_LIMIT=600"
    $appSettings += "DOCKER_REGISTRY_SERVER_URL=https://$AcrName.azurecr.io"
    $appSettings += "DOCKER_REGISTRY_SERVER_USERNAME=$($acrCredentials.username)"
    $appSettings += "DOCKER_REGISTRY_SERVER_PASSWORD=$($acrCredentials.passwords[0].value)"
    
    # Update CORS origins to include the web app URL
    $webAppUrl = "https://$WebAppName.azurewebsites.net"
    $corsKey = if ($envVars.ContainsKey("CORS_ORIGINS")) { "CORS_ORIGINS" } else { $null }
    
    if ($corsKey) {
        $existingCors = $envVars[$corsKey]
        if ($existingCors -notmatch $webAppUrl) {
            $newCors = "$existingCors,$webAppUrl"
            $appSettings = $appSettings | Where-Object { $_ -notmatch "^CORS_ORIGINS=" }
            $appSettings += "CORS_ORIGINS=$newCors"
        }
    }
    
    # Apply settings in batches to avoid command line length limits
    $batchSize = 20
    $totalBatches = [Math]::Ceiling($appSettings.Count / $batchSize)
    
    for ($i = 0; $i -lt $totalBatches; $i++) {
        $start = $i * $batchSize
        $end = [Math]::Min($start + $batchSize, $appSettings.Count)
        $batch = $appSettings[$start..($end-1)]
        
        Write-Info "Applying settings batch $($i+1) of $totalBatches ($($batch.Count) settings)"
        
        az webapp config appsettings set `
            --name $WebAppName `
            --resource-group $ResourceGroup `
            --settings $batch
        
        if ($LASTEXITCODE -ne 0) {
            throw "App settings update failed for batch $($i+1)"
        }
    }
    
    Write-Success "Environment variables configured ($($appSettings.Count) settings)"
    
    # Enable logging
    Write-Info "Enabling application logging..."
    az webapp log config `
        --name $WebAppName `
        --resource-group $ResourceGroup `
        --application-logging filesystem `
        --level information
    
    # Restart the web app
    Write-Info "Restarting Web App..."
    az webapp restart --name $WebAppName --resource-group $ResourceGroup
    
    if ($LASTEXITCODE -ne 0) {
        throw "Web App restart failed"
    }
    
    Write-Info ""
    Write-Success "========================================="
    Write-Success "🎉 Deployment Complete! 🎉"
    Write-Success "========================================="
    Write-Info ""
    Write-Success "Application URL: https://$WebAppName.azurewebsites.net"
    Write-Info ""
    Write-Info "To view logs:"
    Write-Info "  az webapp log tail --name $WebAppName --resource-group $ResourceGroup"
    Write-Info ""
    Write-Info "To check health:"
    Write-Info "  curl https://$WebAppName.azurewebsites.net/health"
    Write-Info ""
}
catch {
    Write-ErrorMsg "Deployment failed: $_"
    Write-ErrorMsg $_.ScriptStackTrace
    exit 1
}