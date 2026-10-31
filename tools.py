"""Tools the model can ask for. The model only picks a tool and its arguments; this file decides what runs."""
import datetime
import json
import os
import subprocess

import config

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tool_calls.log")

# Sent with every request. The chat template turns this into text the model reads.
# The enum lists the allowed names, so the model knows what it can open.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Open an application on the laptop.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "enum": list(config.APPS), "description": "Which app to open."}
                },
                "required": ["name"],
            },
        },
    }
]


def open_app(name: str) -> str:
    # The enum is only a hint to the model; this check is the real allowlist.
    if name not in config.APPS:
        return f"Error: unknown app '{name}'. Allowed: {', '.join(config.APPS)}"
    # A list (not a string) and no shell: the exe path comes from APPS, never from the model.
    subprocess.Popen([config.APPS[name]])
    return f"Opened {name}"


FUNCTIONS = {"open_app": open_app}


def print_call(name: str, arguments: str, result: str):
    print(f"[tool] {name}({arguments}) -> {result}")


# Called after every tool call. The terminal prints it; app.py swaps in its own function to show a row.
on_call = print_call


def run_tool(name: str, arguments: str) -> str:
    """Run one tool call and return the result text for the model. Prints and logs every call.
    Mistakes come back as "Error: ..." text, so the model can read them and tell the user."""
    if name not in FUNCTIONS:
        result = f"Error: unknown tool '{name}'. Available: {', '.join(FUNCTIONS)}"
    else:
        try:
            result = FUNCTIONS[name](**json.loads(arguments))  # arguments arrive as a JSON string
        except (json.JSONDecodeError, TypeError) as e:  # broken JSON, or wrong/missing argument names
            result = f"Error: bad arguments for {name}: {e}"
        except OSError as e:  # the exe is missing or failed to start
            result = f"Error: could not start: {e}"

    on_call(name, arguments, result)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} [tool] {name}({arguments}) -> {result}\n")
    return result
