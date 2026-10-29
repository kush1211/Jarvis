"""Talks to the LLM over the OpenAI-compatible API. Knows nothing about the chat loop."""
from openai import OpenAI

import config

# max_retries=0: the library retries twice by default (with delays). Locally, a refused
# connection means the server isn't running, so report it right away.
client = OpenAI(base_url=config.BASE_URL, api_key=config.API_KEY, max_retries=0)


def chat(messages: list[dict]) -> str:
    """Send the whole conversation, return the assistant's answer text."""
    response = client.chat.completions.create(model=config.MODEL, messages=messages)
    return response.choices[0].message.content
