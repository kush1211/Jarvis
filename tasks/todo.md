# Phase 1 — Todo

- [x] Task 0: Probe server raw responses (thinking field, usage, stream chunks) → findings in plan.md
- [x] Task 1: Env + multi-turn non-streaming chat (requirements, .env.example, .gitignore, config.py, llm.chat, jarvis.py loop)
- [x] Task 2: /exit, /clear, Ctrl+C/EOF, friendly connection + API errors

## Checkpoint A
- [x] Multi-turn memory, commands, server-down error all work
- [x] Code reviewed together

- [~] Task 3: SKIPPED (2026-10-29, Kush's call). Thinking is already hidden and history stores only the answer; SHOW_THINKING not needed

## Deferred (2026-10-29, Kush's call): extras, revisit after tools + a basic front end
- [ ] Task 4: Streaming (stream_chat generator, STREAM setting, errors mid-stream)
- [ ] Task 5: Token usage line + trim_history (75% of CONTEXT_SIZE) + tests/test_jarvis.py
- [ ] Task 6: README with exact PowerShell commands

# Phase 2: Todo (tool calling, open_app)

- [x] Task 7: Probe raw tool-call responses (curl) → "Phase 2 server findings" in plan.md
- [x] Task 8: open_app end to end (tools.py, APPS allowlist, llm.chat(tools), loop + rollback + log)
- [x] Task 9: Bad calls (unknown app/tool, bad JSON), round cap, Ctrl+C rollback, tests/test_tools.py

## Checkpoint D (Phase 2 done)
- [x] All checks pass, seen by Kush
- [x] Kush can explain the loop and the allowlist (closed by Kush, 2026-10-29)

# Front end: Todo (basic window)

- [x] Task F1: Basic PySide6 window, end to end (`app.py`, `jarvis.ask`), checked by Kush
- [x] Task F2: Quiet Glass chat, normal flow (B1 + Option B) · M · deps F1
- [x] Task F3: Working state + tool rows (B2), `tools.on_call` hook · S · deps F2
- [x] Task F4: Error state + Try again (B5), `ask` returns (text, ok) · S · deps F2
- [x] Task F5: Dark native title bar · XS · deps F2

## Checkpoint G
- [x] Design port checked by Kush against the boards; pytest + jarvis.py still fine

# Animations: Todo (subtle)

- [x] Task A1: Living orb (breathing, ripples, grey fade) · S
- [x] Task A2: First-message orb shrink transition · M · deps A1
- [x] Task A3: Chat motion (fade/slide, typing dots, tool rows, smooth scroll) · M
- [x] Task A4: Controls (send hover/press, input glow, Try again hover) · S

## Checkpoint H
- [x] Checked by Kush on the live server; pytest + jarvis.py still fine
