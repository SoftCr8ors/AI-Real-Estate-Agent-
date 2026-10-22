"""
LLM client wrapper for multiple providers.
Supports: Gemini, Groq, OpenAI with unified interface.
"""


from sqlalchemy.orm import Session

from app.services.settings_service import get_ai_api_key, get_ai_provider

# ============================================================================
# LLM CLIENT
# ============================================================================

class LLMClient:
    """
    Unified LLM client supporting multiple providers.
    Priority: admin-saved key (database) > environment variable
    """

    def __init__(self, db: Session, provider: str | None = None):
        """
        Initialize LLM client.

        Args:
            db: Database session
            provider: Provider name (gemini/groq/openai) or None for configured default
        """
        self.db = db
        self.provider = provider or get_ai_provider(db)
        self.api_key = get_ai_api_key(db, self.provider)
        self.client = None

        if not self.api_key:
            raise ValueError(
                f"No API key found for provider '{self.provider}'. "
                f"Set it in admin settings or {self.provider.upper()}_API_KEY environment variable."
            )

        self._initialize_client()

    def _initialize_client(self):
        """Initialize provider-specific client."""
        if self.provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel("gemini-2.5-flash")

        elif self.provider == "groq":
            from groq import Groq
            self.client = Groq(api_key=self.api_key)

        elif self.provider == "openai":
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)

        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def generate(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> dict:
        """
        Generate completion with tool calling support.

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: List of tool definitions
            temperature: Sampling temperature
            max_tokens: Max tokens to generate

        Returns:
            Dict with 'content', 'tool_calls', and 'usage'
        """
        if self.provider == "gemini":
            return self._generate_gemini(messages, tools, temperature, max_tokens)
        elif self.provider == "groq":
            return self._generate_groq(messages, tools, temperature, max_tokens)
        elif self.provider == "openai":
            return self._generate_openai(messages, tools, temperature, max_tokens)

    def _generate_gemini(self, messages, tools, temperature, max_tokens):
        """Generate with Gemini."""
        # Convert messages to Gemini format
        chat = self.client.start_chat(history=[])

        # Gemini uses different format for tools
        if tools:
            # Convert OpenAI-style tools to Gemini format
            self._convert_tools_to_gemini(tools)

        # Get last user message
        user_message = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")

        # Generate
        try:
            response = chat.send_message(
                user_message,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
            )

            return {
                "content": response.text,
                "tool_calls": [],  # Gemini tool calling handled differently
                "usage": {"total_tokens": 0},  # Gemini doesn't expose token counts easily
            }
        except Exception:
            raise

    def _generate_groq(self, messages, tools, temperature, max_tokens):
        """Generate with Groq."""
        try:
            completion_params = {
                "model": "openai/gpt-oss-120b",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if tools:
                completion_params["tools"] = tools
                completion_params["tool_choice"] = "auto"

            response = self.client.chat.completions.create(**completion_params)

            message = response.choices[0].message

            tool_calls = []
            if hasattr(message, "tool_calls") and message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                    for tc in message.tool_calls
                ]

            return {
                "content": message.content or "",
                "tool_calls": tool_calls,
                "usage": {
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                },
            }
        except Exception as e:
            if "rate_limit" in str(e).lower():
                raise RateLimitError(f"Groq rate limit exceeded: {e}")
            raise

    def _generate_openai(self, messages, tools, temperature, max_tokens):
        """Generate with OpenAI."""
        try:
            completion_params = {
                "model": "gpt-4o-mini",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if tools:
                completion_params["tools"] = tools
                completion_params["tool_choice"] = "auto"

            response = self.client.chat.completions.create(**completion_params)

            message = response.choices[0].message

            tool_calls = []
            if hasattr(message, "tool_calls") and message.tool_calls:
                tool_calls = [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                    for tc in message.tool_calls
                ]

            return {
                "content": message.content or "",
                "tool_calls": tool_calls,
                "usage": {
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                },
            }
        except Exception as e:
            if "rate_limit" in str(e).lower():
                raise RateLimitError(f"OpenAI rate limit exceeded: {e}")
            raise

    def _convert_tools_to_gemini(self, tools):
        """Convert OpenAI-style tools to Gemini format."""
        # Simplified - Gemini uses different tool format
        # This is a placeholder for proper conversion
        return []


# ============================================================================
# EXCEPTIONS
# ============================================================================

class RateLimitError(Exception):
    """Raised when API rate limit is exceeded."""
    pass
