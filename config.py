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

# Apps open_app may start: the name the model sends -> the exe we run. Only these names work.
APPS = {
    "notepad": r"C:\Windows\System32\notepad.exe",
    "calculator": r"C:\Windows\System32\calc.exe",
    "chrome": r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "vscode": os.path.join(os.environ["LOCALAPPDATA"], r"Programs\Microsoft VS Code\Code.exe"),
}

# Model calls per user message. Stops a confused model from calling tools forever.
MAX_TOOL_ROUNDS = 5
