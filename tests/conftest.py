import os
import pytest

@pytest.fixture
def openai_key():
    return os.getenv("OPENAI_API_KEY")

@pytest.fixture
def groq_key():
    return os.getenv("GROQ_API_KEY")
