"""Talks to the LLM over the OpenAI-compatible API. Knows nothing about the chat loop."""
from openai import OpenAI

import config

# max_retries=0: the library retries twice by default (with delays). Locally, a refused
# connection means the server isn't running, so report it right away.

client = OpenAI(base_url=config.BASE_URL, api_key=config.API_KEY, max_retries=0)


def chat(messages: list[dict], tools: list[dict]):
    """Send the whole conversation and the tools the model may call. Returns the assistant message:
    either text in .content, or tool requests in .tool_calls."""
    response = client.chat.completions.create(model=config.MODEL, messages=messages, tools=tools)
    return response.choices[0].message
