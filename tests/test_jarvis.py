"""A failed turn must report ok=False and leave history as it was. Run: .venv\\Scripts\\python -m pytest"""
import openai

import jarvis
import llm


def test_server_down_rolls_back(monkeypatch):
    def down(messages, tools):
        # __new__ skips the constructor, which wants an HTTP request object we don't need here
        raise openai.APIConnectionError.__new__(openai.APIConnectionError)

    monkeypatch.setattr(llm, "chat", down)
    messages = [{"role": "system", "content": "sys"}]
    text, ok = jarvis.ask(messages, "hi")
    assert not ok
    assert text.startswith("Can't reach llama-server")
    assert messages == [{"role": "system", "content": "sys"}]
