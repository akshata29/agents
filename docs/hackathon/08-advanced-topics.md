# Advanced Topics & Production Guide

## 🚀 Performance Optimization

### Concurrent Execution Strategies

The framework provides several approaches to optimize performance through intelligent concurrent execution:

#### 1. Pattern-Level Concurrency

```python
from framework.patterns import ConcurrentPattern, HybridPattern
import asyncio

class PerformanceOptimizedOrchestrator(BaseAgent):
    """
    Orchestrator optimized for high-throughput scenarios.
    """
    
    async def execute_parallel_analysis(self, tasks: List[str]) -> Dict[str, Any]:
        """Execute multiple analysis tasks concurrently with load balancing."""
        
        # Batch tasks for optimal resource utilization
        batch_size = self._calculate_optimal_batch_size(tasks)
        batches = [tasks[i:i + batch_size] for i in range(0, len(tasks), batch_size)]
        
        results = []
        
        for batch in batches:
            # Execute batch concurrently
            batch_results = await asyncio.gather(*[
                self._execute_single_task(task) for task in batch
            ], return_exceptions=True)
            
            # Handle exceptions and collect successful results
            processed_results = self._process_batch_results(batch_results, batch)
            results.extend(processed_results)
        
        return {
            "total_tasks": len(tasks),
            "successful_tasks": len([r for r in results if r.get("success", False)]),
            "results": results,
            "performance_metrics": await self._collect_performance_metrics()
        }
    
    def _calculate_optimal_batch_size(self, tasks: List[str]) -> int:
        """Calculate optimal batch size based on system resources and task complexity."""
        
        # Consider CPU cores, memory, and Azure OpenAI rate limits
        cpu_cores = os.cpu_count() or 4
        estimated_task_complexity = self._estimate_task_complexity(tasks)
        azure_rate_limit = 120  # Requests per minute
        
        # Balance between parallelism and rate limiting
        optimal_size = min(
            cpu_cores * 2,  # CPU-based concurrency
            azure_rate_limit // 4,  # Rate limit consideration
            max(1, len(tasks) // 10)  # Task distribution
        )
        
        return optimal_size
```

#### 2. Intelligent Caching System

```python
import hashlib
import json
from typing import Optional
from datetime import datetime, timedelta

class IntelligentCache:
    """
    Multi-level caching system for agent responses and computations.
    """
    
    def __init__(self, redis_client=None):
        self.memory_cache = {}
        self.redis_client = redis_client
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "memory_usage": 0
        }
    
    async def get_cached_response(self, 
                                 agent_name: str, 
                                 messages: List[Dict], 
                                 context: Dict) -> Optional[Dict]:
        """Get cached response if available and valid."""
        
        cache_key = self._generate_cache_key(agent_name, messages, context)
        
        # Level 1: Memory cache (fastest)
        if cache_key in self.memory_cache:
            cached_item = self.memory_cache[cache_key]
            if self._is_cache_valid(cached_item):
                self.cache_stats["hits"] += 1
                return cached_item["response"]
        
        # Level 2: Redis cache (persistent)
        if self.redis_client:
            try:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    cached_item = json.loads(cached_data)
                    if self._is_cache_valid(cached_item):
                        # Promote to memory cache
                        self.memory_cache[cache_key] = cached_item
                        self.cache_stats["hits"] += 1
                        return cached_item["response"]
            except Exception as e:
                logger.warning("Redis cache access failed", error=str(e))
        
        self.cache_stats["misses"] += 1
        return None
    
    async def cache_response(self, 
                           agent_name: str, 
                           messages: List[Dict], 
                           context: Dict, 
                           response: Dict,
                           ttl: int = 3600):
        """Cache agent response with intelligent TTL."""
        
        cache_key = self._generate_cache_key(agent_name, messages, context)
        
        cached_item = {
            "response": response,
            "timestamp": datetime.utcnow().isoformat(),
            "ttl": ttl,
            "agent_name": agent_name
        }
        
        # Store in memory cache
        self.memory_cache[cache_key] = cached_item
        
        # Store in Redis cache if available
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    cache_key,
                    ttl,
                    json.dumps(cached_item, default=str)
                )
            except Exception as e:
                logger.warning("Redis cache storage failed", error=str(e))
    
    def _generate_cache_key(self, agent_name: str, messages: List[Dict], context: Dict) -> str:
        """Generate deterministic cache key."""
        
        # Create normalized representation
        normalized_data = {
            "agent": agent_name,
            "messages": self._normalize_messages_for_caching(messages),
            "context": self._normalize_context_for_caching(context)
        }
        
        # Generate hash
        data_string = json.dumps(normalized_data, sort_keys=True)
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def _normalize_messages_for_caching(self, messages: List[Dict]) -> List[Dict]:
        """Normalize messages for consistent caching."""
        
        normalized = []
        for msg in messages:
            # Remove timestamp and other volatile fields
            normalized_msg = {
                "role": msg.get("role"),
                "content": msg.get("content", "").strip()
            }
            normalized.append(normalized_msg)
        
        return normalized
    
    def _normalize_context_for_caching(self, context: Dict) -> Dict:
        """Normalize context for caching, excluding volatile fields."""
        
        # Exclude fields that shouldn't affect caching
        excluded_fields = {
            "timestamp", "request_id", "session_id", 
            "user_id", "trace_id", "execution_id"
        }
        
        normalized = {
            k: v for k, v in context.items() 
            if k not in excluded_fields
        }
        
        return normalized
```

#### 3. Token Usage Optimization

```python
class TokenOptimizer:
    """
    Optimize token usage for cost-effective LLM interactions.
    """
    
    def __init__(self, model_limits: Dict[str, int]):
        self.model_limits = model_limits  # e.g., {"gpt-4": 8192, "gpt-3.5": 4096}
        self.token_stats = {
            "total_tokens_used": 0,
            "cost_estimate": 0.0,
            "optimization_savings": 0
        }
    
    async def optimize_messages_for_model(self, 
                                        messages: List[Dict], 
                                        model: str,
                                        max_tokens: int = None) -> List[Dict]:
        """Optimize message content to fit within token limits."""
        
        model_limit = self.model_limits.get(model, 4096)
        target_limit = min(model_limit * 0.8, max_tokens or model_limit)  # 80% safety margin
        
        current_tokens = await self._count_tokens(messages, model)
        
        if current_tokens <= target_limit:
            return messages  # No optimization needed
        
        # Apply optimization strategies
        optimized_messages = await self._apply_optimization_strategies(
            messages, target_limit, model
        )
        
        # Track savings
        optimized_tokens = await self._count_tokens(optimized_messages, model)
        self.token_stats["optimization_savings"] += (current_tokens - optimized_tokens)
        
        return optimized_messages
    
    async def _apply_optimization_strategies(self, 
                                           messages: List[Dict], 
                                           target_limit: int,
                                           model: str) -> List[Dict]:
        """Apply various optimization strategies in order of preference."""
        
        strategies = [
            self._remove_redundant_content,
            self._summarize_long_messages, 
            self._truncate_least_important_messages,
            self._compress_system_messages
        ]
        
        optimized = messages.copy()
        
        for strategy in strategies:
            current_tokens = await self._count_tokens(optimized, model)
            
            if current_tokens <= target_limit:
                break
                
            optimized = await strategy(optimized, target_limit, model)
        
        return optimized
    
    async def _summarize_long_messages(self, 
                                     messages: List[Dict], 
                                     target_limit: int,
                                     model: str) -> List[Dict]:
        """Summarize overly long individual messages."""
        
        summarized = []
        
        for msg in messages:
            content = msg.get("content", "")
            msg_tokens = await self._count_tokens([msg], model)
            
            # Summarize if message is too long
            if msg_tokens > target_limit * 0.3:  # Message uses >30% of budget
                summary_prompt = f"""
                Summarize the following content while preserving key information:
                
                {content}
                
                Provide a concise summary that maintains the essential meaning and context.
                """
                
                summarized_content = await self._execute_summarization(summary_prompt)
                
                summarized_msg = msg.copy()
                summarized_msg["content"] = f"[Summarized] {summarized_content}"
                summarized.append(summarized_msg)
            else:
                summarized.append(msg)
        
        return summarized
```

---

## 🔒 Security & Compliance

### Authentication and Authorization

```python
from functools import wraps
from typing import Set, Dict, Any
import jwt
from datetime import datetime, timedelta

class SecurityManager:
    """
    Comprehensive security management for agent framework.
    """
    
    def __init__(self, secret_key: str, token_expiry: int = 3600):
        self.secret_key = secret_key
        self.token_expiry = token_expiry
        self.role_permissions = {
            "admin": {"*"},  # Full access
            "developer": {"agent:read", "agent:write", "workflow:read", "workflow:write"},
            "user": {"agent:read", "workflow:read"},
            "service": {"agent:execute", "workflow:execute"}
        }
    
    def generate_token(self, user_id: str, roles: List[str], permissions: Set[str] = None) -> str:
        """Generate JWT token with role-based permissions."""
        
        # Calculate effective permissions
        effective_permissions = set()
        for role in roles:
            if role in self.role_permissions:
                effective_permissions.update(self.role_permissions[role])
        
        if permissions:
            effective_permissions.update(permissions)
        
        payload = {
            "user_id": user_id,
            "roles": roles,
            "permissions": list(effective_permissions),
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=self.token_expiry)
        }
        
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate and decode JWT token."""
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            raise SecurityException("Token has expired")
        except jwt.InvalidTokenError:
            raise SecurityException("Invalid token")
    
    def require_permission(self, required_permission: str):
        """Decorator to enforce permission-based access control."""
        
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract token from context
                context = kwargs.get('context', {})
                token = context.get('auth_token')
                
                if not token:
                    raise SecurityException("Authentication required")
                
                # Validate token and check permissions
                payload = self.validate_token(token)
                user_permissions = set(payload.get("permissions", []))
                
                # Check if user has required permission or wildcard
                if required_permission not in user_permissions and "*" not in user_permissions:
                    raise SecurityException(f"Insufficient permissions: {required_permission} required")
                
                # Add user context to function
                kwargs['user_context'] = {
                    "user_id": payload.get("user_id"),
                    "roles": payload.get("roles", []),
                    "permissions": user_permissions
                }
                
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator

class SecurityException(Exception):
    """Security-related exception."""
    pass

# Usage in agents
class SecureCodeReviewerAgent(BaseAgent):
    """Code reviewer agent with security controls."""
    
    def __init__(self, name: str, azure_client, security_manager: SecurityManager):
        super().__init__(name=name, description="Secure code reviewer agent")
        self.azure_client = azure_client
        self.security_manager = security_manager
    
    @security_manager.require_permission("agent:execute")
    async def run(self, messages, *, thread=None, **kwargs) -> AgentRunResponse:
        """Execute code review with security validation."""
        
        user_context = kwargs.get('user_context', {})
        
        # Log security event
        logger.info("Secure agent execution", 
                   user_id=user_context.get("user_id"),
                   agent=self.name)
        
        # Sanitize input
        sanitized_messages = await self._sanitize_input_messages(messages)
        
        # Execute review with audit trail
        result = await self._execute_secure_review(sanitized_messages, user_context)
        
        return result
    
    async def _sanitize_input_messages(self, messages: List[Dict]) -> List[Dict]:
        """Sanitize input messages to prevent injection attacks."""
        
        sanitized = []
        
        for msg in messages:
            content = msg.get("content", "")
            
            # Remove potentially dangerous patterns
            sanitized_content = await self._remove_dangerous_patterns(content)
            
            # Validate content length
            if len(sanitized_content) > 50000:  # 50KB limit
                raise SecurityException("Input content exceeds size limit")
            
            sanitized_msg = msg.copy()
            sanitized_msg["content"] = sanitized_content
            sanitized.append(sanitized_msg)
        
        return sanitized
    
    async def _remove_dangerous_patterns(self, content: str) -> str:
        """Remove potentially dangerous patterns from content."""
        
        import re
        
        # Remove common injection patterns
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # XSS
            r'javascript:',                # JavaScript URLs
            r'on\w+\s*=',                 # Event handlers
            r'eval\s*\(',                 # eval() calls
            r'exec\s*\(',                 # exec() calls
        ]
        
        cleaned_content = content
        
        for pattern in dangerous_patterns:
            cleaned_content = re.sub(pattern, '[REMOVED]', cleaned_content, flags=re.IGNORECASE | re.DOTALL)
        
        return cleaned_content
```

### Data Privacy and Compliance

```python
from cryptography.fernet import Fernet
import hashlib
from typing import Optional

class DataPrivacyManager:
    """
    Manage data privacy and compliance requirements.
    """
    
    def __init__(self, encryption_key: Optional[bytes] = None):
        self.encryption_key = encryption_key or Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # PII detection patterns
        self.pii_patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b\d{3}-?\d{3}-?\d{4}\b',
            "ssn": r'\b\d{3}-?\d{2}-?\d{4}\b',
            "credit_card": r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
        }
    
    def detect_pii(self, content: str) -> Dict[str, List[str]]:
        """Detect personally identifiable information in content."""
        
        import re
        
        detected_pii = {}
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                detected_pii[pii_type] = matches
        
        return detected_pii
    
    def anonymize_content(self, content: str, preserve_structure: bool = True) -> Dict[str, Any]:
        """Anonymize content by removing or replacing PII."""
        
        import re
        
        anonymized_content = content
        anonymization_map = {}
        
        for pii_type, pattern in self.pii_patterns.items():
            def replace_pii(match):
                original = match.group(0)
                
                if preserve_structure:
                    # Replace with structure-preserving placeholder
                    if pii_type == "email":
                        replacement = "user@example.com"
                    elif pii_type == "phone":
                        replacement = "XXX-XXX-XXXX"
                    elif pii_type == "ssn":
                        replacement = "XXX-XX-XXXX"
                    elif pii_type == "credit_card":
                        replacement = "XXXX-XXXX-XXXX-XXXX"
                    else:
                        replacement = f"[{pii_type.upper()}]"
                else:
                    replacement = f"[{pii_type.upper()}]"
                
                # Store mapping for potential restoration
                anonymization_map[original] = replacement
                
                return replacement
            
            anonymized_content = re.sub(pattern, replace_pii, anonymized_content, flags=re.IGNORECASE)
        
        return {
            "anonymized_content": anonymized_content,
            "anonymization_map": anonymization_map,
            "pii_detected": bool(anonymization_map)
        }
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data for storage."""
        
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt previously encrypted data."""
        
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
    
    def generate_data_hash(self, data: str) -> str:
        """Generate deterministic hash for data deduplication without storing original."""
        
        return hashlib.sha256(data.encode()).hexdigest()
```

---

## 📊 Monitoring & Observability

### Advanced Metrics Collection

```python
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
import time
from typing import Dict, Any, Optional

class AdvancedObservabilityManager:
    """
    Advanced observability with OpenTelemetry integration.
    """
    
    def __init__(self, service_name: str = "magentic-foundation"):
        self.service_name = service_name
        self.tracer = trace.get_tracer(__name__)
        self.meter = metrics.get_meter(__name__)
        
        # Initialize metrics
        self._initialize_metrics()
        
        # Performance tracking
        self.performance_data = {
            "agent_execution_times": {},
            "pattern_performance": {},
            "resource_utilization": {}
        }
    
    def _initialize_metrics(self):
        """Initialize OpenTelemetry metrics."""
        
        self.agent_execution_counter = self.meter.create_counter(
            name="agent_executions_total",
            description="Total number of agent executions",
            unit="1"
        )
        
        self.agent_execution_histogram = self.meter.create_histogram(
            name="agent_execution_duration_seconds",
            description="Agent execution duration in seconds",
            unit="s"
        )
        
        self.token_usage_counter = self.meter.create_counter(
            name="llm_tokens_consumed_total",
            description="Total LLM tokens consumed",
            unit="1"
        )
        
        self.error_counter = self.meter.create_counter(
            name="agent_errors_total",
            description="Total agent errors",
            unit="1"
        )
    
    def trace_agent_execution(self, agent_name: str, operation: str = "run"):
        """Create tracing context for agent execution."""
        
        def decorator(func):
            async def wrapper(*args, **kwargs):
                with self.tracer.start_as_current_span(
                    f"{agent_name}.{operation}",
                    attributes={
                        "agent.name": agent_name,
                        "operation.type": operation,
                        "service.name": self.service_name
                    }
                ) as span:
                    start_time = time.time()
                    
                    try:
                        # Execute function
                        result = await func(*args, **kwargs)
                        
                        # Record success metrics
                        execution_time = time.time() - start_time
                        
                        span.set_attribute("execution.duration", execution_time)
                        span.set_attribute("execution.success", True)
                        
                        # Update metrics
                        self.agent_execution_counter.add(1, {
                            "agent_name": agent_name,
                            "status": "success"
                        })
                        
                        self.agent_execution_histogram.record(execution_time, {
                            "agent_name": agent_name,
                            "operation": operation
                        })
                        
                        # Track performance data
                        self._update_performance_data(agent_name, execution_time, "success")
                        
                        return result
                        
                    except Exception as e:
                        execution_time = time.time() - start_time
                        
                        # Record error metrics
                        span.set_attribute("execution.duration", execution_time)
                        span.set_attribute("execution.success", False)
                        span.set_attribute("error.type", type(e).__name__)
                        span.set_attribute("error.message", str(e))
                        
                        self.agent_execution_counter.add(1, {
                            "agent_name": agent_name,
                            "status": "error"
                        })
                        
                        self.error_counter.add(1, {
                            "agent_name": agent_name,
                            "error_type": type(e).__name__
                        })
                        
                        # Track performance data
                        self._update_performance_data(agent_name, execution_time, "error")
                        
                        raise
            
            return wrapper
        return decorator
    
    def track_llm_usage(self, model: str, prompt_tokens: int, completion_tokens: int, cost: float):
        """Track LLM usage metrics."""
        
        total_tokens = prompt_tokens + completion_tokens
        
        self.token_usage_counter.add(total_tokens, {
            "model": model,
            "token_type": "total"
        })
        
        self.token_usage_counter.add(prompt_tokens, {
            "model": model,
            "token_type": "prompt"
        })
        
        self.token_usage_counter.add(completion_tokens, {
            "model": model,
            "token_type": "completion"
        })
        
        # Track cost if available
        if hasattr(self, 'cost_gauge'):
            self.cost_gauge.set(cost, {
                "model": model
            })
    
    def _update_performance_data(self, agent_name: str, execution_time: float, status: str):
        """Update internal performance tracking."""
        
        if agent_name not in self.performance_data["agent_execution_times"]:
            self.performance_data["agent_execution_times"][agent_name] = {
                "total_executions": 0,
                "total_time": 0.0,
                "success_count": 0,
                "error_count": 0,
                "avg_time": 0.0,
                "min_time": float('inf'),
                "max_time": 0.0
            }
        
        stats = self.performance_data["agent_execution_times"][agent_name]
        
        stats["total_executions"] += 1
        stats["total_time"] += execution_time
        
        if status == "success":
            stats["success_count"] += 1
        else:
            stats["error_count"] += 1
        
        stats["avg_time"] = stats["total_time"] / stats["total_executions"]
        stats["min_time"] = min(stats["min_time"], execution_time)
        stats["max_time"] = max(stats["max_time"], execution_time)
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        
        report = {
            "service_name": self.service_name,
            "report_timestamp": time.time(),
            "agent_performance": {},
            "system_health": {},
            "recommendations": []
        }
        
        # Agent performance analysis
        for agent_name, stats in self.performance_data["agent_execution_times"].items():
            success_rate = stats["success_count"] / stats["total_executions"] if stats["total_executions"] > 0 else 0
            
            performance_grade = self._calculate_performance_grade(stats, success_rate)
            
            report["agent_performance"][agent_name] = {
                **stats,
                "success_rate": success_rate,
                "performance_grade": performance_grade
            }
            
            # Generate recommendations
            if success_rate < 0.9:
                report["recommendations"].append(f"Agent '{agent_name}' has low success rate ({success_rate:.2%})")
            
            if stats["avg_time"] > 30.0:
                report["recommendations"].append(f"Agent '{agent_name}' has high average execution time ({stats['avg_time']:.2f}s)")
        
        # System health indicators
        total_executions = sum(stats["total_executions"] for stats in self.performance_data["agent_execution_times"].values())
        total_errors = sum(stats["error_count"] for stats in self.performance_data["agent_execution_times"].values())
        
        report["system_health"] = {
            "total_executions": total_executions,
            "total_errors": total_errors,
            "overall_error_rate": total_errors / total_executions if total_executions > 0 else 0,
            "active_agents": len(self.performance_data["agent_execution_times"])
        }
        
        return report
    
    def _calculate_performance_grade(self, stats: Dict, success_rate: float) -> str:
        """Calculate performance grade based on multiple factors."""
        
        # Factors: success rate, average time, consistency
        score = 0
        
        # Success rate (40% of grade)
        if success_rate >= 0.95:
            score += 40
        elif success_rate >= 0.90:
            score += 35
        elif success_rate >= 0.80:
            score += 25
        else:
            score += 10
        
        # Average time (30% of grade) - assuming <5s is excellent, <15s is good
        avg_time = stats["avg_time"]
        if avg_time < 5:
            score += 30
        elif avg_time < 15:
            score += 20
        elif avg_time < 30:
            score += 10
        else:
            score += 0
        
        # Consistency (30% of grade) - low variance is better
        if stats["total_executions"] > 1:
            time_variance = (stats["max_time"] - stats["min_time"]) / stats["avg_time"]
            if time_variance < 0.5:
                score += 30
            elif time_variance < 1.0:
                score += 20
            elif time_variance < 2.0:
                score += 10
            else:
                score += 0
        else:
            score += 15  # Neutral score for insufficient data
        
        # Convert to letter grade
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
```

---

## 🌐 Production Deployment

### Cloud Deployment Architecture

```python
# Azure deployment configuration
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient
import os

class ProductionConfig:
    """
    Production configuration management with Azure integration.
    """
    
    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.credential = DefaultAzureCredential()
        
        # Initialize Azure services
        self.key_vault_client = SecretClient(
            vault_url=os.getenv("AZURE_KEY_VAULT_URL"),
            credential=self.credential
        )
        
        self.blob_service_client = BlobServiceClient(
            account_url=os.getenv("AZURE_STORAGE_ACCOUNT_URL"),
            credential=self.credential
        )
        
        # Load configuration
        self.config = self._load_production_config()
    
    def _load_production_config(self) -> Dict[str, Any]:
        """Load production configuration from Azure Key Vault."""
        
        config = {
            "azure_openai": {
                "api_key": self._get_secret("azure-openai-api-key"),
                "endpoint": self._get_secret("azure-openai-endpoint"),
                "deployment_name": self._get_secret("azure-openai-deployment-name")
            },
            "database": {
                "connection_string": self._get_secret("database-connection-string")
            },
            "monitoring": {
                "application_insights_key": self._get_secret("application-insights-key"),
                "otlp_endpoint": self._get_secret("otlp-endpoint")
            },
            "security": {
                "jwt_secret": self._get_secret("jwt-secret-key"),
                "encryption_key": self._get_secret("data-encryption-key")
            }
        }
        
        return config
    
    def _get_secret(self, secret_name: str) -> str:
        """Retrieve secret from Azure Key Vault."""
        
        try:
            secret = self.key_vault_client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            logger.error(f"Failed to retrieve secret '{secret_name}'", error=str(e))
            raise
```

### Kubernetes Deployment

Create `k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: magentic-foundation-api
  namespace: agents
spec:
  replicas: 3
  selector:
    matchLabels:
      app: magentic-foundation-api
  template:
    metadata:
      labels:
        app: magentic-foundation-api
    spec:
      containers:
      - name: api
        image: your-registry.azurecr.io/magentic-foundation:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: AZURE_KEY_VAULT_URL
          valueFrom:
            secretKeyRef:
              name: azure-config
              key: key-vault-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: magentic-foundation-service
  namespace: agents
spec:
  selector:
    app: magentic-foundation-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### Health Checks and Monitoring

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import asyncio
import time

class HealthCheckManager:
    """
    Comprehensive health check system for production deployment.
    """
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.health_checks = {}
        self.startup_time = time.time()
        
        # Register health check endpoints
        self._register_health_endpoints()
    
    def _register_health_endpoints(self):
        """Register health check endpoints with FastAPI."""
        
        @self.app.get("/health")
        async def health_check():
            """Basic health check endpoint."""
            return JSONResponse({
                "status": "healthy",
                "timestamp": time.time(),
                "uptime": time.time() - self.startup_time
            })
        
        @self.app.get("/ready")
        async def readiness_check():
            """Readiness check endpoint."""
            
            checks = await self._run_readiness_checks()
            
            all_ready = all(check["status"] == "ready" for check in checks.values())
            
            if all_ready:
                return JSONResponse({
                    "status": "ready",
                    "checks": checks
                })
            else:
                raise HTTPException(status_code=503, detail={
                    "status": "not_ready",
                    "checks": checks
                })
        
        @self.app.get("/metrics")
        async def metrics_endpoint():
            """Prometheus metrics endpoint."""
            
            # Return Prometheus-formatted metrics
            metrics = await self._generate_prometheus_metrics()
            
            return Response(
                content=metrics,
                media_type="text/plain; version=0.0.4; charset=utf-8"
            )
    
    async def _run_readiness_checks(self) -> Dict[str, Dict[str, Any]]:
        """Run all readiness checks."""
        
        checks = {
            "azure_openai": await self._check_azure_openai(),
            "database": await self._check_database(),
            "cache": await self._check_cache(),
            "storage": await self._check_storage()
        }
        
        return checks
    
    async def _check_azure_openai(self) -> Dict[str, Any]:
        """Check Azure OpenAI connectivity."""
        
        try:
            # Test connection with minimal request
            response = await self.azure_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            
            return {
                "status": "ready",
                "response_time": 0.1,  # Measure actual response time
                "details": "Azure OpenAI accessible"
            }
            
        except Exception as e:
            return {
                "status": "not_ready",
                "error": str(e),
                "details": "Azure OpenAI connection failed"
            }
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity."""
        
        try:
            # Test database connection
            # Implementation depends on your database choice
            
            return {
                "status": "ready",
                "details": "Database accessible"
            }
            
        except Exception as e:
            return {
                "status": "not_ready",
                "error": str(e),
                "details": "Database connection failed"
            }
    
    async def _generate_prometheus_metrics(self) -> str:
        """Generate Prometheus-formatted metrics."""
        
        metrics = []
        
        # Example metrics
        metrics.append("# HELP agent_executions_total Total number of agent executions")
        metrics.append("# TYPE agent_executions_total counter")
        
        for agent_name, stats in self.observability_manager.performance_data["agent_execution_times"].items():
            metrics.append(f'agent_executions_total{{agent="{agent_name}"}} {stats["total_executions"]}')
        
        return "\n".join(metrics)
```

### Auto-Scaling Configuration

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: magentic-foundation-hpa
  namespace: agents
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: magentic-foundation-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
```

---

## 📈 Performance Tuning Best Practices

### 1. Agent Design Patterns

- **Stateless Agents**: Design agents to be stateless for better scalability
- **Efficient Prompting**: Use structured prompts to reduce token usage
- **Caching Strategies**: Implement intelligent caching at multiple levels
- **Batch Processing**: Process multiple requests concurrently where possible

### 2. Resource Optimization

- **Connection Pooling**: Reuse HTTP connections and database connections
- **Memory Management**: Implement proper cleanup and garbage collection
- **Token Optimization**: Use prompt compression and response caching
- **Concurrent Execution**: Leverage async/await for I/O-bound operations

### 3. Monitoring and Alerting

- **Performance Metrics**: Track execution times, success rates, and resource usage
- **Error Tracking**: Implement comprehensive error logging and alerting
- **Capacity Planning**: Monitor trends and plan for scaling needs
- **User Experience**: Track end-to-end response times and user satisfaction

---

## 🔚 Conclusion

This advanced topics guide provides the foundation for taking your agent framework from development to production. Focus on:

1. **Security First**: Implement proper authentication, authorization, and data protection
2. **Observability**: Comprehensive monitoring and logging for production operations  
3. **Performance**: Optimize for scalability and cost-effectiveness
4. **Reliability**: Build robust error handling and recovery mechanisms

For continued learning:
- [Framework Architecture](./02-framework-architecture.md) - Deep dive into framework internals
- [Development Guide](./07-development-guide.md) - Practical implementation steps
- [Reference Applications](./05-reference-apps.md) - Real-world implementation examples

---

## 📚 Additional Resources

### Production Checklist
- [ ] Security audit completed
- [ ] Performance testing passed
- [ ] Monitoring and alerting configured
- [ ] Disaster recovery plan established
- [ ] Documentation updated
- [ ] Team training completed

### Recommended Tools
- **Monitoring**: Prometheus, Grafana, Application Insights
- **Logging**: ELK Stack, Azure Monitor Logs
- **Security**: Azure Key Vault, HashiCorp Vault
- **CI/CD**: Azure DevOps, GitHub Actions
- **Container Registry**: Azure Container Registry, Docker Hub