from enum import Enum

class ProviderType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    GROQ = "groq"
    OPENROUTER="openrouter"