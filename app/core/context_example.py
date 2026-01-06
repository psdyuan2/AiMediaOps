"""
Context Module Usage Examples.

This file demonstrates how to use the Context module in various scenarios
including basic usage, agent coordination, and state management.
"""

import json
import time
from datetime import datetime
from context import Context, StepStatus


def basic_context_usage_example():
    """Basic Context creation and usage example."""
    print("=== Basic Context Usage Example ===")

    # Create a new context with factory method
    context = Context.create_new(
        goal="Write a blog post about AI technology",
        environment="dev",
        persona={"style": "professional", "avoid_words": ["AI"]}
    )

    print(f"Created context: {context}")
    print(f"Trace ID: {context.meta.trace_id}")
    print(f"Goal: {context.meta.goal}")
    print(f"Environment: {context.meta.environment}")
    print(f"Persona: {context.meta.persona}")

    # Add execution plan steps
    step1_id = context.runtime.add_step("Research AI technology trends", "researcher")
    step2_id = context.runtime.add_step("Write blog outline", "writer")
    step3_id = context.runtime.add_step("Generate blog content", "writer")
    step4_id = context.runtime.add_step("Review and edit", "editor")

    print(f"\nAdded {len(context.runtime.execution_plan)} steps to execution plan")

    # Display execution summary
    summary = context.get_execution_summary()
    print(f"\nExecution Summary:")
    print(json.dumps(summary, indent=2, default=str))


def runtime_management_example():
    """Runtime state management example."""
    print("\n=== Runtime Management Example ===")

    context = Context.create_new("Analyze website performance")

    # Add some steps
    steps = [
        ("Navigate to website", "web_agent"),
        ("Measure load times", "analyzer"),
        ("Generate report", "reporter")
    ]

    step_ids = []
    for description, agent in steps:
        step_id = context.runtime.add_step(description, agent)
        step_ids.append(step_id)

    # Simulate step execution
    for i, step_id in enumerate(step_ids):
        print(f"\n--- Step {i+1} ---")

        # Start step
        context.runtime.set_step_status(step_id, "running")
        current_step = context.runtime.get_current_step()
        print(f"Starting: {current_step.description}")

        # Simulate work
        time.sleep(0.1)

        # Complete step
        result = {"output": f"Step {i+1} completed successfully", "metrics": {"time": 0.1}}
        context.runtime.set_step_status(step_id, "success", result=result)

        # Log action
        context.log_action(
            agent_name=current_step.agent_name,
            action=current_step.description,
            result=result,
            duration_ms=100
        )

        print(f"Completed: {current_step.description}")

        # Move to next step
        if not context.runtime.advance_to_next_step():
            break

    # Mark execution as completed
    context.runtime.is_completed = True

    # Show final summary
    summary = context.get_execution_summary()
    print(f"\nFinal Summary:")
    print(json.dumps(summary, indent=2, default=str))


def blackboard_communication_example():
    """Blackboard data sharing example."""
    print("\n=== Blackboard Communication Example ===")

    context = Context.create_new("Process customer data")

    # Web Agent collects data
    web_data = {
        "customer_name": "John Doe",
        "email": "john@example.com",
        "preferences": ["tech", "business"]
    }
    context.set_shared_data("customer_info", web_data)
    context.log_action("web_agent", "Collected customer information", web_data)

    print(f"Web Agent stored: {context.get_shared_data('customer_info')}")

    # Analyzer Agent processes data
    customer_info = context.get_shared_data("customer_info")
    analysis_result = {
        "customer_segment": "premium",
        "engagement_score": 85,
        "recommendations": ["tech_news", "business_insights"]
    }
    context.set_shared_data("analysis_result", analysis_result)
    context.log_action("analyzer", "Analyzed customer data", analysis_result)

    print(f"Analyzer Agent stored: {context.get_shared_data('analysis_result')}")

    # Reporter Agent uses both data sources
    combined_data = {
        "customer": context.get_shared_data("customer_info"),
        "analysis": context.get_shared_data("analysis_result"),
        "report_generated_at": datetime.now().isoformat()
    }
    context.set_shared_data("final_report", combined_data)
    context.log_action("reporter", "Generated final report", combined_data)

    print(f"Final Report: {json.dumps(combined_data, indent=2)}")


def interrupt_handling_example():
    """Interrupt flag handling example."""
    print("\n=== Interrupt Handling Example ===")

    context = Context.create_new("Login to website and extract data")

    # Set up interrupt flags
    context.set_interrupt_flag("login_required", False)
    context.set_interrupt_flag("captcha_detected", False)

    # Simulate login process
    print("Attempting to login...")
    context.log_action("web_agent", "Navigate to login page")

    # Simulate login failure
    context.set_interrupt_flag("login_required", True)
    context.log_action("web_agent", "Login failed - credentials required")

    if context.get_interrupt_flag("login_required"):
        print("Login required! Handling interrupt...")
        # Simulate credential input
        context.set_interrupt_flag("login_required", False)
        context.log_action("web_agent", "Credentials provided, retrying login")

    # Simulate CAPTCHA detection
    context.set_interrupt_flag("captcha_detected", True)
    if context.get_interrupt_flag("captcha_detected"):
        print("CAPTCHA detected! Handling interrupt...")
        context.set_interrupt_flag("captcha_detected", False)
        context.log_action("web_agent", "CAPTCHA solved")

    print("Login process completed successfully")


def memory_and_checkpoint_example():
    """Memory management and checkpointing example."""
    print("\n=== Memory and Checkpoint Example ===")

    context = Context.create_new("Complex multi-step task")

    # Add reasoning steps to memory
    context.add_memory("Initial goal analysis: Need to break down into smaller sub-tasks")
    context.add_memory("Step 1: Data collection is critical first")
    context.add_memory("Step 2: Processing requires validation")
    context.add_memory("Step 3: Output formatting depends on data quality")

    print(f"Memory entries: {len(context.history.short_term_memory)}")
    for i, memory in enumerate(context.history.short_term_memory, 1):
        print(f"  {i}. {memory}")

    # Create checkpoint
    checkpoint_id = context.create_checkpoint()
    print(f"\nCreated checkpoint: {checkpoint_id}")
    print(f"Checkpoint data available in blackboard: checkpoint_{checkpoint_id}")

    # Add more actions after checkpoint
    context.log_action("processor", "Processing data", {"records": 150})
    context.log_action("validator", "Validating results", {"valid": 148, "invalid": 2})

    # Create snapshot
    snapshot = context.create_snapshot()
    print(f"\nCreated snapshot with {len(snapshot)} keys")
    print(f"Snapshot includes history: {'history' in snapshot}")

    # Get recent actions
    recent_actions = context.history.get_recent_actions(limit=3)
    print(f"\nRecent actions ({len(recent_actions)}):")
    for action in recent_actions:
        print(f"  - {action.agent_name}: {action.action}")


def serialization_example():
    """Context serialization and restoration example."""
    print("\n=== Serialization Example ===")

    # Create context with data
    original_context = Context.create_new(
        goal="Serialize and restore context",
        environment="start"
    )

    # Add some data
    original_context.runtime.add_step("Test serialization", "test_agent")
    original_context.set_shared_data("test_key", "test_value")
    original_context.log_action("test_agent", "Testing serialization")
    original_context.add_memory("Test memory entry")

    # Serialize to JSON
    json_str = original_context.to_json()
    print(f"Serialized context length: {len(json_str)} characters")

    # Restore from JSON
    restored_context = Context.from_json(json_str)
    print(f"Restored context trace ID: {restored_context.meta.trace_id}")
    print(f"Trace IDs match: {original_context.meta.trace_id == restored_context.meta.trace_id}")

    # Verify data integrity
    print(f"Shared data restored: {restored_context.get_shared_data('test_key')}")
    print(f"Action log count: {len(restored_context.history.action_log)}")
    print(f"Memory entries: {len(restored_context.history.short_term_memory)}")


def main():
    """Run all context usage examples."""
    print("Context Module Usage Examples")
    print("=" * 50)

    basic_context_usage_example()
    runtime_management_example()
    blackboard_communication_example()
    interrupt_handling_example()
    memory_and_checkpoint_example()
    serialization_example()

    print("\n" + "=" * 50)
    print("All examples completed successfully!")


if __name__ == "__main__":
    main()