"""Jarvis terminal chat. Run: .venv\\Scripts\\python jarvis.py (the window version is app.py)"""
import openai

import config
import llm
import tools


def reply(messages: list[dict]) -> str:
    """Ask the model, run any tools it requests, send the results back, repeat until it answers
    in text. Every step is added to messages, because the model needs it to write its answer."""
    for _ in range(config.MAX_TOOL_ROUNDS):
        message = llm.chat(messages, tools.TOOLS)
        if not message.tool_calls:
            return message.content

        # The model's request goes into history first, then one result per call, linked by id.
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [call.model_dump() for call in message.tool_calls],
        })
        for call in message.tool_calls:
            result = tools.run_tool(call.function.name, call.function.arguments)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

    return f"(Stopped: more than {config.MAX_TOOL_ROUNDS} tool rounds for one message.)"


def ask(messages: list[dict], user_text: str) -> tuple[str, bool]:
    """One full turn: add the user's text, get the answer, keep both in history.
    Returns (answer, True), or (friendly error line, False). Used by the terminal and the window."""
    # On failure, cut history back to here: one turn can add several messages (tool calls
    # and results), and history must only keep complete turns.
    turn_start = len(messages)
    messages.append({"role": "user", "content": user_text})
    try:
        answer = reply(messages)
    except openai.APIConnectionError:  # server down, wrong port, or timeout
        del messages[turn_start:]
        return f"Can't reach llama-server at {config.BASE_URL}. Is it running?", False
    except openai.APIError as e:  # server answered, but with an error
        del messages[turn_start:]
        return f"LLM error: {e}", False
    except KeyboardInterrupt:  # Ctrl+C while waiting for the reply (terminal only)
        del messages[turn_start:]
        return "(cancelled)", False

    messages.append({"role": "assistant", "content": answer})
    return answer, True


def main():
    # The server remembers nothing between requests: this list IS the conversation,
    # and we send all of it every turn.
    messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]
    print(f"Jarvis ready ({config.BASE_URL}). /clear to reset, /exit or Ctrl+C to quit.")

    while True:
        try:
            user_text = input("\nyou> ").strip()
        except (KeyboardInterrupt, EOFError):  # Ctrl+C at the prompt, or input ran out
            print("\nBye.")
            break

        if not user_text:
            continue

        # Commands are handled here and never sent to the model.
        if user_text == "/exit":
            print("Bye.")
            break
        if user_text == "/clear":
            messages = messages[:1]  # keep only the system prompt
            print("History cleared.")
            continue
        if user_text.startswith("/"):
            print("Commands: /clear, /exit")
            continue

        text, _ok = ask(messages, user_text)
        print(f"jarvis> {text}")


if __name__ == "__main__":
    main()
