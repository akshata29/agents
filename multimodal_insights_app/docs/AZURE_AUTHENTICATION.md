# Azure Authentication Setup

This document explains how to configure Azure AD authentication for the Multimodal Insights application.

## Overview

The application supports two authentication methods for Azure services:

1. **Azure AD Authentication** (Recommended for production)
2. **Key-based Authentication** (For development only)

## Azure AD Authentication (Recommended)

### Why Use Azure AD?

- ✅ **More Secure**: No keys stored in configuration
- ✅ **Centralized Management**: Control access through Azure AD
- ✅ **Audit Trail**: Track all access through Azure AD logs
- ✅ **Role-Based Access**: Use Azure RBAC for fine-grained permissions
- ✅ **Key Rotation**: No need to update keys in your application

### Prerequisites

1. Azure subscription
2. Azure AD tenant
3. Permissions to create service principals

### Step 1: Create Service Principal

```bash
# Login to Azure
az login

# Create service principal
az ad sp create-for-rbac --name multimodal-insights-app --role Contributor

# Output will look like:
# {
#   "appId": "your-client-id",
#   "displayName": "multimodal-insights-app",
#   "password": "your-client-secret",
#   "tenant": "your-tenant-id"
# }
```

Save these values - you'll need them for configuration.

### Step 2: Assign Cosmos DB Permissions

```bash
# Get your Cosmos DB account resource ID
COSMOS_RESOURCE_ID=$(az cosmosdb show \
  --name your-cosmos-account \
  --resource-group your-resource-group \
  --query id -o tsv)

# Assign Cosmos DB Account Contributor role to service principal
az role assignment create \
  --assignee your-client-id \
  --role "Cosmos DB Account Contributor" \
  --scope $COSMOS_RESOURCE_ID
```

Alternatively, use the Azure Portal:
1. Navigate to your Cosmos DB account
2. Click "Access control (IAM)"
3. Click "Add" → "Add role assignment"
4. Select "Cosmos DB Account Contributor"
5. Search for your service principal name
6. Click "Save"

### Step 3: Configure Environment Variables

Update your `.env` file:

```bash
# Azure CosmosDB
COSMOSDB_ENDPOINT=https://your-cosmos.documents.azure.com:443/
# Don't set COSMOSDB_KEY - we'll use Azure AD instead
COSMOSDB_DATABASE=multimodal_insights
COSMOSDB_CONTAINER=tasks

# Azure AD Service Principal
TENANT_ID=your-tenant-id
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret
```

### Step 4: Assign Additional Azure Service Permissions

If you're using Azure Storage or other services with Azure AD:

```bash
# For Azure Storage
az role assignment create \
  --assignee your-client-id \
  --role "Storage Blob Data Contributor" \
  --scope /subscriptions/{subscription-id}/resourceGroups/{resource-group}/providers/Microsoft.Storage/storageAccounts/{storage-account}
```

### Step 5: Test Connection

```bash
cd backend
.\start.ps1
```

Check the logs for:
```
Using ClientSecretCredential for CosmosDB authentication
Cosmos DB initialized: multimodal_insights/tasks
```

## Key-Based Authentication (Development Only)

For local development, you can use key-based authentication:

### Configuration

```bash
# Azure CosmosDB
COSMOSDB_ENDPOINT=https://your-cosmos.documents.azure.com:443/
COSMOSDB_KEY=your-primary-or-secondary-key
COSMOSDB_DATABASE=multimodal_insights
COSMOSDB_CONTAINER=tasks

# Don't set TENANT_ID, CLIENT_ID, CLIENT_SECRET
```

### How It Works

The application will automatically detect which authentication method to use:

```python
if tenant_id and client_id and client_secret:
    # Use Azure AD (Service Principal)
    credential = ClientSecretCredential(...)
else:
    # Fallback to DefaultAzureCredential
    # (tries managed identity, Azure CLI, etc.)
    credential = DefaultAzureCredential()
```

## Authentication Fallback Chain

If you don't provide service principal credentials, the application uses `DefaultAzureCredential`, which tries:

1. **Environment variables** (AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET)
2. **Managed Identity** (if running in Azure App Service, Functions, VM, etc.)
3. **Azure CLI** (if you're logged in via `az login`)
4. **Visual Studio Code** (if logged in)
5. **Azure PowerShell** (if logged in)

This is great for local development!

## Production Best Practices

### 1. Use Managed Identity (Best)

If running in Azure (App Service, Functions, Container Instances, AKS):

```bash
# Enable system-assigned managed identity
az webapp identity assign --name your-app --resource-group your-rg

# Assign Cosmos DB permissions to managed identity
az role assignment create \
  --assignee $(az webapp identity show --name your-app --resource-group your-rg --query principalId -o tsv) \
  --role "Cosmos DB Account Contributor" \
  --scope $COSMOS_RESOURCE_ID
```

Then **don't set** TENANT_ID, CLIENT_ID, or CLIENT_SECRET in production.

### 2. Use Azure Key Vault

Store sensitive values in Key Vault:

```bash
# Store service principal credentials
az keyvault secret set --vault-name your-keyvault --name TenantId --value your-tenant-id
az keyvault secret set --vault-name your-keyvault --name ClientId --value your-client-id
az keyvault secret set --vault-name your-keyvault --name ClientSecret --value your-client-secret

# Grant app access to Key Vault
az keyvault set-policy --name your-keyvault \
  --spn your-client-id \
  --secret-permissions get list
```

### 3. Never Commit Secrets

- ✅ Add `.env` to `.gitignore`
- ✅ Use `.env.example` for documentation
- ✅ Use environment variables in CI/CD
- ✅ Rotate credentials regularly

## Troubleshooting

### Error: "Failed to initialize Cosmos DB"

**Check:**
1. COSMOSDB_ENDPOINT is correct
2. Service principal has correct permissions
3. TENANT_ID, CLIENT_ID, CLIENT_SECRET are correct
4. Network connectivity to Cosmos DB

### Error: "Unauthorized" or "Forbidden"

**Solution:**
1. Verify service principal has "Cosmos DB Account Contributor" role
2. Check role assignment scope (resource, resource group, or subscription)
3. Wait a few minutes for permissions to propagate

### Error: "ClientSecretCredential authentication failed"

**Check:**
1. CLIENT_SECRET is correct (it's the "password" from service principal creation)
2. Service principal hasn't expired
3. TENANT_ID matches your Azure AD tenant

### Testing Authentication Locally

```bash
# Test with Azure CLI
az login
cd backend
.\start.ps1

# Application will use Azure CLI credentials via DefaultAzureCredential
```

## Migration from Key-Based to Azure AD

### Step 1: Create Service Principal
Follow "Step 1: Create Service Principal" above

### Step 2: Assign Permissions
Follow "Step 2: Assign Cosmos DB Permissions" above

### Step 3: Update Configuration
```bash
# Add to .env
TENANT_ID=your-tenant-id
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret

# Remove (comment out)
# COSMOSDB_KEY=your-old-key
```

### Step 4: Test
```bash
cd backend
.\start.ps1
```

### Step 5: Verify Logs
```
Using ClientSecretCredential for CosmosDB authentication
Cosmos DB initialized: multimodal_insights/tasks
```

## Security Checklist

- [ ] Service principal created with minimal required permissions
- [ ] Secrets stored in Azure Key Vault (production)
- [ ] `.env` file in `.gitignore`
- [ ] Regular credential rotation schedule
- [ ] Audit logs enabled in Azure AD
- [ ] Managed identity used in Azure environments
- [ ] Key-based authentication disabled in production

## Additional Resources

- [Azure AD Service Principals](https://docs.microsoft.com/azure/active-directory/develop/app-objects-and-service-principals)
- [Azure RBAC for Cosmos DB](https://docs.microsoft.com/azure/cosmos-db/role-based-access-control)
- [DefaultAzureCredential](https://docs.microsoft.com/python/api/azure-identity/azure.identity.defaultazurecredential)
- [Managed Identity](https://docs.microsoft.com/azure/active-directory/managed-identities-azure-resources/overview)

---

**Summary**: Always use Azure AD authentication in production. Use managed identity when running in Azure, or service principal for external deployments. Key-based authentication should only be used for local development.
