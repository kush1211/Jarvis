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
- [ ] Kush can explain the loop and the allowlist
