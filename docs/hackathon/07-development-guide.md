# Development Quickstart Guide

## 🚀 Getting Started

This guide provides step-by-step instructions for setting up your development environment and building your first agent using our framework.

## 📋 Prerequisites

### System Requirements
- **Operating System**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 18.04+)
- **Python**: 3.11 or higher
- **Node.js**: 18.0 or higher (for frontend development)
- **Memory**: Minimum 8GB RAM (16GB recommended)
- **Storage**: 5GB free space

### Account Requirements
- **Azure OpenAI**: Access to GPT-4 and embeddings models
- **Azure Subscription**: For cloud resources (optional for local development)
- **GitHub Account**: For code repository access

---

## 🛠️ Environment Setup

### Step 1: Clone and Setup Framework

```bash
# Clone the repository
git clone https://github.com/your-org/agent-foundation.git
cd agent-foundation

# Setup framework development environment
cd framework
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -e .
pip install -r requirements.txt
```

### Step 2: Configure Azure OpenAI

```bash
# Copy environment template
cp .env.template .env

# Edit .env file with your credentials
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
```

### Step 3: Verify Installation

```python
# Test framework installation
python -c "from framework import MagenticFoundation; print('Framework installed successfully!')"

# Test Azure OpenAI connection
python examples/test_connection.py
```

---

## 👶 Your First Agent

Let's build a simple "Code Reviewer" agent to understand the framework basics.

### Step 1: Create Agent Class

Create `my_agents/code_reviewer.py`:

```python
from framework.agents.base import BaseAgent
from framework.core.types import AgentRunResponse, ChatMessage, Role, TextContent
from typing import Dict, Any
import structlog

logger = structlog.get_logger(__name__)

class CodeReviewerAgent(BaseAgent):
    """
    Simple code reviewer agent that analyzes code quality and provides feedback.
    
    This agent demonstrates:
    - Basic agent structure
    - LLM integration
    - Structured output generation
    """
    
    def __init__(self, name: str, azure_client):
        super().__init__(
            name=name,
            description="Code reviewer agent that analyzes code quality and provides improvement suggestions"
        )
        self.azure_client = azure_client
        self.system_prompt = """
        You are an expert code reviewer with extensive experience in multiple programming languages.
        
        Your responsibilities:
        1. Analyze code for bugs, security vulnerabilities, and performance issues
        2. Check code style, readability, and maintainability
        3. Suggest specific improvements with examples
        4. Provide overall quality assessment with scoring
        
        Always provide constructive, actionable feedback with specific examples.
        """
    
    async def run(self, messages, *, thread=None, **kwargs) -> AgentRunResponse:
        """Main execution method for code review."""
        
        # Extract code from messages
        code_content = self._extract_code_from_messages(messages)
        language = kwargs.get('language', 'auto-detect')
        
        # Perform code review
        review_result = await self._perform_code_review(code_content, language)
        
        # Format response
        response_text = self._format_review_response(review_result)
        
        logger.info("Code review completed", 
                   language=language, 
                   issues_found=len(review_result.get('issues', [])))
        
        return AgentRunResponse(messages=[
            ChatMessage(role=Role.ASSISTANT, contents=[TextContent(text=response_text)])
        ])
    
    def _extract_code_from_messages(self, messages) -> str:
        """Extract code content from message history."""
        normalized = self._normalize_messages(messages)
        
        # Look for code blocks or explicit code content
        for message in normalized:
            if message.get('role') == 'user':
                content = message.get('content', '')
                
                # Check for code blocks
                if '```' in content:
                    # Extract content between code blocks
                    start = content.find('```')
                    end = content.rfind('```')
                    if start != end and start != -1:
                        # Remove language identifier if present
                        code_start = content.find('\n', start) + 1
                        return content[code_start:end].strip()
                
                # Return entire content if no code blocks
                return content.strip()
        
        return ""
    
    async def _perform_code_review(self, code: str, language: str) -> Dict[str, Any]:
        """Perform comprehensive code review using LLM."""
        
        review_prompt = f"""
        Please perform a comprehensive code review of the following {language} code:

        ```{language}
        {code}
        ```

        Provide a detailed analysis covering:

        1. **Code Quality Assessment** (Score: 1-10)
           - Overall code quality rating
           - Key strengths and weaknesses

        2. **Issues Identified**
           - Bugs and potential runtime errors
           - Security vulnerabilities
           - Performance bottlenecks
           - Style and convention violations

        3. **Improvement Suggestions**
           - Specific code improvements with examples
           - Best practice recommendations
           - Refactoring opportunities

        4. **Code Metrics**
           - Complexity assessment
           - Maintainability score
           - Test coverage suggestions

        Format your response as structured analysis with clear sections and actionable feedback.
        """
        
        try:
            response = await self.azure_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": review_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            review_text = response.choices[0].message.content
            
            # Parse structured review (simplified parsing)
            return self._parse_review_response(review_text)
            
        except Exception as e:
            logger.error("Code review failed", error=str(e))
            return {
                "error": f"Review failed: {str(e)}",
                "quality_score": 0,
                "issues": [],
                "suggestions": []
            }
    
    def _parse_review_response(self, review_text: str) -> Dict[str, Any]:
        """Parse LLM response into structured review data."""
        
        # Simple parsing logic (in production, use more robust parsing)
        review_data = {
            "quality_score": 7,  # Default score
            "issues": [],
            "suggestions": [],
            "strengths": [],
            "raw_review": review_text
        }
        
        # Extract quality score
        if "Score:" in review_text:
            try:
                score_text = review_text.split("Score:")[1].split(")")[0]
                score = int(''.join(filter(str.isdigit, score_text)))
                review_data["quality_score"] = min(max(score, 1), 10)
            except:
                pass
        
        # Extract sections (simplified)
        sections = review_text.split("**")
        for i, section in enumerate(sections):
            if "Issues" in section and i + 1 < len(sections):
                # Parse issues from next section
                issues_text = sections[i + 1]
                review_data["issues"] = [
                    issue.strip() 
                    for issue in issues_text.split("-") 
                    if issue.strip() and len(issue.strip()) > 10
                ]
            
            elif "Improvement" in section and i + 1 < len(sections):
                # Parse suggestions from next section
                suggestions_text = sections[i + 1]
                review_data["suggestions"] = [
                    suggestion.strip() 
                    for suggestion in suggestions_text.split("-") 
                    if suggestion.strip() and len(suggestion.strip()) > 10
                ]
        
        return review_data
    
    def _format_review_response(self, review_result: Dict[str, Any]) -> str:
        """Format review results into readable response."""
        
        if "error" in review_result:
            return f"❌ **Code Review Failed**\n\n{review_result['error']}"
        
        quality_score = review_result.get('quality_score', 0)
        quality_emoji = "🟢" if quality_score >= 8 else "🟡" if quality_score >= 6 else "🔴"
        
        response = f"""# 📝 Code Review Report

## {quality_emoji} Overall Quality Score: {quality_score}/10

"""
        
        # Add issues section
        issues = review_result.get('issues', [])
        if issues:
            response += "## 🚨 Issues Identified\n\n"
            for i, issue in enumerate(issues[:5], 1):  # Limit to top 5
                response += f"{i}. {issue}\n"
            
            if len(issues) > 5:
                response += f"... and {len(issues) - 5} more issues\n"
            response += "\n"
        
        # Add suggestions section
        suggestions = review_result.get('suggestions', [])
        if suggestions:
            response += "## 💡 Improvement Suggestions\n\n"
            for i, suggestion in enumerate(suggestions[:5], 1):  # Limit to top 5
                response += f"{i}. {suggestion}\n"
            
            if len(suggestions) > 5:
                response += f"... and {len(suggestions) - 5} more suggestions\n"
            response += "\n"
        
        # Add full review
        response += "## 📋 Detailed Analysis\n\n"
        response += review_result.get('raw_review', 'No detailed analysis available.')
        
        return response
```

### Step 2: Create Agent Registration

Create `my_agents/__init__.py`:

```python
"""My custom agents module."""

from .code_reviewer import CodeReviewerAgent

__all__ = ['CodeReviewerAgent']
```

### Step 3: Test Your Agent

Create `test_my_agent.py`:

```python
import asyncio
from openai import AsyncAzureOpenAI
from my_agents.code_reviewer import CodeReviewerAgent
import os

async def test_code_reviewer():
    # Initialize Azure OpenAI client
    azure_client = AsyncAzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    
    # Create agent instance
    reviewer = CodeReviewerAgent("Code Reviewer", azure_client)
    
    # Test code sample
    test_code = """
def calculate_average(numbers):
    total = 0
    for num in numbers:
        total = total + num
    return total / len(numbers)

# Usage
nums = [1, 2, 3, 4, 5]
avg = calculate_average(nums)
print("Average:", avg)
    """
    
    # Create test messages
    messages = [
        {
            "role": "user", 
            "content": f"Please review this Python code:\n\n```python\n{test_code}\n```"
        }
    ]
    
    # Run agent
    print("🔍 Running code review...")
    result = await reviewer.run(messages, language="python")
    
    print("\n" + "="*50)
    print("CODE REVIEW RESULT")
    print("="*50)
    print(result.messages[0].contents[0].text)

if __name__ == "__main__":
    asyncio.run(test_code_reviewer())
```

### Step 4: Run Your Agent

```bash
# Make sure your environment is activated and configured
python test_my_agent.py
```

---

## 🏗️ Building Complex Workflows

### Step 1: Create Multi-Agent Workflow

Create `workflows/code_analysis_workflow.py`:

```python
from framework.patterns import SequentialPattern, ConcurrentPattern
from framework.core.orchestrator import Orchestrator
from my_agents.code_reviewer import CodeReviewerAgent

class CodeAnalysisWorkflow:
    """
    Comprehensive code analysis workflow using multiple agents.
    
    Workflow Steps:
    1. Code Quality Review
    2. Security Analysis (concurrent)
    3. Performance Analysis (concurrent)  
    4. Final Report Generation
    """
    
    def __init__(self, azure_client):
        self.azure_client = azure_client
        self.orchestrator = Orchestrator()
        
        # Initialize agents
        self.code_reviewer = CodeReviewerAgent("Code Reviewer", azure_client)
        
        # Register agents
        self._register_agents()
    
    async def _register_agents(self):
        """Register all workflow agents."""
        agents = [
            ("code_reviewer", self.code_reviewer),
        ]
        
        for agent_id, agent_instance in agents:
            await self.orchestrator.agent_registry.register_agent(
                agent_id=agent_id,
                agent_instance=agent_instance,
                capabilities=["code_analysis"]
            )
    
    async def analyze_code(self, code: str, language: str = "python") -> dict:
        """Execute complete code analysis workflow."""
        
        # Step 1: Initial code review
        review_result = await self.orchestrator.execute(
            task=f"Review this {language} code for quality issues:\n```{language}\n{code}\n```",
            pattern=SequentialPattern(agents=["code_reviewer"]),
            context={"language": language, "analysis_type": "quality"}
        )
        
        # For this example, we'll keep it simple with one agent
        # In a full implementation, you'd add security and performance agents
        
        return {
            "workflow_id": "code_analysis_001",
            "language": language,
            "review_result": review_result,
            "timestamp": "2024-01-15T10:30:00Z"
        }

# Usage example
async def run_workflow_example():
    from openai import AsyncAzureOpenAI
    import os
    
    azure_client = AsyncAzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    
    workflow = CodeAnalysisWorkflow(azure_client)
    
    test_code = """
def factorial(n):
    if n == 0:
        return 1
    else:
        return n * factorial(n-1)
    """
    
    result = await workflow.analyze_code(test_code, "python")
    print("Workflow completed:", result["workflow_id"])

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_workflow_example())
```

---

## 🧪 Testing and Debugging

### Unit Testing Your Agents

Create `tests/test_code_reviewer.py`:

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from my_agents.code_reviewer import CodeReviewerAgent

class TestCodeReviewerAgent:
    
    @pytest.fixture
    def mock_azure_client(self):
        """Mock Azure OpenAI client for testing."""
        client = MagicMock()
        
        # Mock chat completion response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """
        **Code Quality Assessment** (Score: 8/10)
        
        **Issues Identified**
        - No input validation for empty list
        - Potential division by zero error
        
        **Improvement Suggestions**
        - Add error handling for edge cases
        - Consider using built-in functions
        """
        
        client.chat.completions.create = AsyncMock(return_value=mock_response)
        return client
    
    @pytest.fixture
    def code_reviewer(self, mock_azure_client):
        """Create CodeReviewerAgent instance for testing."""
        return CodeReviewerAgent("Test Reviewer", mock_azure_client)
    
    @pytest.mark.asyncio
    async def test_extract_code_from_messages(self, code_reviewer):
        """Test code extraction from messages."""
        messages = [
            {
                "role": "user",
                "content": "Please review this code:\n```python\ndef hello():\n    print('hello')\n```"
            }
        ]
        
        code = code_reviewer._extract_code_from_messages(messages)
        assert "def hello():" in code
        assert "print('hello')" in code
    
    @pytest.mark.asyncio
    async def test_perform_code_review(self, code_reviewer, mock_azure_client):
        """Test code review execution."""
        test_code = "def test(): pass"
        
        result = await code_reviewer._perform_code_review(test_code, "python")
        
        assert "quality_score" in result
        assert result["quality_score"] > 0
        assert isinstance(result.get("issues", []), list)
        
        # Verify LLM was called
        mock_azure_client.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_full_agent_run(self, code_reviewer):
        """Test complete agent execution."""
        messages = [
            {
                "role": "user", 
                "content": "Review: ```python\ndef add(a, b): return a + b\n```"
            }
        ]
        
        result = await code_reviewer.run(messages, language="python")
        
        assert len(result.messages) == 1
        assert result.messages[0].role.value == "assistant"
        assert "Code Review Report" in result.messages[0].contents[0].text
    
    def test_parse_review_response(self, code_reviewer):
        """Test review response parsing."""
        sample_review = """
        **Code Quality Assessment** (Score: 7/10)
        
        **Issues Identified**
        - Missing error handling
        - No type hints
        
        **Improvement Suggestions**
        - Add exception handling
        - Include type annotations
        """
        
        parsed = code_reviewer._parse_review_response(sample_review)
        
        assert parsed["quality_score"] == 7
        assert len(parsed["issues"]) > 0
        assert len(parsed["suggestions"]) > 0

# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### Integration Testing

Create `tests/test_integration.py`:

```python
import pytest
import asyncio
from framework.core.orchestrator import Orchestrator
from framework.patterns import SequentialPattern
from my_agents.code_reviewer import CodeReviewerAgent

@pytest.mark.integration
class TestIntegration:
    """Integration tests for agent framework integration."""
    
    @pytest.mark.asyncio
    async def test_agent_registration_and_execution(self):
        """Test agent registration and orchestrated execution."""
        # This would require actual Azure OpenAI credentials
        # Skip in CI/CD or use mock credentials
        pytest.skip("Requires live Azure OpenAI credentials")
        
        # Real integration test code would go here
        orchestrator = Orchestrator()
        
        # ... rest of integration test
```

### Debugging Tools

Create `debug_tools/agent_debugger.py`:

```python
import structlog
import json
from datetime import datetime

class AgentDebugger:
    """Debugging utilities for agent development."""
    
    def __init__(self, log_level="INFO"):
        self.logger = structlog.get_logger(__name__)
        self.execution_traces = []
    
    def trace_agent_execution(self, agent_name: str, messages: list, result: dict):
        """Trace agent execution for debugging."""
        trace = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_name": agent_name,
            "input_messages": messages,
            "output_result": result,
            "execution_id": f"exec_{len(self.execution_traces) + 1}"
        }
        
        self.execution_traces.append(trace)
        self.logger.info("Agent execution traced", 
                        agent=agent_name, 
                        execution_id=trace["execution_id"])
    
    def save_debug_session(self, filename: str):
        """Save debug session to file."""
        with open(filename, 'w') as f:
            json.dump({
                "session_start": datetime.utcnow().isoformat(),
                "execution_traces": self.execution_traces
            }, f, indent=2)
    
    def print_execution_summary(self):
        """Print execution summary for debugging."""
        print("\n" + "="*50)
        print("AGENT EXECUTION SUMMARY")
        print("="*50)
        
        for trace in self.execution_traces:
            print(f"\n{trace['execution_id']}: {trace['agent_name']}")
            print(f"  Timestamp: {trace['timestamp']}")
            print(f"  Input messages: {len(trace['input_messages'])}")
            print(f"  Output length: {len(str(trace['output_result']))}")

# Usage in your agent testing
debugger = AgentDebugger()

async def debug_agent_run():
    # ... your agent code
    result = await agent.run(messages)
    debugger.trace_agent_execution("CodeReviewer", messages, result.__dict__)
    debugger.print_execution_summary()
```

---

## 📁 Project Structure

Organize your project following this recommended structure:

```
my_agent_project/
├── my_agents/                    # Your custom agents
│   ├── __init__.py
│   ├── code_reviewer.py
│   ├── security_analyzer.py
│   └── performance_tester.py
├── workflows/                    # Multi-agent workflows
│   ├── __init__.py
│   └── code_analysis_workflow.py
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── test_code_reviewer.py
│   └── test_integration.py
├── debug_tools/                  # Debugging utilities
│   ├── __init__.py
│   └── agent_debugger.py
├── configs/                      # Configuration files
│   ├── agent_config.yaml
│   └── workflow_config.yaml
├── examples/                     # Usage examples
│   ├── basic_usage.py
│   └── advanced_workflows.py
├── requirements.txt              # Dependencies
├── .env.template                 # Environment template
├── .env                         # Your environment (gitignored)
├── README.md                    # Project documentation
└── setup.py                     # Package setup
```

---

## 🔧 Configuration Management

### Agent Configuration File

Create `configs/agent_config.yaml`:

```yaml
# Agent Configuration
agents:
  code_reviewer:
    name: "Code Reviewer Agent"
    description: "Analyzes code quality and provides feedback"
    model: "gpt-4"
    temperature: 0.3
    max_tokens: 2000
    capabilities:
      - code_analysis
      - quality_assessment
      - security_review
    
  security_analyzer:
    name: "Security Analysis Agent"
    description: "Identifies security vulnerabilities in code"
    model: "gpt-4"
    temperature: 0.1
    max_tokens: 1500
    capabilities:
      - security_analysis
      - vulnerability_detection

# Workflow Configuration
workflows:
  code_analysis:
    name: "Complete Code Analysis"
    description: "Comprehensive code review workflow"
    agents:
      - code_reviewer
      - security_analyzer
    patterns:
      - type: "sequential"
        agents: ["code_reviewer"]
      - type: "concurrent"
        agents: ["security_analyzer", "performance_tester"]
```

### Configuration Loader

Create `configs/__init__.py`:

```python
import yaml
from pathlib import Path
from typing import Dict, Any

class ConfigManager:
    """Manage agent and workflow configurations."""
    
    def __init__(self, config_dir: str = "configs"):
        self.config_dir = Path(config_dir)
        self._configs = {}
    
    def load_config(self, config_name: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if config_name not in self._configs:
            config_path = self.config_dir / f"{config_name}.yaml"
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    self._configs[config_name] = yaml.safe_load(f)
            else:
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        return self._configs[config_name]
    
    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Get configuration for specific agent."""
        agent_config = self.load_config("agent_config")
        
        if agent_name not in agent_config.get("agents", {}):
            raise ValueError(f"Agent configuration not found: {agent_name}")
        
        return agent_config["agents"][agent_name]
    
    def get_workflow_config(self, workflow_name: str) -> Dict[str, Any]:
        """Get configuration for specific workflow."""
        workflow_config = self.load_config("agent_config")
        
        if workflow_name not in workflow_config.get("workflows", {}):
            raise ValueError(f"Workflow configuration not found: {workflow_name}")
        
        return workflow_config["workflows"][workflow_name]

# Usage
config_manager = ConfigManager()
code_reviewer_config = config_manager.get_agent_config("code_reviewer")
```

---

## 🚀 Deployment Preparation

### Containerization

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install the package
RUN pip install -e .

# Set environment variables
ENV PYTHONPATH=/app
ENV ENVIRONMENT=production

# Expose port for API (if applicable)
EXPOSE 8000

# Default command
CMD ["python", "-m", "my_agents.api"]
```

### Docker Compose for Development

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  agent-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
      - AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
      - ENVIRONMENT=development
    volumes:
      - .:/app
      - agent-logs:/app/logs
    depends_on:
      - redis

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

volumes:
  agent-logs:
```

---

## 📚 Next Steps

1. **[Continue to Advanced Topics →](./08-advanced-topics.md)** - Learn about performance optimization, security, and production deployment
2. **[Back to Hackathon Implementation →](./06-hackathon-implementation.md)** - Continue with remaining hackathon projects
3. **[Framework Architecture →](./02-framework-architecture.md)** - Deeper understanding of framework internals

---

## 🆘 Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Solution: Ensure proper Python path
export PYTHONPATH=/path/to/your/project:$PYTHONPATH

# Or install in development mode
pip install -e .
```

**2. Azure OpenAI Connection Issues**
```python
# Test connection manually
import os
from openai import AsyncAzureOpenAI

async def test_connection():
    client = AsyncAzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2024-02-15-preview", 
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        print("Connection successful!")
    except Exception as e:
        print(f"Connection failed: {e}")
```

**3. Agent Registration Issues**
```python
# Ensure agent implements BaseAgent properly
from framework.agents.base import BaseAgent

class MyAgent(BaseAgent):  # Must inherit from BaseAgent
    def __init__(self, name: str):
        super().__init__(name=name, description="...")  # Must call super().__init__
    
    async def run(self, messages, **kwargs):  # Must implement run method
        # Your agent logic here
        pass
```

### Getting Help

- **Framework Documentation**: Check `docs/` directory
- **Reference Applications**: 
  - `deep_research_app/` - Three execution paradigms (YAML, Code, MAF)
  - `finagent_app/` - Multi-pattern orchestration (Static)
  - `finagent_dynamic_app/` - **ReAct planning + Human-in-the-loop** 🌟
  - `multimodal_insights_app/` - **Custom Copilot + Azure AI Services** 🌟
- **Example Code**: See `framework/examples/` directory  
- **Debug Logging**: Enable detailed logging for troubleshooting
- **Community**: Join the developer community for support

---

## 🎯 Next Steps: Choose Your Reference App Template

Now that you understand the basics, choose a reference app as your starting point:

### Option 1: Start with Deep Research App
**Best for**: Understanding orchestration patterns, multiple execution modes
```powershell
cd deep_research_app
# Follow deep_research_app/README.md
```

### Option 2: Start with Financial Research App (Static)
**Best for**: Learning all patterns, domain-specific agents
```powershell
cd finagent_app
# Follow finagent_app/README.md
```

### Option 3: Start with Financial Research App (Dynamic) 🌟
**Best for**: Dynamic planning, human-in-the-loop, CosmosDB persistence
```powershell
cd finagent_dynamic_app
# Follow finagent_dynamic_app/GETTING_STARTED.md
```
**Key Features to Learn**:
- ReAct-based dynamic planning
- Human approval workflow
- Synthesis agent pattern (context optimization)
- CosmosDB persistence layer

### Option 4: Start with Multimodal Insights App 🌟
**Best for**: Multimodal processing, Azure AI Services, Custom Copilot UI
```powershell
cd multimodal_insights_app
# Follow multimodal_insights_app/README.md
```
**Key Features to Learn**:
- Azure Speech-to-Text integration
- Azure Document Intelligence integration
- Multimodal file processing (audio, video, PDF)
- Persona-based summarization
- Custom Copilot user experience

---

## 🎓 Recommended Learning Path

1. **Day 1-2**: Complete this quickstart guide
   - Build your first simple agent
   - Create a basic workflow
   - Understand framework basics

2. **Day 3-4**: Study Deep Research App
   - Understand three execution modes
   - Learn orchestration patterns
   - Run all three modes

3. **Day 5-7**: Deep dive into Financial Dynamic App
   - Study ReAct planning pattern
   - Understand human-in-the-loop workflow
   - Learn synthesis agent pattern
   - Explore CosmosDB persistence

4. **Day 8-10**: Explore Multimodal Insights App
   - Learn Azure AI Services integration
   - Build multimodal processing pipelines
   - Create custom Copilot experiences

5. **Day 11+**: Build Your Hackathon Project
   - Choose appropriate template
   - Customize for your domain
   - Implement your business logic
   - Test and refine