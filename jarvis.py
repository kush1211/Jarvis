"""Jarvis terminal chat. Run: .venv\\Scripts\\python jarvis.py"""
import openai

import config
import llm


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

        messages.append({"role": "user", "content": user_text})
        try:
            answer = llm.chat(messages)
        except openai.APIConnectionError:  # server down, wrong port, or timeout
            messages.pop()  # history only keeps complete question+answer pairs
            print(f"Can't reach llama-server at {config.BASE_URL}. Is it running?")
            continue
        except openai.APIError as e:  # server answered, but with an error
            messages.pop()
            print(f"LLM error: {e}")
            continue
        except KeyboardInterrupt:  # Ctrl+C while waiting for the reply
            messages.pop()
            print("\n(cancelled)")
            continue

        messages.append({"role": "assistant", "content": answer})
        print(f"jarvis> {answer}")


if __name__ == "__main__":
    main()
