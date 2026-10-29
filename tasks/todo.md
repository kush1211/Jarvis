# Phase 1 — Todo

- [x] Task 0: Probe server raw responses (thinking field, usage, stream chunks) → findings in plan.md
- [x] Task 1: Env + multi-turn non-streaming chat (requirements, .env.example, .gitignore, config.py, llm.chat, jarvis.py loop)
- [x] Task 2: /exit, /clear, Ctrl+C/EOF, friendly connection + API errors

## Checkpoint A
- [x] Multi-turn memory, commands, server-down error all work
- [ ] Code reviewed together

- [ ] Task 3: Thinking hidden by default, SHOW_THINKING=true shows it, history stores answer only
- [ ] Task 4: Streaming (stream_chat generator, STREAM setting, errors mid-stream)

## Checkpoint B
- [ ] Both modes work, compared, llm.py reviewed

- [ ] Task 5: Token usage line + trim_history (75% of CONTEXT_SIZE) + tests/test_jarvis.py
- [ ] Task 6: README with exact PowerShell commands

## Checkpoint C (Phase 1 done)
- [ ] All Done-when boxes in PROJECT_CONTEXT.md §8 checked
- [ ] Kush can explain every file
