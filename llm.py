"""Talks to the LLM over the OpenAI-compatible API. Knows nothing about the chat loop."""
from openai import OpenAI

import config

client = OpenAI(base_url=config.BASE_URL, api_key=config.API_KEY)


def chat(messages: list[dict]) -> str:
    """Send the whole conversation, return the assistant's answer text."""
    response = client.chat.completions.create(model=config.MODEL, messages=messages)
    return response.choices[0].message.content
