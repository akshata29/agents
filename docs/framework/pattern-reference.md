# Magentic Foundation Framework - Complete Pattern Reference

**Quick reference for all available orchestration patterns**

## Pattern Overview

The framework provides **7 orchestration patterns** for different multi-agent scenarios:

| Pattern | Type | Source | Complexity | Best For |
|---------|------|--------|------------|----------|
| Sequential | Wrapper | MAF | ⭐ Simple | Chain execution, pipelines |
| Concurrent | Wrapper | MAF | ⭐⭐ Medium | Parallel processing, fan-out |
| Group Chat | Wrapper | MAF | ⭐⭐ Medium | Multi-expert discussions |
| Handoff | Wrapper | MAF | ⭐⭐ Medium | Routing, triage, escalation |
| ReAct | Custom | Framework | ⭐⭐⭐ Complex | Dynamic reasoning, planning |
| Hierarchical | Custom | Framework | ⭐⭐⭐ Complex | Manager-worker, teams |
| MAF Workflows | Native | MAF | ⭐⭐⭐ Complex | Graph-based, fan-in/out |

---

## 1. Sequential Pattern

**Purpose:** Execute agents one after another in a defined order

```python
from framework.patterns import SequentialPattern

pattern = SequentialPattern(
    agents=["planner", "researcher", "writer", "reviewer"],
    config={
        "preserve_context": True,
        "fail_fast": False
    }
)
```

**General Use Cases:**
- Content pipelines (research → write → edit → publish)
- Analysis workflows (collect → process → analyze → report)
- Multi-stage processing

**Financial Services Use Cases:**

### Banking:
- **Loan Application Processing**
  - Credit check → Risk assessment → Compliance review → Approval decision
  - Each stage requires previous results
  - Context preserved throughout pipeline
  
- **Account Opening Workflow**
  - Identity verification → KYC compliance → Credit assessment → Account setup
  - Sequential checks ensure regulatory compliance

- **Transaction Fraud Investigation**
  - Transaction analysis → Pattern detection → Risk scoring → Investigation report
  - Each agent builds on previous findings

### Insurance:
- **Claims Processing Pipeline**
  - Claim intake → Policy verification → Damage assessment → Payout calculation
  - Linear workflow with clear dependencies
  
- **Underwriting Process**
  - Application review → Risk assessment → Medical evaluation → Premium calculation
  - Each stage informs the next decision

- **Policy Renewal Workflow**
  - Policy review → Risk reassessment → Premium adjustment → Customer notification
  - Sequential evaluation of policy status

### Capital Markets:
- **IPO Preparation**
  - Company analysis → Financial due diligence → Valuation → Prospectus generation
  - Each stage requires completion of previous analysis
  
- **Investment Research Report**
  - Data collection → Financial modeling → Market analysis → Report generation
  - Linear research workflow with context preservation

- **Trade Settlement**
  - Trade validation → Clearing → Settlement → Confirmation
  - Sequential steps in settlement process

---

## 2. Concurrent Pattern

**Purpose:** Execute multiple agents simultaneously on the same task

```python
from framework.patterns import ConcurrentPattern

pattern = ConcurrentPattern(
    agents=["analyst1", "analyst2", "analyst3"],
    config={
        "max_concurrent": 3,
        "aggregation_method": "merge",
        "require_all_success": False
    }
)
```

**General Use Cases:**
- Multi-perspective analysis
- Parallel research
- Consensus building
- Redundancy and verification

**Financial Services Use Cases:**

### Banking:
- **Credit Risk Assessment**
  - Multiple risk models run in parallel (FICO, internal model, ML model)
  - Aggregate results for comprehensive risk view
  - Different perspectives on creditworthiness
  
- **Anti-Money Laundering (AML) Screening**
  - Parallel checks: Sanctions lists, PEP databases, adverse media
  - Multiple agents scan different data sources simultaneously
  - Faster screening with comprehensive coverage

- **Mortgage Valuation**
  - Multiple property appraisers work independently
  - Parallel assessment methods (comparative, income, cost approach)
  - Aggregate for final valuation

### Insurance:
- **Multi-Expert Claims Review**
  - Structural engineer + Claims adjuster + Fraud specialist
  - Each reviews claim independently
  - Aggregate findings for final decision
  
- **Catastrophe Loss Estimation**
  - Multiple models run concurrently (AIR, RMS, KCC)
  - Different modeling approaches in parallel
  - Consensus-based loss estimate

- **Medical Underwriting**
  - Parallel review by medical underwriters + automated risk scoring + claims history analysis
  - Independent assessments merged for decision

### Capital Markets:
- **Multi-Strategy Portfolio Analysis**
  - Multiple analysts assess same portfolio from different angles
  - Technical + Fundamental + Quantitative analysis in parallel
  - Comprehensive investment view
  
- **Market Impact Assessment**
  - Parallel analysis of order impact across multiple exchanges
  - Simultaneous liquidity analysis
  - Aggregate for optimal execution strategy

- **ESG Scoring**
  - Environmental + Social + Governance agents work concurrently
  - Each agent specializes in one dimension
  - Combined score from parallel assessments

---

## 3. Group Chat Pattern ✨ NEW

**Purpose:** Multi-agent collaborative conversation with managed turn-taking

```python
from framework.patterns import GroupChatPattern

pattern = GroupChatPattern(
    agents=["economist", "technologist", "sociologist"],
    config={
        "manager_type": "round_robin",
        "max_iterations": 10,
        "require_consensus": True
    }
)
```

**General Use Cases:**
- Panel discussions
- Multi-expert brainstorming
- Collaborative problem solving
- Consensus-driven decisions

**Manager Types:**
- `round_robin` - Agents speak in order
- `custom` - Custom selection logic

**Financial Services Use Cases:**

### Banking:
- **Credit Committee Deliberation**
  - Credit officer + Risk manager + Relationship manager + Compliance officer
  - Round-robin discussion of large loan applications
  - Consensus-based approval decision
  
- **New Product Development**
  - Product manager + Risk expert + Technology lead + Compliance specialist
  - Iterative discussion to design compliant, profitable products
  - All perspectives considered before launch

- **Financial Crime Investigation**
  - AML analyst + Fraud investigator + Legal counsel + Business unit rep
  - Collaborative review of suspicious activity
  - Group consensus on escalation decisions

### Insurance:
- **Complex Claims Adjudication**
  - Claims examiner + Medical reviewer + Legal counsel + Fraud investigator
  - Multi-round discussion of disputed claims
  - Collaborative decision with all expert input
  
- **Reinsurance Treaty Negotiation**
  - Actuary + Underwriter + Legal + Risk manager
  - Iterative discussion of treaty terms
  - Consensus on acceptable risk transfer

- **Catastrophe Response Planning**
  - Claims operations + Risk modeling + Communications + Finance
  - Collaborative planning for major event response
  - Group alignment on response strategy

### Capital Markets:
- **Investment Committee Decision**
  - Portfolio manager + Risk analyst + Sector specialist + Economist
  - Round-robin discussion of major investment decisions
  - Consensus-based allocation decisions
  
- **Market Structure Analysis**
  - Trader + Quant + Regulator expert + Technology lead
  - Collaborative analysis of market changes
  - Group recommendation on trading strategy

- **M&A Deal Evaluation**
  - Investment banker + Valuation expert + Industry analyst + Risk manager
  - Multi-perspective discussion of deal merits
  - Consensus on deal recommendation

---

## 4. Handoff Pattern ✨ NEW

**Purpose:** Dynamic agent-to-agent delegation based on conversation

```python
from framework.patterns import HandoffPattern, create_triage_pattern

# Option 1: Manual configuration
pattern = HandoffPattern(
    agents=["triage", "billing", "technical", "account"],
    initial_agent="triage",
    handoff_relationships={
        "triage": ["billing", "technical", "account"],
        "billing": ["triage"],
        "technical": ["triage"],
        "account": ["triage"]
    }
)

# Option 2: Helper function
pattern = create_triage_pattern(
    triage_agent="customer_service",
    specialist_agents=["billing", "technical", "account"]
)

# Option 3: Escalation pattern
pattern = create_escalation_pattern(
    agent_levels=[
        ["tier1_a", "tier1_b"],
        ["tier2"],
        ["tier3_senior"]
    ]
)
```

**General Use Cases:**
- Customer service routing
- Support escalation
- Specialized expertise delegation
- Dynamic task routing

**Handoff Strategies:**
- `explicit` - Agent explicitly calls handoff
- `automatic` - System determines handoffs
- `hybrid` - Combination of both

**Financial Services Use Cases:**

### Banking:
- **Customer Service Triage**
  - Triage agent: First-line support
  - Specialists: Account services, Lending specialist, Investment advisor, Technical support
  - Triage identifies issue type and hands off to appropriate specialist
  - Specialist handles or escalates further
  - Tracks handoff reason and customer journey
  
- **Fraud Investigation Escalation**
  - Level 1: Automated fraud detection system
  - Level 2: Fraud analyst (reviews flagged transactions)
  - Level 3: Senior investigator (complex cases)
  - Level 4: Legal/Law enforcement (criminal activity)
  - Each level can escalate based on severity, amount, or complexity

- **Loan Processing Workflow**
  - Intake: Loan officer (initial application)
  - Handoff to: Credit analyst (risk assessment)
  - Then to: Underwriter (approval decision)
  - Escalate to: Approval committee (large/complex loans)
  - Dynamic routing to specialized underwriters by loan type

### Insurance:
- **Claims Routing System**
  - Initial: Claims handler (first notice of loss)
  - Specialists: Property specialist, Injury specialist, Liability specialist
  - Routing: Agent determines claim type and hands off to expert
  - Escalation: Complex cases escalate through specialist tiers
  - Special handoff: Suspected fraud → Special investigations unit
  
- **Underwriting Escalation**
  - Level 1: Automated underwriting system (standard risks)
  - Level 2: Junior underwriter (routine cases)
  - Level 3: Senior underwriter (non-standard risks)
  - Level 4: Chief underwriter (high-value or complex)
  - Medical cases: Direct handoff to medical underwriter

- **Customer Complaint Resolution**
  - Level 1: Customer service representative
  - Level 2: Supervisor (unresolved issues)
  - Level 3: Department manager (formal complaints)
  - Level 4: Ombudsman/Legal (regulatory complaints)
  - Can hand back for additional investigation at any level

### Capital Markets:
- **Trading Desk Routing**
  - Entry: Order management system
  - Specialists: Equity trader, Fixed income trader, Derivatives trader, Algorithm specialist
  - Routes based on security type and order size
  - Escalates: Large orders → Head trader
  - Compliance: Unusual orders → Compliance review before execution
  
- **Research Request Handling**
  - Intake: Research coordinator (request triage)
  - Specialists: Sector analysts, Quantitative analysts, Technical analysts, Economists
  - Routes based on research topic and complexity
  - Escalates: Complex questions → Senior analysts → Chief strategist
  - Publication: Final reports → Editing/publishing team

- **Compliance Review Escalation**
  - Level 1: Automated surveillance system (flags potential issues)
  - Level 2: Compliance analyst (routine flags and investigations)
  - Level 3: Compliance officer (potential violations)
  - Level 4: Chief compliance officer/Legal (serious breaches)
  - Escalates based on severity and regulatory impact

---

## 5. ReAct Pattern

**Purpose:** Reasoning and acting with dynamic plan updates

```python
from framework.patterns import ReActPattern

pattern = ReActPattern(
    agents=["strategic_planner"],
    config={
        "reasoning_agent": "strategic_planner",
        "max_iterations": 10,
        "enable_backtracking": True
    }
)
```

**General Use Cases:**
- Complex problem solving
- Dynamic planning
- Adaptive execution
- Research with course correction

**Loop:** Observation → Thought → Action → Reflection

**Financial Services Use Cases:**

### Banking:
- **Complex Credit Investigation**
  - Observe: Initial credit application red flags
  - Think: What additional information is needed?
  - Act: Request specific documents or run additional checks
  - Reflect: Sufficient info? Need more investigation?
  - Adapt plan based on findings
  
- **Suspicious Activity Investigation**
  - Start with transaction pattern alert
  - Dynamically determine what to investigate next
  - Adjust investigation approach based on findings
  - Backtrack if initial hypothesis is wrong

- **Restructuring Loan Negotiation**
  - Observe customer financial situation
  - Plan negotiation strategy dynamically
  - Adjust terms based on customer responses
  - Revise approach if initial offer rejected

### Insurance:
- **Complex Fraud Investigation**
  - Start with suspicious claim indicators
  - Dynamically plan investigation steps
  - Adjust approach based on evidence found
  - Backtrack and try different angles if needed
  
- **Catastrophe Claims Handling**
  - Initial event assessment
  - Dynamic resource allocation based on claims volume
  - Adjust strategy as situation evolves
  - Revise estimates based on new data

- **High-Value Underwriting**
  - Observe initial application
  - Determine what additional assessments needed
  - Request info based on emerging risk factors
  - Adjust underwriting approach dynamically

### Capital Markets:
- **Algorithmic Trading Strategy Adaptation**
  - Observe market conditions
  - Think: Is current strategy optimal?
  - Act: Adjust parameters or switch strategies
  - Reflect: Did adjustment improve performance?
  - Dynamic adaptation to market regime changes
  
- **Investment Research Deep Dive**
  - Start with company overview
  - Dynamically determine what to investigate next
  - Adjust research plan based on findings
  - Backtrack if initial thesis is wrong

- **Risk Scenario Analysis**
  - Observe portfolio positions
  - Identify potential risk scenarios dynamically
  - Run targeted stress tests
  - Adjust risk assessment based on results

---

## 6. Hierarchical Pattern ✨ NEW

**Purpose:** Manager-worker coordination with task decomposition

```python
from framework.patterns import HierarchicalPattern, create_research_team

# Option 1: Manual configuration
pattern = HierarchicalPattern(
    manager_agent="project_manager",
    worker_agents=["developer1", "developer2", "tester"],
    worker_expertise={
        "developer1": ["frontend", "react"],
        "developer2": ["backend", "api"],
        "tester": ["qa", "testing"]
    },
    config={
        "allocation_strategy": "expertise",
        "enable_worker_collaboration": True,
        "require_manager_approval": False
    }
)

# Option 2: Research team
pattern = create_research_team(
    manager="lead_researcher",
    researchers=["primary", "secondary", "fact_checker"]
)

# Option 3: Content team
pattern = create_content_team(
    manager="content_manager",
    content_workers=["researcher", "writer", "editor", "reviewer"]
)

# Option 4: Analysis team
pattern = create_analysis_team(
    manager="analysis_manager",
    analysts=["data_analyst", "statistical_analyst", "business_analyst"]
)
```

**General Use Cases:**
- Project management
- Team coordination
- Task decomposition
- Parallel work distribution

**Allocation Strategies:**
- `round_robin` - Even distribution
- `expertise` - Based on skills
- `load_balanced` - Based on workload
- `first_available` - First to respond

**Financial Services Use Cases:**

### Banking:
- **Commercial Loan Processing**
  - Manager: Senior credit officer
  - Workers: Credit analyst, Financial analyst, Industry specialist, Compliance reviewer
  - Manager decomposes loan into analysis tasks
  - Allocates based on expertise (industry specialist for sector analysis)
  - Workers execute in parallel
  - Manager aggregates and makes final decision
  
- **Regulatory Reporting**
  - Manager: Regulatory reporting manager
  - Workers: Data extraction specialist, Calculation specialist, Validation specialist, Filing specialist
  - Manager breaks down report into components
  - Parallel processing of each component
  - Manager reviews and submits consolidated report

- **Branch Network Analysis**
  - Manager: Regional director
  - Workers: Branch performance analysts (one per branch)
  - Manager assigns each branch to an analyst
  - Parallel analysis of all branches
  - Manager aggregates for regional strategy

### Insurance:
- **Large Commercial Policy Underwriting**
  - Manager: Chief underwriter
  - Workers: Property underwriter, Liability underwriter, Cyber underwriter, Financial underwriter
  - Manager decomposes policy into coverage areas
  - Each specialist underwrites their portion
  - Manager aggregates for overall pricing and terms
  
- **Catastrophe Loss Assessment**
  - Manager: CAT manager
  - Workers: Regional claims coordinators (one per affected region)
  - Manager allocates regions to coordinators
  - Parallel loss assessment across regions
  - Manager aggregates for total loss estimate

- **Multi-State Regulatory Filing**
  - Manager: Regulatory compliance manager
  - Workers: State specialists (one per state)
  - Manager assigns states to specialists
  - Parallel preparation of state-specific filings
  - Manager reviews and coordinates submissions

### Capital Markets:
- **Multi-Asset Portfolio Construction**
  - Manager: Chief investment officer
  - Workers: Equity strategist, Fixed income strategist, Alternative investments specialist, Risk manager
  - Manager sets overall allocation strategy
  - Each specialist optimizes their asset class
  - Manager aggregates into unified portfolio
  
- **IPO Due Diligence**
  - Manager: Lead banker
  - Workers: Financial analyst, Legal reviewer, Market analyst, Operations specialist
  - Manager decomposes due diligence into work streams
  - Parallel execution of all work streams
  - Manager aggregates for final prospectus

- **Market Research Report**
  - Manager: Research director
  - Workers: Sector analysts (technology, healthcare, financials, etc.)
  - Manager assigns sectors to analysts
  - Parallel research on each sector
  - Manager synthesizes into market outlook

---

## 7. MAF Workflows (Graph-Based)

**Purpose:** Visual graph-based workflows with executors and edges

```python
from agent_framework import WorkflowBuilder

workflow = (
    WorkflowBuilder()
    .set_start_executor(planner)
    .add_fan_out_edges(planner, researchers)  # Parallel
    .add_fan_in_edges(researchers, synthesizer)  # Collect
    .build()
)
```

**General Use Cases:**
- Complex workflow graphs
- Fan-out/fan-in patterns
- Type-safe message passing
- Event streaming

See `EXECUTION_MODES_COMPARISON.md` and Phase 3 documentation.

**Financial Services Use Cases:**

### Banking:
- **Credit Decision Workflow**
  - Start: Application intake executor
  - Fan-out: Parallel credit check, fraud screening, document verification
  - Conditional: Low risk → Auto-approve, High risk → Manual review
  - Fan-in: Aggregate results
  - Decision: Approval executor with type-safe credit decision message
  
- **KYC/AML Onboarding**
  - Start: Customer data collection
  - Fan-out: Parallel identity verification, sanctions screening, PEP check, adverse media
  - Type-safe messages: Structured risk scores from each executor
  - Conditional edges: High risk → Enhanced due diligence path
  - Fan-in: Risk aggregation → Final approval

- **Regulatory Reporting Pipeline**
  - Start: Data extraction executor
  - Fan-out: Parallel calculations (capital ratios, liquidity, market risk)
  - Type-safe: Structured regulatory report sections
  - Fan-in: Report assembly executor
  - End: Validation and submission

### Insurance:
- **Auto Claims Processing**
  - Start: Claims intake executor
  - Fan-out: Parallel damage assessment, liability determination, coverage verification
  - Conditional: Total loss → Salvage workflow, Repairable → Repair workflow
  - Fan-in: Claims decision executor
  - Type-safe payment instruction messages
  
- **Underwriting Workflow**
  - Start: Application review executor
  - Fan-out: Parallel risk assessment (medical, financial, lifestyle)
  - Conditional edges: High risk → Additional medical exams
  - Fan-in: Pricing executor with type-safe premium calculation
  - End: Policy issuance or decline with structured reasons

- **Catastrophe Response**
  - Start: Event detection executor
  - Fan-out: Parallel regional loss estimation executors
  - Event streaming: Real-time loss updates
  - Fan-in: Aggregate loss projection
  - Dynamic edges: Add more regional executors as needed

### Capital Markets:
- **Trade Execution Pipeline**
  - Start: Order receipt executor
  - Conditional: Size-based routing (small → Direct, large → Algorithm)
  - Fan-out: Parallel risk check, compliance check, capital check
  - Type-safe: Structured approval/rejection messages
  - Fan-in: Execution decision
  - Event streaming: Real-time execution updates
  
- **Portfolio Rebalancing**
  - Start: Drift analysis executor
  - Fan-out: Parallel optimization for each asset class
  - Type-safe: Structured trade recommendations
  - Conditional: Requires approval → Manager review path
  - Fan-in: Trade list aggregation
  - End: Execution instructions

- **IPO Pricing Workflow**
  - Start: Financial analysis executor
  - Fan-out: Parallel market analysis, comparable analysis, investor feedback
  - Type-safe: Structured valuation messages
  - Fan-in: Price range determination
  - Conditional: Board approval → Launch, Revise → Back to analysis
  - Event streaming: Real-time pricing updates during roadshow

---

## Pattern Selection Guide

### Choose Sequential when:
- ✅ Tasks must be done in order
- ✅ Each step depends on previous results
- ✅ Simple linear pipeline
- ❌ Don't need parallelization

### Choose Concurrent when:
- ✅ Tasks can run in parallel
- ✅ Need multiple perspectives
- ✅ Want redundancy/verification
- ❌ Don't need inter-agent communication

### Choose Group Chat when:
- ✅ Need collaborative discussion
- ✅ Multiple experts should contribute
- ✅ Iterative refinement needed
- ✅ Consensus building important

### Choose Handoff when:
- ✅ Need dynamic routing
- ✅ Specialized agents for different tasks
- ✅ Triage/escalation workflows
- ✅ Agent decides who's next

### Choose ReAct when:
- ✅ Complex problem solving
- ✅ Need dynamic planning
- ✅ Uncertain path forward
- ✅ Backtracking might be needed

### Choose Hierarchical when:
- ✅ Clear manager-worker structure
- ✅ Task decomposition needed
- ✅ Need coordination layer
- ✅ Parallel work with oversight

### Choose MAF Workflows when:
- ✅ Visual workflow design important
- ✅ Complex graph structures
- ✅ Type-safe message passing critical
- ✅ Event streaming required

---

## Combining Patterns

Patterns can be combined for sophisticated workflows:

### Example 1: Hierarchical + Handoff
```python
# Manager uses handoff pattern for routing
# Workers use sequential patterns for their tasks

manager_pattern = HandoffPattern(
    agents=["manager", "team_a", "team_b"],
    initial_agent="manager"
)

team_a_pattern = SequentialPattern(
    agents=["research", "analyze", "report"]
)
```

### Example 2: Group Chat + ReAct
```python
# Group chat for discussion
# ReAct for individual agent reasoning

group_pattern = GroupChatPattern(
    agents=["expert1", "expert2", "expert3"]
)

# Each expert uses ReAct internally
expert_pattern = ReActPattern(
    agents=["expert1"],
    config={"max_iterations": 5}
)
```

### Example 3: Hierarchical + Concurrent
```python
# Manager distributes to workers
# Workers execute concurrently

hierarchical_pattern = HierarchicalPattern(
    manager_agent="coordinator",
    worker_agents=["worker1", "worker2", "worker3"],
    config={"allocation_strategy": "load_balanced"}
)

# Workers can use concurrent pattern internally
```

---

## Quick Reference Code

### Import Statements
```python
# Core patterns
from framework.patterns import (
    SequentialPattern,
    ConcurrentPattern,
    ReActPattern,
    GroupChatPattern,
    HandoffPattern,
    HierarchicalPattern
)

# Helper functions
from framework.patterns import (
    create_triage_pattern,
    create_escalation_pattern,
    create_research_team,
    create_content_team,
    create_analysis_team
)

# Orchestrator
from framework.core.orchestrator import MagenticOrchestrator
```

### Basic Execution
```python
orchestrator = MagenticOrchestrator()

# Execute any pattern
result = await orchestrator.execute(
    pattern=my_pattern,
    task="Your task description here"
)
```

---

## Pattern Configuration Examples

### Sequential with Context Management
```python
SequentialPattern(
    agents=["agent1", "agent2", "agent3"],
    config={
        "preserve_context": True,
        "fail_fast": False,
        "context_window_limit": 32000
    }
)
```

### Concurrent with Aggregation
```python
ConcurrentPattern(
    agents=["agent1", "agent2", "agent3"],
    config={
        "max_concurrent": 3,
        "timeout_per_agent": 300,
        "require_all_success": False,
        "aggregation_method": "merge",
        "wait_for_all": True
    }
)
```

### Group Chat with Round-Robin
```python
GroupChatPattern(
    agents=["expert1", "expert2", "expert3"],
    config={
        "manager_type": "round_robin",
        "max_iterations": 40,
        "require_consensus": False
    }
)
```

### Handoff with Custom Instructions
```python
HandoffPattern(
    agents=["triage", "specialist1", "specialist2"],
    initial_agent="triage",
    config={
        "handoff_strategy": "explicit",
        "allow_return_handoffs": True,
        "max_handoffs": 10,
        "handoff_instructions": "Custom instructions here"
    }
)
```

### ReAct with Backtracking
```python
ReActPattern(
    agents=["planner"],
    config={
        "reasoning_agent": "planner",
        "max_iterations": 10,
        "max_reasoning_steps": 50,
        "enable_backtracking": True
    }
)
```

### Hierarchical with Expertise
```python
HierarchicalPattern(
    manager_agent="manager",
    worker_agents=["worker1", "worker2"],
    worker_expertise={
        "worker1": ["skill_a", "skill_b"],
        "worker2": ["skill_c", "skill_d"]
    },
    config={
        "allocation_strategy": "expertise",
        "max_workers_per_task": 2,
        "enable_worker_collaboration": True,
        "require_manager_approval": False,
        "timeout_per_worker": 300
    }
)
```

---

## Additional Resources

- **Framework README**: `framework/README.md`
- **Phase 3 Report**: `PHASE_3_COMPLETE.md` (MAF Workflows)
- **Phase 4b Report**: `PHASE_4B_MISSING_PATTERNS.md` (New patterns)
- **Execution Modes**: `EXECUTION_MODES_COMPARISON.md`
- **Deep Research App**: `deep_research_app/README.md` (Examples)

---

## Pattern Architecture

All patterns follow consistent architecture:

```python
class MyPattern(OrchestrationPattern):
    """Pattern implementation."""
    
    # Pydantic fields for configuration
    field1: str = Field(description="...")
    field2: int = Field(default=10, description="...")
    
    def __init__(self, agents, config, ...):
        """Initialize pattern."""
        super().__init__(...)
    
    async def execute(self, input_data, context):
        """Execute pattern."""
        return await self._execute_with_orchestrator(input_data, context)
    
    def validate(self):
        """Validate configuration."""
        # Validation logic
        return True
    
    def get_execution_summary(self):
        """Get execution summary."""
        return {...}
```

---

## Summary

✅ **7 total patterns** available  
✅ **4 MAF wrappers** (Sequential, Concurrent, Group Chat, Handoff)  
✅ **2 custom implementations** (ReAct, Hierarchical)  
✅ **1 native MAF** (Workflows - graph-based)  
✅ **8 helper functions** for common scenarios  
✅ **Consistent API** across all patterns  
✅ **Complete documentation** with examples  

**Ready to orchestrate any multi-agent scenario!**
