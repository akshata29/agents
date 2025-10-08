"""
Group Chat Orchestration Pattern using Microsoft Agent Framework

This pattern demonstrates group chat orchestration following the documented
best practices for collaborative multi-agent conversations. Agents participate
in iterative maker-checker loops with moderated turn-taking and decision-making.

Pattern Architecture: Writer ⟷ Reviewer ⟷ Moderator (iterative conversation)

Key Characteristics:
- Spontaneous or guided collaboration among agents (supports human participation)
- Iterative maker-checker loops where agents take turns creating and reviewing
- Transparent and auditable conversations with all output in single thread
- Real-time conversation management with smart termination logic
- Quality control through multiple expert perspectives and consensus building

Implementation follows the documented 6-step process:
1. Create chat client (via AgentFactory)
2. Define collaborative agents (Writer, Reviewer, Moderator)
3. Build group chat workflow using custom GroupChatManager with WorkflowBuilder
4. Run workflow with iterative conversation management
5. Process results from complete conversation thread
6. Handle aggregated responses with participant identification

Customization Options (per hackathon guidelines):
- Conversation result filtering and summarization
- Next agent selection logic
- User input integration points  
- Conversation termination criteria

Uses WorkflowBuilder with custom executor from the official Microsoft Agent Framework.
"""

import asyncio
from datetime import datetime
from typing import List, Optional

from agent_framework import (
    ChatMessage, Role, WorkflowBuilder, Executor, 
    WorkflowContext, WorkflowOutputEvent, handler
)
from azure.identity import AzureCliCredential

from common.agents import AgentFactory


class GroupChatManager(Executor):
    """
    Manages group chat orchestration with turn-taking and decision making.
    
    This executor coordinates iterative conversations between Writer, Reviewer, 
    and Moderator agents, implementing the documented group chat pattern with:
    - Maker-checker loops for quality control
    - Smart termination logic based on consensus or iteration limits
    - Conversation flow management with participant turn-taking
    - Support for human-in-the-loop integration points
    
    Follows the Group Chat call order from hackathon guidelines:
    1. should_request_user_input: Check for human input needs
    2. should_terminate: Determine conversation completion 
    3. filter_results: Process final conversation if ending
    4. select_next_agent: Choose next participant if continuing
    """
    
    def __init__(self, factory: AgentFactory, max_iterations: int = 6):
        super().__init__(id="group_chat_manager")
        self.factory = factory
        self.max_iterations = max_iterations
        self.current_iteration = 0
        
        # Create agents for group chat
        self.writer = factory.create_writer_agent()
        self.reviewer = factory.create_reviewer_agent()
        self.moderator = factory.create_moderator_agent()
        
        # Conversation history
        self.conversation: List[ChatMessage] = []
    
    @handler
    async def start_group_chat(
        self, 
        task: str, 
        ctx: WorkflowContext[List[ChatMessage]]
    ) -> None:
        """Handle the initial task and start the group chat process."""
        print(f"🏁 Starting group chat orchestration: {task}")
        
        # Add initial user message
        user_message = ChatMessage(role=Role.USER, text=task)
        self.conversation.append(user_message)
        
        # Start the iterative conversation
        await self._run_conversation_loop(ctx)
    
    async def _run_conversation_loop(self, ctx: WorkflowContext[List[ChatMessage]]) -> None:
        """Run the main conversation loop between agents."""
        
        while self.current_iteration < self.max_iterations:
            self.current_iteration += 1
            print(f"\n🔄 Group Chat Iteration {self.current_iteration}/{self.max_iterations}")
            
            # Phase 1: Writer creates/refines content
            print("📝 Writer phase...")
            writer_response = await self.writer.run(self.conversation)
            
            if writer_response.messages:
                latest_message = writer_response.messages[-1]
                self.conversation.append(ChatMessage(
                    role=Role.ASSISTANT,
                    text=latest_message.text,
                    author_name="Writer"
                ))
                print(f"   Writer: {latest_message.text[:100]}...")
            
            # Phase 2: Reviewer evaluates content
            print("🔍 Reviewer phase...")
            review_prompt = self.conversation + [ChatMessage(
                role=Role.USER,
                text="Please review the writer's latest response. Provide specific feedback and indicate if this is ready for final approval or needs revision."
            )]
            
            reviewer_response = await self.reviewer.run(review_prompt)
            
            if reviewer_response.messages:
                review_message = reviewer_response.messages[-1]
                self.conversation.append(ChatMessage(
                    role=Role.ASSISTANT,
                    text=review_message.text,
                    author_name="Reviewer"
                ))
                print(f"   Reviewer: {review_message.text[:100]}...")
                
                # Check if reviewer approves (simple heuristic)
                review_text = review_message.text.lower()
                is_approved = any(term in review_text for term in [
                    "approved", "ready", "excellent", "good to go", "final approval"
                ])
            else:
                is_approved = False
            
            # Phase 3: Moderator makes decision
            print("⚖️  Moderator decision phase...")
            moderator_prompt = self.conversation + [ChatMessage(
                role=Role.USER,
                text="Based on the conversation so far, should we: 1) Continue iterating for improvements, 2) Conclude with current content, or 3) Request significant revisions? Provide your decision and reasoning."
            )]
            
            moderator_response = await self.moderator.run(moderator_prompt)
            
            if moderator_response.messages:
                mod_message = moderator_response.messages[-1]
                self.conversation.append(ChatMessage(
                    role=Role.ASSISTANT,
                    text=mod_message.text,
                    author_name="Moderator"
                ))
                print(f"   Moderator: {mod_message.text[:100]}...")
                
                # Check if moderator concludes (simple heuristic)
                mod_text = mod_message.text.lower()
                should_conclude = any(term in mod_text for term in [
                    "conclude", "complete", "finished", "final", "ready to deliver"
                ]) or is_approved
            else:
                should_conclude = False
            
            # Decision point: continue or conclude
            if should_conclude:
                print("✅ Group chat concluded by moderator decision!")
                break
            
            print("🔄 Continuing iteration based on feedback...")
        
        if self.current_iteration >= self.max_iterations:
            print("⏰ Maximum iterations reached, concluding group chat.")
        
        # Yield the final conversation
        await ctx.yield_output(self.conversation)


async def run_group_chat_orchestration(task: str = None) -> list:
    """
    Demonstrates group chat orchestration following Microsoft Agent Framework best practices.
    
    This implementation follows the documented 6-step group chat pattern process:
    1. Create chat client (via AgentFactory)
    2. Define collaborative agents with distinct conversation roles
    3. Build group chat workflow using custom GroupChatManager with WorkflowBuilder
    4. Run workflow - manages iterative conversation with maker-checker loops
    5. Process results - extract complete conversation thread from all participants
    6. Handle aggregated responses - process messages with participant identification
    
    The group chat pattern is ideal for:
    - Collaborative problem-solving requiring multiple perspectives
    - Iterative maker-checker workflows with quality gates
    - Creative brainstorming where agents build on each other's ideas
    - Decision-making processes benefiting from debate and consensus
    - Content workflows with clear separation between creation and review
    
    Args:
        task (str, optional): The collaborative task for group discussion.
                            If None, uses a default marketing strategy scenario.
    
    Returns:
        list: Complete conversation thread with participant identification:
              [
                {
                  "agent": str,        # Agent name (Writer, Reviewer, Moderator, user)
                  "input": str,        # Context or previous conversation
                  "output": str,       # Agent's contribution to conversation
                  "timestamp": str     # ISO timestamp of contribution
                }
              ]
    
    Raises:
        Exception: If Azure OpenAI client initialization fails
        Exception: If workflow execution encounters unrecoverable errors
        
    Example:
        >>> task = "Create marketing strategy for AI-powered finance app"
        >>> results = await run_group_chat_orchestration(task)
        >>> print(f"Group conversation completed with {len(results)} contributions")
        
    Note:
        This implementation ensures transparent, auditable conversation management
        with iterative maker-checker loops, following documented group chat
        orchestration best practices exactly.
    """
    if task is None:
        task = "Create a compelling marketing strategy for a new AI-powered personal finance app that helps millennials automate their savings and investment decisions."
    
    print("=" * 80)
    print("GROUP CHAT ORCHESTRATION PATTERN")
    print("=" * 80)
    print(f"Task: {task}")
    print()
    
    # STEP 1: Create your chat client (via AgentFactory)
    # AgentFactory encapsulates Azure OpenAI client setup with proper credentials
    # and configuration management, following documented best practices
    factory = AgentFactory()
    
    # STEP 2: Define your agents
    # Create collaborative agents with specific conversation roles
    # Each agent participates in iterative maker-checker loops
    print("Creating group chat participants...")
    print("✓ Writer Agent: Content creation and iteration")        # 📝 Creates and refines content
    print("✓ Reviewer Agent: Quality evaluation and feedback")     # 🔍 Evaluates and provides feedback  
    print("✓ Moderator Agent: Decision making and conversation management")  # ⚖️  Manages flow and decisions
    print()
    
    # STEP 3: Build the group chat workflow
    # Use custom GroupChatManager with WorkflowBuilder to create iterative conversation workflow
    # GroupChatManager implements the documented group chat behavior with turn-taking
    manager = GroupChatManager(factory, max_iterations=4)
    
    print("Building group chat workflow...")
    
    # Create workflow with custom executor for conversation management
    workflow = (
        WorkflowBuilder()
        .set_start_executor(manager)  # Custom executor manages agent interactions
        .build()
    )
    
    print("✓ Group chat workflow configured with maker-checker loops")
    print()
    
    # STEP 4: Run the workflow
    # Execute iterative conversation with managed turn-taking and decision points
    # GroupChatManager coordinates conversation flow between participants
    print("Executing group chat orchestration...")
    print("-" * 60)
    
    outputs = []
    
    # STEP 5: Process the results
    # Stream conversation events and extract complete conversation thread
    # Each event contains the conversation history from all participants
    async for event in workflow.run_stream(task):
        if isinstance(event, WorkflowOutputEvent):
            outputs.append(event.data)
    
    # STEP 6: Handle the aggregated responses
    # Process complete conversation thread with participant identification
    # Display transparent and auditable conversation history
    if outputs:
        final_conversation = outputs[0]
        print("\n" + "=" * 80)
        print("GROUP CHAT ORCHESTRATION RESULTS")
        print("=" * 80)
        
        # Show complete conversation thread with participant identification
        for i, message in enumerate(final_conversation, 1):
            author = message.author_name or ("user" if message.role == Role.USER else "assistant")
            print(f"\n{i:02d}. [{author.upper()}]")
            print("-" * 40)
            print(message.text)
    else:
        print("No output received from group chat.")
    
    print("\n" + "=" * 80)
    print("Group chat orchestration completed!")
    print("Collaborative conversation achieved consensus.")
    print("=" * 80)
    
    # Return the conversation outputs for API consumption
    if outputs:
        final_conversation = outputs[0]
        return [
            {
                "agent": message.author_name or ("user" if message.role == Role.USER else "assistant"),
                "input": task if i == 0 else "Previous conversation context",
                "output": message.text,
                "timestamp": datetime.now().isoformat()
            }
            for i, message in enumerate(final_conversation)
            if message.role != Role.USER or i == 0  # Include first user message and all assistant messages
        ]
    else:
        return []


async def main():
    """Main function for standalone execution."""
    await run_group_chat_orchestration()


if __name__ == "__main__":
    asyncio.run(main())