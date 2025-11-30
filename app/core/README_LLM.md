# LLM Service Module

## Overview

The `LLMService` is a structured reasoning engine designed for pure agentic architectures. It ensures that **100% of LLM outputs are valid Pydantic objects**, eliminating the need for raw text parsing in agent systems.

## Key Features

- **Structured Outputs Only**: Every response is a validated Pydantic model
- **Automatic Retries**: Built-in retry logic with exponential backoff
- **Async/Await**: Designed for Python 3.11+ compatibility with `browser-use`
- **Multiple Provider Support**: Works with OpenAI, DeepSeek, Zhipu, and other OpenAI-compatible APIs
- **Health Checking**: Built-in service health validation

## Quick Start

```python
from app.core import LLMService
from pydantic import BaseModel

# Define your structured output model
class AnalysisResult(BaseModel):
    sentiment: str
    confidence: float
    key_points: list[str]

# Initialize the service
llm_service = LLMService()

# Generate structured output
result = await llm_service.generate(
    prompt="Analyze this customer feedback: 'Great product, fast shipping!'",
    response_model=AnalysisResult,
    system_prompt="You are a sentiment analysis expert."
)

# Result is guaranteed to be a valid AnalysisResult instance
print(f"Sentiment: {result.sentiment}")
print(f"Confidence: {result.confidence}")
```

## Configuration

The service automatically reads configuration from environment variables:

- `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, or `ZHIPU_API_KEY`: API key (one required)
- `OPENAI_BASE_URL` or `ZHIPU_MODEL_URL`: Custom API endpoint
- `MODEL_NAME`, `DEEPSEEK_GUI_MODEL_NAME`, or `ZHIPU_GUI_MODEL_NAME`: Model name

## Method Reference

### `generate(prompt, response_model, system_prompt=None, temperature=0.0)`

Generates structured output from the LLM.

**Parameters:**
- `prompt` (str): The main prompt/question
- `response_model` (Type[T]): Pydantic model class for output
- `system_prompt` (Optional[str]): System prompt for behavior guidance
- `temperature` (float): Sampling temperature (0.0 = deterministic)

**Returns:**
- Instance of `response_model` with validated data

**Raises:**
- `ValidationError`: If output cannot be parsed into the model
- `ValueError`: For invalid input parameters
- `Exception`: For API or processing errors

### `health_check()`

Checks if the LLM service is healthy and accessible.

**Returns:**
- Dictionary with health status information

## Example Use Cases

### 1. Media Analysis
```python
class MediaAnalysis(BaseModel):
    title: str
    sentiment: str
    key_topics: list[str]
    engagement_score: float

analysis = await llm_service.generate(
    prompt="Analyze this social media post: 'New AI product launched! 🚀'",
    response_model=MediaAnalysis
)
```

### 2. Decision Making
```python
class Decision(BaseModel):
    action: str
    reasoning: str
    confidence: float
    alternatives: list[str]

decision = await llm_service.generate(
    prompt="Should we launch the feature tomorrow or wait?",
    response_model=Decision,
    system_prompt="You are a product manager making strategic decisions."
)
```

### 3. Creative Writing with Structure
```python
class Story(BaseModel):
    title: str
    genre: str
    protagonist: str
    plot_summary: str
    themes: list[str]

story = await llm_service.generate(
    prompt="Write a micro-story about an AI discovering emotions",
    response_model=Story,
    temperature=0.8
)
```

## Error Handling

The service includes comprehensive error handling with automatic retries:

- **Validation Errors**: Retries automatically up to 3 times
- **API Errors**: Handles timeouts, rate limits, and connectivity issues
- **Input Validation**: Validates parameters before making API calls

## Testing

Run the test script to verify functionality:

```bash
python test_llm_module.py
```

This will test:
- Service initialization
- Health check
- Structured analysis generation
- Creative structured output

## Architecture Notes

This module follows the pure agentic architecture principles:

1. **No Raw Text Chat**: All interactions return structured objects
2. **Metadata-First**: Even creative outputs include metadata
3. **Type Safety**: Guaranteed return types through Pydantic validation
4. **Async-First**: Designed for event-loop integration
5. **Retry Logic**: Robust error handling for production use

The service can be safely integrated into agent systems where predictable, structured communication with the LLM is essential.