# Jarvis

A local AI assistant on Kush's Windows laptop: a plain-Python chat (PySide6 window + terminal client) that talks to llama-server (Gemma 4 E2B) and runs tools for it. A learning project: Kush wants to understand every file.

- Vision, setup, roadmap, safety rules: `PROJECT_CONTEXT.md` (read only the section you need)
- Current plan and progress: `tasks/plan.md`, `tasks/todo.md`

## Status (2026-10-31)
- Phase 1 (chat client) and Phase 2 (tool calling, `open_app`) are done and pushed.
- Front end done: `app.py`, a PySide6 window in Kush's "Quiet Glass" design (states: first open, chat, working + tool rows, error + Try again). Kush doesn't study the front-end code; keep core changes readable.
- Deferred extras: streaming, history trimming, show-thinking, README (see todo.md). Kush wants tools and a basic front end first.
- Next: Phase 3 (more system tools + confirmation for tools that change things). Not planned yet.

## Commands (PowerShell, from the project root)
- Run (starts llama-server if needed, then Jarvis): `.\start.ps1`
- Window: `.venv\Scripts\python app.py` (server must be running)
- Tests: `.venv\Scripts\python -m pytest`
- Install deps: `uv pip install -r requirements.txt` (Python is not on PATH; the venv was made with `uv venv --python 3.12`)
- Server health: `curl http://127.0.0.1:8080/health` → `{"status":"ok"}`

## Files
- `config.py`: all settings (`.env` values, system prompt, `APPS` allowlist, `MAX_TOOL_ROUNDS`)
- `llm.py`: one request to the model (`chat(messages, tools)` returns the message). Knows nothing about the loop
- `tools.py`: tool schemas (`TOOLS`), functions (`FUNCTIONS`), `run_tool` (errors become `"Error: ..."` text, every call is printed and logged to `tool_calls.log`)
- `jarvis.py`: terminal chat loop, commands, `reply()` tool loop, `ask()` = one turn with rollback, returns `(text, ok)`
- `app.py`: the window. Worker `QThread` calls `jarvis.ask`; `tools.on_call` hook shows tool rows
- `start.ps1`: launcher (still runs the terminal client). `tests/`: bad tool calls, failed-turn rollback

## Adding a tool
One schema in `TOOLS`, one function, one entry in `FUNCTIONS`. The loop doesn't change. Anything not in an allowlist is checked in code (an `enum` in the schema is only a hint to the model).

## Server facts (llama.cpp b11963, `--jinja`)
- Thinking arrives in `reasoning_content`; `content` is clean. Never store thinking in history.
- `tool_calls[].function.arguments` is a JSON string. `content` is `""` on a tool call.
- Context is 4096 tokens, shared by history and tool schemas.
- If tool calls look malformed: update llama.cpp first (Gemma 4 launch bugs).

## Rules
- Safety (PROJECT_CONTEXT.md §9): the model only proposes; code executes via defined tools; allowlists; confirm anything that changes/sends/deletes; never run model output in a shell; log and cap tool calls; secrets only in `.env`.
- Plain Python, no frameworks (no LangChain etc.). Fewest files, smallest diff.
- Working style: plan → Kush's OK → code → Kush runs the tests by hand. Slow pace, one step per message. Kush already knows tool calling and streaming.
- Commit or push only when Kush asks.
