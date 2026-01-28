"""
LLM Service Module for Pure Agentic Architecture

This module implements a structured reasoning engine that wraps LLM APIs
and ensures 100% of outputs are valid Pydantic objects.
"""

import os
import json
from typing import Type, TypeVar, Optional
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, retry_if_exception_type, wait_exponential
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from app.core.config import llm_settings

# Generic type for structured output
T = TypeVar('T', bound=BaseModel)


class LLMService:
    """
    Structured Reasoning Engine for Pure Agentic Architecture

    This service provides asynchronous LLM interaction with guaranteed
    structured output using Pydantic models.
    """

    def __init__(self):
        """Initialize the LLM service with configuration from config.py or environment variables."""
        # Determine which API key is being used
        if llm_settings.OPENAI_API_KEY:
            self.api_key = llm_settings.OPENAI_API_KEY
            self.base_url = llm_settings.OPENAI_BASE_URL
            self.model_name = llm_settings.OPENAI_MODEL_NAME
            self.supports_structured_output = True
        elif llm_settings.DEEPSEEK_API_KEY:
            self.api_key = llm_settings.DEEPSEEK_API_KEY
            self.base_url = llm_settings.DEEPSEEK_BASE_URL
            self.model_name = llm_settings.DEEPSEEK_MODEL_NAME
            self.supports_structured_output = False
        elif llm_settings.ZHIPU_API_KEY:
            self.api_key = llm_settings.ZHIPU_API_KEY
            self.base_url = llm_settings.ZHIPU_MODEL_URL
            self.model_name = llm_settings.ZHIPU_MODEL_NAME
            self.supports_structured_output = False
        elif os.getenv('OPENAI_API_KEY'):
            self.api_key = os.getenv('OPENAI_API_KEY')
            self.base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
            self.model_name = os.getenv('MODEL_NAME', 'gpt-4o')
            self.supports_structured_output = True
        elif os.getenv('DEEPSEEK_API_KEY'):
            self.api_key = os.getenv('DEEPSEEK_API_KEY')
            self.base_url = os.getenv('DEEPSEEK_MODEL_URL', 'https://api.deepseek.com')
            self.model_name = os.getenv('DEEPSEEK_GUI_MODEL_NAME', 'deepseek-chat')
            self.supports_structured_output = False
        elif os.getenv('ZHIPU_API_KEY'):
            self.api_key = os.getenv('ZHIPU_API_KEY')
            self.base_url = os.getenv('ZHIPU_MODEL_URL', 'https://open.bigmodel.cn/api/paas/v4/')
            self.model_name = os.getenv('ZHIPU_GUI_MODEL_NAME', 'glm-4.5v')
            self.supports_structured_output = False
        else:
            raise ValueError("No API key found. Please set OPENAI_API_KEY, DEEPSEEK_API_KEY, or ZHIPU_API_KEY in config.py or environment.")

        # Allow manual overrides
        self.base_url = os.getenv('OPENAI_BASE_URL') or self.base_url
        self.model_name = os.getenv('MODEL_NAME') or self.model_name

        # Initialize the LangChain chat model
        self._model: BaseChatModel = ChatOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model_name,
            temperature=0.0,
            max_tokens=None,
            timeout=60
        )

    @property
    def model(self) -> BaseChatModel:
        """Get the underlying LangChain model instance."""
        return self._model

    def _create_json_schema_prompt(self, response_model: Type[T]) -> str:
        """Create a prompt that instructs the LLM to output JSON matching the schema."""
        schema = response_model.model_json_schema()

        return f"""
Please respond with a valid JSON object that strictly follows this schema:

{json.dumps(schema, indent=2, ensure_ascii=False)}

Requirements:
1. Your response must be ONLY the JSON object (no markdown, no code blocks, no explanations)
2. All required fields must be included
3. Values must match the specified types and constraints
4. Do not add any additional fields beyond the schema

Example format:
{{"field1": "value1", "field2": ["item1", "item2"]}}
"""

    @retry(
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((ValidationError, ValueError, Exception)),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def generate(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.0
    ) -> T:
        """
        Generate structured output from the LLM.

        Args:
            prompt: The main prompt/question for the LLM
            response_model: Pydantic model class for structured output
            system_prompt: Optional system prompt to guide the LLM behavior
            temperature: Sampling temperature (0.0 = deterministic, higher = more creative)

        Returns:
            An instance of the response_model with validated data

        Raises:
            ValidationError: If the LLM output cannot be parsed into the response model
            ValueError: If there are issues with the input parameters
            Exception: For other API or processing errors
        """
        # Validate input parameters
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        if not issubclass(response_model, BaseModel):
            raise ValueError("response_model must be a Pydantic BaseModel subclass")

        # Update model temperature if different from default
        if temperature != self._model.temperature:
            self._model.temperature = temperature

        try:
            if self.supports_structured_output:
                # Use native structured output (OpenAI)
                return await self._generate_with_structured_output(prompt, response_model, system_prompt, temperature)
            else:
                # Use manual JSON parsing (DeepSeek, Zhipu, etc.)
                return await self._generate_with_json_parsing(prompt, response_model, system_prompt, temperature)

        except Exception as e:
            # Handle API errors, timeouts, etc.
            if "API" in str(e).upper() or "timeout" in str(e).lower():
                raise Exception(f"LLM API error: {str(e)}") from e
            else:
                # For other exceptions, let them be handled by the retry decorator
                raise

    async def _generate_with_structured_output(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str],
        temperature: float
    ) -> T:
        """Generate using native structured output support."""
        # Construct the message payload
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        # Create structured output model
        structured_model = self._model.with_structured_output(response_model)

        # Invoke the model with structured output
        result = await structured_model.ainvoke(messages)

        # Validate that we got the expected type
        if not isinstance(result, response_model):
            raise ValidationError(f"Expected {response_model.__name__}, got {type(result).__name__}")

        return result

    async def _generate_with_json_parsing(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str],
        temperature: float
    ) -> T:
        """Generate using manual JSON parsing for APIs without structured output support."""
        # Create enhanced prompt with JSON schema instructions
        json_schema_prompt = self._create_json_schema_prompt(response_model)
        enhanced_prompt = f"{prompt}\n\n{json_schema_prompt}"

        # Construct the message payload
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=enhanced_prompt))

        # Invoke the model for text response
        response = await self._model.ainvoke(messages)

        # Extract content from response
        content = response.content.strip() if hasattr(response, 'content') else str(response).strip()

        # Try to extract JSON from the response
        try:
            # First, try to find JSON in markdown code blocks
            if '```json' in content:
                json_start = content.find('```json') + 7
                json_end = content.find('```', json_start)
                if json_end > json_start:
                    json_str = content[json_start:json_end].strip()
                else:
                    json_str = content[json_start:].strip()
            elif '```' in content:
                json_start = content.find('```') + 3
                json_end = content.find('```', json_start)
                if json_end > json_start:
                    json_str = content[json_start:json_end].strip()
                else:
                    json_str = content[json_start:].strip()
            else:
                # Assume the entire response is JSON
                json_str = content

            # Parse JSON
            try:
                json_data = json.loads(json_str)
            except json.JSONDecodeError:
                # Try to fix common JSON issues
                cleaned_json = json_str.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                json_data = json.loads(cleaned_json)

            # Validate and create Pydantic model
            result = response_model.model_validate(json_data)
            return result

        except json.JSONDecodeError as e:
            raise ValidationError(f"Failed to parse JSON from LLM response: {str(e)}\nResponse content: {content[:200]}...") from e
        except Exception as e:
            raise ValidationError(f"Failed to validate LLM output as {response_model.__name__}: {str(e)}\nJSON data: {json_data if 'json_data' in locals() else 'N/A'}") from e

    async def health_check(self) -> dict:
        """
        Check if the LLM service is healthy and accessible.

        Returns:
            Dictionary containing health status information
        """
        try:
            class TestResponse(BaseModel):
                status: str
                model: str

            # Simple start call with a very specific prompt
            result = await self.generate(
                prompt="Respond with a JSON object containing: status='ok' and model name",
                response_model=TestResponse,
                system_prompt="You are a health check system. Always respond with valid JSON.",
                temperature=0.0
            )

            return {
                "status": "healthy",
                "model": self.model_name,
                "base_url": self.base_url,
                "supports_structured_output": self.supports_structured_output,
                "test_response": result.model_dump()
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "model": self.model_name,
                "base_url": self.base_url,
                "supports_structured_output": self.supports_structured_output,
                "error": str(e)
            }


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    # Example Pydantic model for testing
    class TestPoem(BaseModel):
        title: str
        verses: list[str]
        sentiment: str

    async def test_llm_service():
        """Test the LLM service with a simple example."""
        try:
            llm_service = LLMService()

            # Health check
            health = await llm_service.health_check()
            print("Health check:", health)

            # Test structured generation
            poem = await llm_service.generate(
                prompt="Write a short haiku about artificial intelligence",
                response_model=TestPoem,
                system_prompt="You are a creative poet who writes concise, meaningful poems."
            )

            print("Generated poem:")
            print(f"Title: {poem.title}")
            print(f"Verses: {poem.verses}")
            print(f"Sentiment: {poem.sentiment}")

        except Exception as e:
            print(f"Error testing LLM service: {e}")

    # Run start if executed directly
    asyncio.run(test_llm_service())