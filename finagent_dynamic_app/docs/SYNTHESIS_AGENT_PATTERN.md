# Synthesis Agent Pattern

## Overview

The system now implements a **dual-context pattern** for different types of agents:

### Agent Types

1. **Data Gathering Agents** (Company, SEC, Earnings, Fundamentals, Technicals)
   - Perform specific, focused tasks
   - Only need explicit dependency outputs
   - Use `dependency_artifacts` context

2. **Synthesis Agents** (Forecaster, Report)
   - Analyze and combine data from multiple sources
   - Need comprehensive session context
   - Use `session_context` with ALL previous step outputs

## How It Works

### 1. Agent Type Detection

```python
def _is_synthesis_agent(self, step: Step) -> bool:
    """Check if agent needs comprehensive session context"""
    synthesis_agents = [AgentType.FORECASTER, AgentType.REPORT]
    return step.agent in synthesis_agents
```

### 2. Context Gathering

#### For Synthesis Agents
```python
async def _get_session_context(self, step: Step) -> Dict[str, Any]:
    """Get ALL previous completed step outputs"""
    all_steps = await self.cosmos.get_steps_by_plan(step.plan_id, step.session_id)
    previous_completed = [
        s for s in all_steps 
        if s.status == COMPLETED and s.order < step.order
    ]
    
    return {
        "session_context": [
            {
                "step_order": s.order,
                "agent": s.agent.value,
                "action": s.action,
                "tools": s.tools,
                "result": s.agent_reply
            }
            for s in previous_completed
        ]
    }
```

#### For Regular Agents
```python
async def _get_dependency_artifacts(self, step: Step) -> Dict[str, Any]:
    """Get outputs from explicit dependencies only"""
    # Only collects from step.dependencies list
    return {"dependency_artifacts": artifacts_from_dependencies}
```

### 3. Context Passing in _execute_step()

```python
if self._is_synthesis_agent(step):
    # Get ALL previous step outputs
    session_ctx = await self._get_session_context(step)
    context.update(session_ctx)
    logger.info(f"Added {len(session_ctx['session_context'])} steps to synthesis agent")
elif step.dependencies:
    # Get only explicit dependencies
    dep_artifacts = await self._get_dependency_artifacts(step)
    context.update(dep_artifacts)
```

## Agent Implementation

### ForecasterAgent

The `ForecasterAgent` now uses `session_context` to access all previous analysis:

```python
def _build_forecast_prompt(self, task, ticker, tool_name, context):
    # Priority 1: session_context (comprehensive)
    session_context = context.get("session_context", [])
    
    # Fallback: dependency_artifacts (backward compatibility)
    if not session_context:
        session_context = context.get("dependency_artifacts", [])
    
    # Extract ALL types of data
    for artifact in session_context:
        tools = artifact.get("tools", [])
        agent = artifact.get("agent", "")
        content = artifact.get("content", "")
        
        if "get_yahoo_finance_news" in tools:
            news_data = content
        if "get_recommendations" in tools:
            recommendations_data = content
        if "company" in agent.lower():
            company_data = content
        # etc...
```

## Benefits

1. **Comprehensive Analysis**: Synthesis agents see the full picture
2. **No Manual Dependencies**: Don't need to declare every dependency
3. **Automatic Data Discovery**: Agents find what they need in session context
4. **Backward Compatible**: Falls back to dependency_artifacts if needed
5. **Efficient for Data Gathering**: Regular agents don't get unnecessary context

## Example Workflow

```
Step 1: Company Agent → get_stock_info → company_data
Step 2: Company Agent → get_yahoo_finance_news → news_data  
Step 3: Company Agent → get_recommendations → recommendations_data
Step 4: Forecaster → analyze_positive_developments → Dependencies: [2,3]

OLD BEHAVIOR:
- Step 4 gets: news_data, recommendations_data (only explicit dependencies)
- MISSING: company_data from Step 1

NEW BEHAVIOR:
- Step 4 is synthesis agent
- Gets session_context with ALL steps: [1, 2, 3]
- Has access to: company_data, news_data, recommendations_data
- Makes comprehensive analysis with full context
```

## Configuration

Synthesis agents are defined in `task_orchestrator.py`:

```python
synthesis_agents = [AgentType.FORECASTER, AgentType.REPORT]
```

To add new synthesis agents:
1. Add to `synthesis_agents` list
2. Update agent's prompt building to use `session_context`
3. Extract relevant data from session artifacts

## Logging

The system logs comprehensive context gathering:

```
INFO: Checking if synthesis agent | agent=Forecaster | is_synthesis=True
INFO: Collecting session context for synthesis agent | plan_id=xxx
INFO: Found 4 previous completed steps | current_order=5
INFO: Added session context from step 1 | agent=Company | tools=['get_stock_info']
INFO: Added session context from step 2 | agent=Company | tools=['get_yahoo_finance_news']
INFO: Total session artifacts collected | num_artifacts=4
INFO: Added comprehensive session context for synthesis agent | num_session_artifacts=4
```

## Testing

To verify synthesis agent context:

1. Create multi-step plan with data gathering + forecaster
2. Check logs for "Added comprehensive session context"
3. Verify forecaster output uses data from ALL previous steps
4. Confirm no "lack of specific data" messages in output
