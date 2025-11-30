# Context Module

The Context Module provides the core state management system for the Multi-Agent System. It serves as the "Single Source of Truth" for the entire agent execution lifecycle.

## Architecture

The Context follows a **layered architecture** with three distinct layers:

### 1. MetaContext (Static Layer)
Read-only metadata initialized at task start:
- `trace_id`: Unique UUID for request/task execution trace
- `goal`: User's original natural language instruction
- `environment`: Execution environment (dev, prod, test, staging)
- `persona`: Dynamic persona configuration from Vector DB

### 2. RuntimeContext (Dynamic Layer)
State machine that changes during execution:
- `execution_plan`: List of steps with status tracking
- `current_step_index`: Pointer to current execution step
- `blackboard`: Shared memory space for agent communication
- `interrupt_flags`: Flags for handling special conditions

### 3. HistoryContext (Logging Layer)
Chronological logging and memory:
- `action_log`: Time-stamped log of all agent actions
- `short_term_memory`: Chain-of-Thought summaries and key reasoning

## Installation

```bash
pip install pydantic
```

## Quick Start

### Basic Usage

```python
from app.core import Context

# Create a new context
context = Context.create_new(
    goal="Write a blog post about AI technology",
    environment="dev",
    persona={"style": "professional", "avoid_words": ["AI"]}
)

# Add execution steps
step1 = context.runtime.add_step("Research AI trends", "researcher")
step2 = context.runtime.add_step("Write outline", "writer")

# Execute steps
context.runtime.set_step_status(step1, "success")
context.runtime.advance_to_next_step()

# Log actions
context.log_action("researcher", "Completed research", {"articles_found": 15})
```

### Blackboard Communication

```python
# Agent A stores data
context.set_shared_data("user_data", {"name": "John", "age": 30})
context.log_action("web_agent", "Collected user data")

# Agent B reads data
user_data = context.get_shared_data("user_data")
context.log_action("analyzer", "Processed user data", user_data)
```

### Serialization

```python
# Save context state
json_str = context.to_json()

# Restore context state
restored_context = Context.from_json(json_str)
```

## Key Features

### 1. Execution Plan Management
- Step-by-step execution tracking
- Status monitoring (pending, running, success, failed)
- Error handling and result storage

### 2. Agent Communication
- Blackboard pattern for data sharing
- Interrupt flag system for handling special conditions
- Coordinated execution state

### 3. Memory and Logging
- Comprehensive action logging
- Short-term memory for reasoning steps
- Checkpointing for state recovery

### 4. Serialization Support
- JSON serialization/deserialization
- Snapshot creation for debugging
- Context restoration capabilities

## Advanced Usage

### Interrupt Handling

```python
# Set interrupt flags
context.set_interrupt_flag("login_required", True)

# Check for interrupts
if context.get_interrupt_flag("login_required"):
    # Handle login
    context.set_interrupt_flag("login_required", False)
```

### Checkpointing

```python
# Create checkpoint
checkpoint_id = context.create_checkpoint()

# Get snapshot
snapshot = context.create_snapshot(include_history=True)

# Restore from snapshot
context.restore_from_snapshot(snapshot)
```

### Memory Management

```python
# Add reasoning steps to memory
context.add_memory("Initial analysis complete")
context.add_memory("Next step: validate assumptions")

# Access recent actions
recent_actions = context.history.get_recent_actions(limit=5)
```

## API Reference

### Context Class

#### Factory Methods
- `create_new(goal, environment, persona)` - Create new context instance
- `from_json(json_str)` - Restore from JSON string
- `from_dict(data)` - Restore from dictionary

#### Serialization
- `to_json()` - Convert to JSON string
- `to_dict()` - Convert to dictionary

#### Blackboard Methods
- `set_shared_data(key, value)` - Store data
- `get_shared_data(key, default)` - Retrieve data
- `remove_shared_data(key)` - Remove data
- `clear_blackboard()` - Clear all data

#### Logging Methods
- `log_action(agent_name, action, result, duration_ms)` - Log action
- `add_memory(memory_entry)` - Add to short-term memory

#### Interrupt Methods
- `set_interrupt_flag(flag, value)` - Set interrupt flag
- `get_interrupt_flag(flag)` - Get interrupt flag value
- `clear_interrupt_flag(flag)` - Clear interrupt flag

#### Utility Methods
- `create_snapshot(include_history)` - Create state snapshot
- `create_checkpoint()` - Create checkpoint
- `get_execution_summary()` - Get execution summary

### RuntimeContext Class

#### Step Management
- `add_step(description, agent_name)` - Add execution step
- `get_current_step()` - Get current step
- `advance_to_next_step()` - Move to next step
- `set_step_status(step_id, status, error_message, result)` - Update step status

## Examples

See `context_example.py` for comprehensive usage examples including:
- Basic context creation and management
- Runtime state management
- Agent coordination via blackboard
- Interrupt handling
- Memory management and checkpointing
- Serialization and restoration

## Design Principles

1. **Single Source of Truth**: All agents read from and write to the same Context
2. **Layered Architecture**: Clear separation between static, dynamic, and historical data
3. **Type Safety**: Full Pydantic validation and serialization
4. **Agent Coordination**: Built-in support for inter-agent communication
5. **Observability**: Comprehensive logging and state tracking
6. **Recoverability**: Checkpointing and snapshot capabilities

## Performance Considerations

- Context objects are designed to be memory-efficient
- JSON serialization uses Pydantic's optimized serialization
- Blackboard operations are O(1) time complexity
- Action logging grows linearly with execution length

## Error Handling

- All Pydantic validation errors are preserved
- Invalid interrupt flags raise ValueError
- Serialization errors are properly caught and reported
- Step status transitions are validated