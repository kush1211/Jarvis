"""All settings in one place. Values come from .env; defaults match a local llama-server."""
import os

from dotenv import load_dotenv

load_dotenv()  # copies KEY=value lines from .env into os.environ (real env vars win)

BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8080/v1")
MODEL = os.getenv("LLM_MODEL", "gemma-4-e2b")
API_KEY = os.getenv("LLM_API_KEY", "sk-no-key-needed")

SYSTEM_PROMPT = (
    "You are Jarvis, a helpful assistant running locally on Kush's Windows laptop. "
    "Give short, direct answers."
)
