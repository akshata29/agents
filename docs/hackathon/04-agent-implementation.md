# Agent Implementation Guide

## 🎯 Creating MAF-Compliant Agents

This guide shows you how to create agents that work seamlessly with Microsoft Agent Framework and our orchestration patterns.

## 📋 MAF Agent Requirements

Every agent must implement the `BaseAgent` interface with these mandatory methods:

```python
from agent_framework import BaseAgent, AgentRunResponse, ChatMessage, Role, TextContent, AgentThread
from typing import Any, AsyncGenerator

class YourAgent(BaseAgent):
    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AgentRunResponse:
        """Execute the agent - REQUIRED by MAF."""
        pass
    
    async def run_stream(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AsyncGenerator[AgentRunResponseUpdate, None]:
        """Stream responses - REQUIRED by MAF."""
        pass
```

## 🏗 Complete Agent Implementation Template

Here's a complete template for implementing a agent:

```python
import asyncio
import structlog
from datetime import datetime
from typing import Any, Dict, List, Optional, AsyncGenerator

from agent_framework import (
    BaseAgent, AgentRunResponse, AgentRunResponseUpdate, 
    ChatMessage, Role, TextContent, AgentThread
)
from openai import AsyncAzureOpenAI

logger = structlog.get_logger(__name__)

class CustomAgent(BaseAgent):
    """
    Template for MAF-compliant agents with Azure OpenAI integration.
    
    This template demonstrates:
    - Proper MAF interface implementation
    - Azure OpenAI integration
    - Context handling
    - Error management
    - Logging and monitoring
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        azure_client: AsyncAzureOpenAI,
        model: str = "gpt-4",
        system_prompt: str = "You are a helpful AI assistant.",
        **kwargs
    ):
        """Initialize the agent."""
        super().__init__(name=name, description=description)
        
        self.azure_client = azure_client
        self.model = model
        self.system_prompt = system_prompt
        self.capabilities = kwargs.get("capabilities", [])
        self.tools = kwargs.get("tools", [])
        
        logger.info("Agent initialized", 
                   name=name, model=model, capabilities=len(self.capabilities))
    
    async def run(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AgentRunResponse:
        """
        Execute the agent - MAF required method.
        
        This is the main execution method that all orchestration patterns call.
        """
        start_time = datetime.utcnow()
        
        try:
            # 1. Normalize messages using helper method
            normalized_messages = self._normalize_messages(messages)
            
            # 2. Extract task and context
            task = self._extract_task(normalized_messages)
            context = kwargs.get('context', {})
            
            # 3. Build enhanced prompt with context
            prompt = self._build_prompt(task, context, normalized_messages)
            
            # 4. Execute LLM call
            result_text = await self._execute_llm(prompt)
            
            # 5. Create MAF-compliant response
            response_message = ChatMessage(
                role=Role.ASSISTANT,
                contents=[TextContent(text=result_text)]
            )
            
            # 6. Notify thread if provided (important for conversation continuity)
            if thread:
                await self._notify_thread_of_new_messages(
                    thread, normalized_messages, response_message
                )
            
            # 7. Log execution metrics
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info("Agent execution completed",
                       agent=self.name, 
                       execution_time=execution_time,
                       input_length=len(task),
                       output_length=len(result_text))
            
            return AgentRunResponse(messages=[response_message])
            
        except Exception as e:
            logger.error("Agent execution failed", 
                        agent=self.name, error=str(e), exc_info=True)
            
            # Return error as agent response (graceful degradation)
            error_message = ChatMessage(
                role=Role.ASSISTANT,
                contents=[TextContent(text=f"I encountered an error: {str(e)}")]
            )
            return AgentRunResponse(messages=[error_message])
    
    async def run_stream(
        self,
        messages: str | ChatMessage | list[str] | list[ChatMessage] | None = None,
        *,
        thread: AgentThread | None = None,
        **kwargs: Any
    ) -> AsyncGenerator[AgentRunResponseUpdate, None]:
        """
        Stream responses - MAF required method.
        
        For real-time applications and better user experience.
        """
        # Get full response first (implement true streaming as needed)
        response = await self.run(messages, thread=thread, **kwargs)
        
        # Yield streaming updates
        for message in response.messages:
            if message.contents:
                for content in message.contents:
                    if isinstance(content, TextContent):
                        yield AgentRunResponseUpdate(
                            contents=[content],
                            role=Role.ASSISTANT
                        )
    
    def _normalize_messages(self, messages) -> List[ChatMessage]:
        """
        Normalize input messages to standard ChatMessage list.
        
        Handles all possible input formats from MAF.
        """
        if messages is None:
            return []
        
        if isinstance(messages, str):
            return [ChatMessage(role=Role.USER, contents=[TextContent(text=messages)])]
        
        if isinstance(messages, ChatMessage):
            return [messages]
        
        if isinstance(messages, list):
            normalized = []
            for msg in messages:
                if isinstance(msg, str):
                    normalized.append(ChatMessage(role=Role.USER, contents=[TextContent(text=msg)]))
                elif isinstance(msg, ChatMessage):
                    normalized.append(msg)
            return normalized
        
        return []
    
    def _extract_task(self, messages: List[ChatMessage]) -> str:
        """Extract the main task from normalized messages."""
        if not messages:
            return "Please provide a task or question."
        
        # Get the last user message
        last_message = messages[-1]
        return last_message.text if hasattr(last_message, 'text') else str(last_message)
    
    def _build_prompt(self, task: str, context: Dict[str, Any], messages: List[ChatMessage]) -> str:
        """
        Build enhanced prompt with context from orchestration patterns.
        
        This is where you integrate context from previous agents in patterns.
        """
        prompt_parts = [f"Task: {task}"]
        
        # Add context from orchestration patterns
        if context:
            # Context from previous agents in sequential patterns
            if "previous_results" in context:
                prompt_parts.append(f"Previous Results: {context['previous_results']}")
            
            # Context from concurrent pattern aggregation
            if "parallel_results" in context:
                prompt_parts.append(f"Parallel Analysis: {context['parallel_results']}")
            
            # Domain-specific context
            if "domain" in context:
                prompt_parts.append(f"Domain: {context['domain']}")
            
            # Metadata from orchestrator
            if "metadata" in context:
                metadata = context["metadata"]
                if "priority" in metadata:
                    prompt_parts.append(f"Priority: {metadata['priority']}")
                if "constraints" in metadata:
                    prompt_parts.append(f"Constraints: {metadata['constraints']}")
        
        # Add conversation history for context
        if len(messages) > 1:
            conversation_context = []
            for msg in messages[:-1]:  # Exclude current message
                role = "User" if msg.role == Role.USER else "Assistant"
                conversation_context.append(f"{role}: {msg.text}")
            
            if conversation_context:
                prompt_parts.append(f"Conversation History:\n" + "\n".join(conversation_context))
        
        return "\n\n".join(prompt_parts)
    
    async def _execute_llm(self, prompt: str) -> str:
        """
        Execute LLM call with Azure OpenAI.
        
        Customize this method for your specific LLM integration.
        """
        try:
            # Prepare messages for Azure OpenAI
            openai_messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            # Add tool definitions if available
            kwargs = {
                "model": self.model,
                "messages": openai_messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            # Add tools if agent has them
            if self.tools:
                kwargs["tools"] = self._format_tools_for_openai()
            
            # Execute async call
            response = await self.azure_client.chat.completions.create(**kwargs)
            
            # Handle tool calls if present
            if response.choices[0].message.tool_calls:
                return await self._handle_tool_calls(response.choices[0].message.tool_calls, prompt)
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error("LLM execution failed", agent=self.name, error=str(e))
            return f"I apologize, but I encountered a technical issue: {str(e)}"
    
    def _format_tools_for_openai(self) -> List[Dict]:
        """Format agent tools for OpenAI function calling."""
        formatted_tools = []
        
        for tool in self.tools:
            # Convert internal tool format to OpenAI format
            formatted_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("parameters", {})
                }
            })
        
        return formatted_tools
    
    async def _handle_tool_calls(self, tool_calls, original_prompt: str) -> str:
        """Handle tool calls from LLM response."""
        tool_results = []
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            # Execute tool (implement your tool execution logic)
            result = await self._execute_tool(function_name, function_args)
            tool_results.append(f"Tool {function_name}: {result}")
        
        # Create follow-up prompt with tool results
        follow_up_prompt = f"""
        Original task: {original_prompt}
        
        Tool execution results:
        {chr(10).join(tool_results)}
        
        Please provide a comprehensive response based on the tool results.
        """
        
        # Recursive call to get final response
        return await self._execute_llm(follow_up_prompt)
    
    async def _execute_tool(self, tool_name: str, args: Dict) -> str:
        """
        Execute a specific tool.
        
        Implement your tool execution logic here.
        This could integrate with MCP servers, APIs, databases, etc.
        """
        # Placeholder implementation
        return f"Executed {tool_name} with args {args}"
    
    async def _notify_thread_of_new_messages(
        self, 
        thread: AgentThread, 
        input_messages: List[ChatMessage], 
        response_message: ChatMessage
    ) -> None:
        """Notify thread of conversation updates for continuity."""
        try:
            # Add input messages to thread
            for message in input_messages:
                await thread.add_message(message)
            
            # Add response message to thread
            await thread.add_message(response_message)
            
        except Exception as e:
            logger.warning("Failed to update thread", error=str(e))
    
    # Legacy compatibility method for YAML workflows
    async def process(self, task: str, context: Dict[str, Any] = None) -> str:
        """
        Legacy method for YAML workflow compatibility.
        
        This allows the agent to work with older workflow engines.
        """
        context = context or {}
        response = await self.run(messages=task, context=context)
        return response.messages[-1].text if response.messages else ""
```

## 🎯 Hackathon-Specific Agent Examples

### 1. Orchestrator Enhancement Agent

```python
class OrchestratorEnhancementAgent(BaseAgent):
    """Agent specialized for enhancing orchestration with multi-modal support."""
    
    def __init__(self, name: str, azure_client: AsyncAzureOpenAI):
        super().__init__(
            name=name,
            description="Enhances orchestration patterns with multi-modal capabilities"
        )
        self.azure_client = azure_client
        self.system_prompt = """
        You are an orchestration enhancement specialist. Your role is to:
        1. Analyze multi-modal input (documents, images, verbal instructions)
        2. Design optimal agent orchestration patterns
        3. Implement dynamic plan updating based on execution feedback
        4. Optimize for both accuracy and performance
        
        Key capabilities:
        - Multi-modal input processing
        - Dynamic pattern selection
        - Plan adaptation and optimization  
        - Performance monitoring and tuning
        """
    
    async def run(self, messages, *, thread=None, **kwargs) -> AgentRunResponse:
        """Enhanced orchestration planning with multi-modal support."""
        
        context = kwargs.get('context', {})
        
        # Extract multi-modal inputs
        documents = context.get('documents', [])
        images = context.get('images', [])
        audio_transcripts = context.get('audio_transcripts', [])
        
        # Build enhanced prompt
        task = self._extract_task(self._normalize_messages(messages))
        enhanced_prompt = self._build_orchestration_prompt(
            task, documents, images, audio_transcripts, context
        )
        
        # Execute with orchestration-specific processing
        result = await self._execute_llm(enhanced_prompt)
        
        return AgentRunResponse(messages=[
            ChatMessage(role=Role.ASSISTANT, contents=[TextContent(text=result)])
        ])
    
    def _build_orchestration_prompt(self, task, documents, images, audio, context):
        """Build specialized prompt for orchestration enhancement."""
        prompt = f"Orchestration Enhancement Task: {task}\n\n"
        
        if documents:
            prompt += f"Document Context ({len(documents)} documents):\n"
            for i, doc in enumerate(documents[:3]):  # Limit to first 3
                prompt += f"Doc {i+1}: {doc.get('summary', doc.get('content', '')[:200])}...\n"
            prompt += "\n"
        
        if images:
            prompt += f"Image Context ({len(images)} images):\n"
            for i, img in enumerate(images[:3]):
                prompt += f"Image {i+1}: {img.get('description', 'Visual content provided')}\n"
            prompt += "\n"
        
        if audio:
            prompt += f"Audio Context ({len(audio)} transcripts):\n"
            for i, transcript in enumerate(audio[:3]):
                prompt += f"Audio {i+1}: {transcript[:200]}...\n"
            prompt += "\n"
        
        prompt += """
        Based on this multi-modal input, please:
        1. Analyze the optimal orchestration pattern (sequential, concurrent, react, etc.)
        2. Recommend specific agents for each step
        3. Identify potential bottlenecks and optimization opportunities
        4. Suggest dynamic adaptation strategies
        5. Provide implementation guidance
        """
        
        return prompt
```

### 2. Multi-Modal Research Agent

```python
class MultiModalResearchAgent(BaseAgent):
    """Agent specialized for deep reasoning across multiple modalities."""
    
    def __init__(self, name: str, azure_client: AsyncAzureOpenAI, modality: str = "all"):
        super().__init__(
            name=name,
            description=f"Multi-modal research agent specializing in {modality} analysis"
        )
        self.azure_client = azure_client
        self.modality = modality  # "text", "image", "audio", "video", or "all"
        self.system_prompt = f"""
        You are a multi-modal research specialist focusing on {modality} analysis.
        Your capabilities include:
        1. Cross-modal information synthesis
        2. Deep reasoning and pattern recognition
        3. Evidence-based analysis and fact-checking
        4. Comprehensive report generation
        
        Always provide detailed analysis with proper citations and confidence levels.
        """
    
    async def run(self, messages, *, thread=None, **kwargs) -> AgentRunResponse:
        """Execute multi-modal research with deep reasoning."""
        
        context = kwargs.get('context', {})
        research_data = context.get('research_data', {})
        
        # Extract modality-specific data
        text_data = research_data.get('text', [])
        image_data = research_data.get('images', [])
        audio_data = research_data.get('audio', [])
        video_data = research_data.get('video', [])
        
        task = self._extract_task(self._normalize_messages(messages))
        
        # Build research-specific prompt
        research_prompt = self._build_research_prompt(
            task, text_data, image_data, audio_data, video_data, context
        )
        
        # Execute with research-optimized processing
        result = await self._execute_research_llm(research_prompt)
        
        return AgentRunResponse(messages=[
            ChatMessage(role=Role.ASSISTANT, contents=[TextContent(text=result)])
        ])
    
    def _build_research_prompt(self, task, text_data, image_data, audio_data, video_data, context):
        """Build specialized research prompt."""
        prompt = f"Research Task: {task}\n\n"
        
        # Add available data sources
        prompt += "Available Research Data:\n"
        
        if text_data:
            prompt += f"Text Sources ({len(text_data)}):\n"
            for i, source in enumerate(text_data[:5]):
                prompt += f"- Source {i+1}: {source.get('title', 'Untitled')} - {source.get('summary', '')[:150]}...\n"
        
        if image_data and self.modality in ["image", "all"]:
            prompt += f"Visual Sources ({len(image_data)}):\n"
            for i, img in enumerate(image_data[:3]):
                prompt += f"- Image {i+1}: {img.get('caption', 'Visual analysis available')}\n"
        
        if audio_data and self.modality in ["audio", "all"]:
            prompt += f"Audio Sources ({len(audio_data)}):\n"
            for i, audio in enumerate(audio_data[:3]):
                prompt += f"- Audio {i+1}: {audio.get('transcript', 'Audio analysis available')[:100]}...\n"
        
        prompt += f"""
        
        Research Requirements:
        - Provide comprehensive analysis across all available modalities
        - Include confidence levels for each finding
        - Cross-reference information between sources
        - Identify potential biases or limitations
        - Generate actionable insights
        - Include proper citations
        
        Research Focus: {context.get('research_focus', 'comprehensive analysis')}
        Depth Level: {context.get('depth', 'standard')}
        Target Audience: {context.get('audience', 'technical professionals')}
        """
        
        return prompt
    
    async def _execute_research_llm(self, prompt: str) -> str:
        """Execute LLM call optimized for research tasks."""
        try:
            response = await self.azure_client.chat.completions.create(
                model="gpt-4",  # Use more capable model for research
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more factual responses
                max_tokens=3000   # Longer responses for comprehensive research
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error("Research LLM execution failed", error=str(e))
            return f"Research analysis encountered an error: {str(e)}"
```

### 3. Data Retrieval Optimization Agent

```python
class DataOptimizationAgent(BaseAgent):
    """Agent specialized for optimizing data retrieval patterns."""
    
    def __init__(self, name: str, azure_client: AsyncAzureOpenAI):
        super().__init__(
            name=name,
            description="Optimizes data retrieval for large datasets with entitlement awareness"
        )
        self.azure_client = azure_client
        self.system_prompt = """
        You are a data retrieval optimization specialist. Your expertise includes:
        1. Query optimization and performance tuning
        2. Knowledge graph navigation and optimization
        3. Entitlement-aware data access patterns
        4. Caching and indexing strategies
        5. Distributed data architecture optimization
        
        Always consider security, performance, and scalability in your recommendations.
        """
    
    async def run(self, messages, *, thread=None, **kwargs) -> AgentRunResponse:
        """Execute data optimization analysis."""
        
        context = kwargs.get('context', {})
        
        # Extract data optimization context
        knowledge_graphs = context.get('knowledge_graphs', [])
        access_patterns = context.get('access_patterns', [])
        performance_metrics = context.get('performance_metrics', {})
        entitlement_rules = context.get('entitlement_rules', [])
        
        task = self._extract_task(self._normalize_messages(messages))
        
        # Build optimization-specific prompt
        optimization_prompt = self._build_optimization_prompt(
            task, knowledge_graphs, access_patterns, performance_metrics, entitlement_rules
        )
        
        result = await self._execute_llm(optimization_prompt)
        
        return AgentRunResponse(messages=[
            ChatMessage(role=Role.ASSISTANT, contents=[TextContent(text=result)])
        ])
    
    def _build_optimization_prompt(self, task, kgs, patterns, metrics, entitlements):
        """Build data optimization prompt."""
        prompt = f"Data Optimization Task: {task}\n\n"
        
        if kgs:
            prompt += f"Knowledge Graphs ({len(kgs)}):\n"
            for i, kg in enumerate(kgs[:3]):
                prompt += f"- KG {i+1}: {kg.get('name', 'Unnamed')} - {kg.get('size', 'Unknown')} entities\n"
        
        if patterns:
            prompt += f"\nAccess Patterns ({len(patterns)}):\n"
            for i, pattern in enumerate(patterns[:5]):
                prompt += f"- Pattern {i+1}: {pattern.get('query_type', 'Unknown')} - {pattern.get('frequency', 'Unknown')} requests/min\n"
        
        if metrics:
            prompt += f"\nCurrent Performance:\n"
            prompt += f"- Average Latency: {metrics.get('avg_latency', 'Unknown')}ms\n"
            prompt += f"- P95 Latency: {metrics.get('p95_latency', 'Unknown')}ms\n"
            prompt += f"- Error Rate: {metrics.get('error_rate', 'Unknown')}%\n"
        
        if entitlements:
            prompt += f"\nEntitlement Rules ({len(entitlements)} rules defined)\n"
        
        prompt += """
        
        Optimization Goals:
        1. Minimize query latency while maintaining accuracy
        2. Optimize for P95 performance under load
        3. Implement efficient caching strategies
        4. Ensure entitlement compliance at all levels
        5. Scale horizontally for increased load
        
        Please provide:
        - Specific optimization recommendations
        - Implementation strategy
        - Expected performance improvements
        - Risk assessment and mitigation
        """
        
        return prompt
```

### 4. General Purpose Agent with MCP Integration

```python
class GeneralPurposeAgent(BaseAgent):
    """Agent with dynamic capability selection via MCP integration."""
    
    def __init__(self, name: str, azure_client: AsyncAzureOpenAI, mcp_client=None):
        super().__init__(
            name=name,
            description="General purpose agent with dynamic MCP capability selection"
        )
        self.azure_client = azure_client
        self.mcp_client = mcp_client
        self.system_prompt = """
        You are a general purpose AI agent with access to dynamic capabilities via MCP.
        Your role is to:
        1. Analyze user requests to determine required capabilities
        2. Select and invoke appropriate MCP tools
        3. Integrate results from multiple tools
        4. Provide comprehensive responses
        
        Available capabilities are dynamically loaded based on context and requirements.
        """
    
    async def run(self, messages, *, thread=None, **kwargs) -> AgentRunResponse:
        """Execute with dynamic MCP capability selection."""
        
        context = kwargs.get('context', {})
        available_mcps = context.get('available_mcps', [])
        
        task = self._extract_task(self._normalize_messages(messages))
        
        # 1. Analyze task to determine required capabilities
        required_capabilities = await self._analyze_required_capabilities(task, context)
        
        # 2. Select appropriate MCP tools
        selected_tools = await self._select_mcp_tools(required_capabilities, available_mcps)
        
        # 3. Execute with selected tools
        result = await self._execute_with_mcps(task, selected_tools, context)
        
        return AgentRunResponse(messages=[
            ChatMessage(role=Role.ASSISTANT, contents=[TextContent(text=result)])
        ])
    
    async def _analyze_required_capabilities(self, task: str, context: Dict) -> List[str]:
        """Analyze task to determine required capabilities."""
        analysis_prompt = f"""
        Analyze this task to determine required capabilities: {task}
        
        Available capability categories:
        - text_processing
        - image_analysis  
        - data_analysis
        - web_search
        - file_operations
        - database_query
        - api_integration
        - code_generation
        
        Return a list of required capabilities.
        """
        
        # Use LLM to analyze capabilities
        response = await self._execute_llm(analysis_prompt)
        
        # Parse capabilities from response (implement proper parsing)
        capabilities = self._parse_capabilities(response)
        
        return capabilities
    
    async def _select_mcp_tools(self, capabilities: List[str], available_mcps: List[Dict]) -> List[Dict]:
        """Select appropriate MCP tools based on capabilities."""
        selected = []
        
        for capability in capabilities:
            # Find MCP tools that provide this capability
            matching_tools = [
                mcp for mcp in available_mcps 
                if capability in mcp.get('capabilities', [])
            ]
            
            if matching_tools:
                # Select best tool (could implement scoring logic)
                selected.append(matching_tools[0])
        
        return selected
    
    async def _execute_with_mcps(self, task: str, tools: List[Dict], context: Dict) -> str:
        """Execute task using selected MCP tools."""
        tool_results = {}
        
        # Execute each selected tool
        for tool in tools:
            try:
                if self.mcp_client:
                    result = await self.mcp_client.call_tool(
                        tool['name'], 
                        {'task': task, 'context': context}
                    )
                    tool_results[tool['name']] = result
                else:
                    # Fallback for testing
                    tool_results[tool['name']] = f"Simulated result from {tool['name']}"
            
            except Exception as e:
                logger.warning(f"Tool {tool['name']} failed", error=str(e))
                tool_results[tool['name']] = f"Tool error: {str(e)}"
        
        # Integrate results
        integration_prompt = f"""
        Task: {task}
        
        Tool Results:
        {self._format_tool_results(tool_results)}
        
        Please integrate these tool results to provide a comprehensive response to the task.
        """
        
        return await self._execute_llm(integration_prompt)
    
    def _parse_capabilities(self, response: str) -> List[str]:
        """Parse capabilities from LLM response."""
        # Implement proper parsing logic
        # This is a simplified version
        capabilities = []
        lines = response.lower().split('\n')
        
        known_capabilities = [
            'text_processing', 'image_analysis', 'data_analysis',
            'web_search', 'file_operations', 'database_query',
            'api_integration', 'code_generation'
        ]
        
        for line in lines:
            for capability in known_capabilities:
                if capability.replace('_', ' ') in line or capability in line:
                    capabilities.append(capability)
        
        return list(set(capabilities))  # Remove duplicates
    
    def _format_tool_results(self, results: Dict[str, str]) -> str:
        """Format tool results for integration prompt."""
        formatted = []
        for tool_name, result in results.items():
            formatted.append(f"{tool_name}: {result}")
        return '\n'.join(formatted)
```

## 🔧 Agent Registration and Usage

### Framework Registration

```python
from framework import MagenticFoundation

# Initialize framework
app = MagenticFoundation()
await app.initialize()

# Register agents
await app.agent_registry.register_agent(
    agent_id="orchestrator_enhancement",
    agent_instance=OrchestratorEnhancementAgent("Orchestrator Enhancer", azure_client),
    capabilities=["orchestration", "multi_modal", "planning", "optimization"]
)

await app.agent_registry.register_agent(
    agent_id="multimodal_researcher", 
    agent_instance=MultiModalResearchAgent("Multi-Modal Researcher", azure_client),
    capabilities=["research", "analysis", "multi_modal", "synthesis"]
)

await app.agent_registry.register_agent(
    agent_id="data_optimizer",
    agent_instance=DataOptimizationAgent("Data Optimizer", azure_client),
    capabilities=["data_optimization", "performance", "scaling", "security"]
)

await app.agent_registry.register_agent(
    agent_id="general_purpose",
    agent_instance=GeneralPurposeAgent("General Purpose", azure_client, mcp_client),
    capabilities=["dynamic", "mcp_integration", "flexible", "adaptive"]
)
```

### Pattern Integration

```python
# Use agents with orchestration patterns
from framework.patterns import SequentialPattern, ConcurrentPattern, ReActPattern

# Sequential pattern with specialized agents
sequential_result = await app.orchestrator.execute(
    task="Enhance orchestration system with multi-modal capabilities",
    pattern=SequentialPattern(agents=["orchestrator_enhancement", "data_optimizer"]),
    context={"documents": docs, "images": imgs, "requirements": requirements}
)

# Concurrent pattern for parallel analysis
concurrent_result = await app.orchestrator.execute(
    task="Parallel analysis of research data",
    pattern=ConcurrentPattern(agents=["multimodal_researcher", "data_optimizer"]),
    context={"research_data": data, "performance_targets": targets}
)

# ReAct pattern for dynamic planning
react_result = await app.orchestrator.execute(
    task="Dynamic capability selection and execution",
    pattern=ReActPattern(agent="general_purpose"),
    context={"available_mcps": mcps, "user_context": user_profile}
)
```

## 🔜 Next Steps

Now let's examine real-world implementations in our reference applications:

[→ Continue to Reference Applications Analysis](./05-reference-apps.md)

---

## 📚 Additional Resources

### Best Practices
- Always implement both `run()` and `run_stream()` methods
- Use proper message normalization
- Handle thread notifications for conversation continuity
- Implement graceful error handling
- Add comprehensive logging and monitoring
- Support both MAF and legacy compatibility

### Testing Your Agents
```python
# Unit test template
import pytest
from unittest.mock import Mock

@pytest.mark.asyncio
async def test_agent_run():
    azure_client = Mock()
    agent = CustomAgent("Test Agent", azure_client)
    
    # Mock Azure OpenAI response
    azure_client.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content="Test response"))]
    )
    
    # Test execution
    result = await agent.run("Test task")
    
    assert len(result.messages) == 1
    assert result.messages[0].role == Role.ASSISTANT
    assert "Test response" in result.messages[0].text
```

### Performance Optimization
- Use async/await properly for I/O operations
- Implement connection pooling for Azure OpenAI
- Cache frequently used prompts and responses
- Monitor token usage and costs
- Implement rate limiting and backoff strategies