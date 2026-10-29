"""Jarvis terminal chat. Run: .venv\\Scripts\\python jarvis.py"""
import config
import llm


def main():
    # The server remembers nothing between requests: this list IS the conversation,
    # and we send all of it every turn.
    messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]
    print(f"Jarvis ready ({config.BASE_URL}). Ctrl+C to quit.")

    while True:
        user_text = input("\nyou> ").strip()
        if not user_text:
            continue
        messages.append({"role": "user", "content": user_text})
        answer = llm.chat(messages)
        messages.append({"role": "assistant", "content": answer})
        print(f"jarvis> {answer}")


if __name__ == "__main__":
    main()
