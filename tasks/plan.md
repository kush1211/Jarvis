# Plan: Jarvis Phase 1 — Python chat client for llama-server

## Context
Phase 0 is done: llama-server runs Gemma 4 E2B on the RTX 3050 and serves an OpenAI-compatible API on `http://127.0.0.1:8080/v1`. Phase 1 builds the Python terminal chat client that later phases (tool calling, voice, cloud) plug into. Requirements: `PROJECT_CONTEXT.md` §8 Phase 1. It's a learning project, so we go one small task at a time: I explain each task, you OK it, I write the code, we test it together, and you make sure you understand it before we move on.

Current state: the project folder has only `PROJECT_CONTEXT.md`. Python isn't on PATH; `uv` is installed (`C:\Users\Admin\.local\bin\uv.exe`) → we use it.

## Decisions
- **Env:** `uv venv --python 3.12` → `.venv`; `uv pip install -r requirements.txt`. Deps: `openai`, `python-dotenv`, `pytest`.
- **No framework.** Plain Python, 3 modules + 1 test file.
- **Thinking:** first look at the raw JSON the server actually returns (Task 0), then pick the parsing approach. Expected: llama-server with `--jinja` puts the thinking in `message.reasoning_content` (stream: `delta.reasoning_content`). Fallback: split on inline think tags.
- **Streaming vs non-streaming:** keep both functions in `llm.py`; `STREAM=true|false` in `.env` picks one, so you can compare the two.
- **Trimming:** after each reply, read `usage.prompt_tokens + completion_tokens` from the server. If it's over 75% of `CONTEXT_SIZE` (4096), drop the oldest user+assistant pair (never the system prompt). `# ponytail:` comment: it's a heuristic based on the last reply's size, not exact token counting; upgrade path = `/tokenize` endpoint.
- **Testing:** check each task by hand against the live server, plus one `tests/test_jarvis.py` for the pure logic (trimming, splitting inline thinking).

## Files
| File | Purpose |
|---|---|
| `requirements.txt` | openai, python-dotenv, pytest |
| `.env.example` (committed) / `.env` (gitignored) | `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`, `SHOW_THINKING`, `STREAM`, `CONTEXT_SIZE` |
| `.gitignore` | `.env`, `.venv/`, `__pycache__/` |
| `config.py` | loads `.env` once into module constants, plus `SYSTEM_PROMPT` |
| `llm.py` | `chat(messages) -> Reply` (non-stream) and `stream_chat(messages)` generator yielding `("thinking"|"answer", text)` and finally usage |
| `jarvis.py` | entry point: input loop, history, `/exit` `/clear`, printing, error messages, trimming |
| `tests/test_jarvis.py` | trimming + inline-thinking split |
| `README.md` | start server, set up env, run, settings |

Dependency order: config → llm → jarvis (loop) → thinking → streaming → usage/trim → README.

## Tasks

### Task 0 — Probe the server (no code, ~10 min)
Start llama-server, then send one request by hand with `Invoke-RestMethod` (non-stream) and with `curl.exe -N` (stream). Look at the response: where does the thinking text show up, is `usage` included, and what does a stream chunk look like.
- **AC:** we know which field holds the thinking, the shape of `usage`, and whether the stream sends usage at the end.
- **Verify:** findings written into `tasks/plan.md` under "Server findings".

### Task 1 — Env + multi-turn chat (non-streaming) · M
`requirements.txt`, `.env.example`, `.gitignore`, `config.py`, `llm.chat()`, and a minimal loop in `jarvis.py` that keeps `messages` and sends the full list each turn.
- **AC:** `python jarvis.py` starts; "my name is Kush" → "what's my name?" answers Kush. Settings come only from `.env`.
- **Verify:** manual run against the live server.

### Task 2 — Commands + friendly errors · S
`/exit` (plus Ctrl+C/EOF exits cleanly), `/clear` (reset to the system prompt only). Catch `openai.APIConnectionError` → `Can't reach llama-server at <url>. Is it running?` and keep the loop alive. Catch other `openai.APIError`s → short one-line message.
- **AC:** `/clear` makes it forget the name; with the server stopped you get the friendly message and no traceback; restarting the server and typing again works.
- **Verify:** manual (stop the server mid-session).

**Checkpoint A:** multi-turn + commands + errors work → review the code together.

### Task 3 — Thinking handling (non-streaming) · S
Use what we learned in Task 0. Only store the final answer in history (never the thinking). If `SHOW_THINKING=true`, print the thinking dimmed above the answer.
- **AC:** default → only the answer shows; with `SHOW_THINKING=true` → thinking + answer; history holds only the answer.
- **Verify:** manual with both settings; the test covers the inline-tag fallback.

### Task 4 — Streaming · M
`llm.stream_chat()` reads the chunks, yields thinking/answer pieces, and records usage at the end. `jarvis.py` prints the pieces as they arrive (`flush=True`) and builds the full answer for history. `STREAM` picks the mode.
- **AC:** the reply appears token by token; thinking is hidden or shown based on the setting; the remember-my-name test still passes; connection errors are still friendly (mid-stream too).
- **Verify:** manual, both `STREAM` values.

**Checkpoint B:** both modes work → compare how they feel and how fast they start, review `llm.py`.

### Task 5 — Token usage + history trimming · S
After each reply print `[tokens: prompt X + reply Y = Z / 4096]`. Pure function `trim_history(messages, used_tokens, limit)` drops the oldest user+assistant pair when over 75%. A server context-overflow error → trim + tell the user (or suggest `/clear`).
- **AC:** usage line shows every reply; a long chat never errors out on context; the system prompt is always kept.
- **Verify:** `.venv\Scripts\python -m pytest`; manual long chat (paste long text a few times).

### Task 6 — README · XS
Exact PowerShell commands: start the server, `uv venv`, install, copy `.env.example` → `.env`, run, settings table.
- **AC:** a fresh shell following the README gets to a working chat.

**Checkpoint C (Phase 1 done):** go through every checkbox in the Done-when list in `PROJECT_CONTEXT.md` §8, and you explain each file back in your own words.

## After approval
1. Write this plan to `tasks/plan.md` and the checklist to `tasks/todo.md` (the folder is empty, so nothing gets overwritten).
2. Start Task 0. Explain → your OK → do → verify → next.

## Risks
| Risk | Mitigation |
|---|---|
| Thinking comes back inline, or the field name is different | Task 0 checks this first; inline-tag fallback |
| Stream doesn't send usage | ask for it with `stream_options={"include_usage": True}`; else show usage only in non-stream mode |
| Thinking makes simple replies slow | out of scope for Phase 1; note `--reasoning-budget 0` / `chat_template_kwargs` to try in Phase 2 |
| VRAM taken by other apps → slow | close GPU apps; check Task Manager dedicated memory |

## Verification (end to end)
1. Start llama-server with the command from `PROJECT_CONTEXT.md` §5.
2. `.venv\Scripts\python jarvis.py`: multi-turn memory, `/clear`, `/exit`, thinking on/off, stream on/off, usage line.
3. Stop the server → friendly error; restart → keeps working.
4. `.venv\Scripts\python -m pytest` passes.

## Server findings (Task 0, 2026-10-29, build b11963)

**Non-streaming** (`POST /v1/chat/completions`):
- Thinking is in its own field: `choices[0].message.reasoning_content`. The final answer in `message.content` is clean, with no inline tags. → No tag splitting needed; drop the inline-tag fallback unless it shows up later.
- `usage` = `{prompt_tokens, completion_tokens, total_tokens, prompt_tokens_details.cached_tokens}`. **`completion_tokens` includes the thinking**: "17*23?" → 247 completion tokens for a 7-token answer.
- Bonus llama.cpp field `timings`: `predicted_per_second` (generation t/s), `prompt_per_second`, `cache_n`. Not part of the OpenAI format, but useful to show.

**Streaming** (`"stream": true`, server-sent events):
- Each line is `data: {json}`, with a blank line between events, ending with `data: [DONE]`.
- First chunk: `delta.role = "assistant"`. Then the thinking pieces arrive as `delta.reasoning_content`, then the answer pieces as `delta.content`. One field per chunk, never mixed.
- Last chunk before `[DONE]`: `finish_reason: "stop"` with an empty delta.
- With `stream_options: {"include_usage": true}` there's one extra chunk with `choices: []` that carries `usage` (+ `timings`). → Code must handle an empty `choices` list.
- "Say hi in 3 words" → 226 completion tokens, about 4 s of thinking before the first answer token shows up. So with thinking hidden, the user waits ~4 s seeing nothing → show a "thinking…" indicator.

**Other observations:**
- Server log: `n_slots = 4, n_ctx_slot = 4096, kv_unified = true`. The server runs 4 parallel request slots that share one 4096-token KV cache.
- `prompt_tokens_details.cached_tokens` / `cache_n`: the server reuses the KV cache for a prompt prefix it has already seen. That's why resending the full history each turn stays cheap.
- Generation was ~55 t/s this time (VRAM 2849/4096 MiB, all on GPU) vs 72–77 t/s in Phase 0. Cause unknown (power mode / charger / clocks?). A learning-track item, not a Phase 1 blocker.
- Thinking roughly doubles to 30x the token count for trivial prompts. A strong argument for turning thinking off for simple commands in Phase 2.

---

# Plan: Jarvis Phase 2: tool calling, first tool `open_app`

Phase 1 Tasks 3–6 are deferred (see todo.md). Phase 2 builds on the Task 2 code as it is now: non-streaming, no trimming.

## Decisions
- **No framework.** We write the tool loop ourselves: send messages + tools → if the reply has `tool_calls`, run them, append the results as `role: "tool"` messages, call again → stop when the reply is plain text.
- **Max 5 tool rounds per user message** (`MAX_TOOL_ROUNDS` in config.py). When the cap is hit, Jarvis prints a message and stops.
- **Allowlist in `config.py`** (`APPS = {"notepad": [path], ...}`), not `.env`, because it's a Python dict, not a secret. The model only sends a *name*. We look it up and run the fixed path with `subprocess.Popen([path])` and no shell, so model text never reaches a command line.
- **`open_app` runs without confirmation:** it's read-only in effect (opens a window, changes nothing). Confirmations start in Phase 3 for tools that change something.
- **Bad calls go back to the model as the tool result**, not as crashes (unknown app → "Unknown app 'x'. Allowed: ..."; bad JSON; unknown tool).
- **Log every call:** one line in the terminal (`[tool] open_app(name='notepad') -> Opened notepad`) and the same line, with a timestamp, appended to `tool_calls.log` (gitignored).
- **History:** the assistant message with `tool_calls` and every `tool` result go into `messages` (the model needs them to write its final answer). Thinking is never stored. On an error or Ctrl+C mid-loop we roll `messages` back to how it was *before* the user's message (today it's one `pop()`; with tools it can be several messages).
- **Files:** new `tools.py` (schema + allowlist lookup + `run_tool`). `llm.chat` takes `tools` and returns the whole message, not just the text. The loop lives in `jarvis.py`.

## Tasks

### Task 7: Probe tool calls on the raw server (no code) · XS
See exactly what llama-server returns before writing the loop (Gemma 4 had tool-call bugs at launch).
- Accept: we've seen and written down in "Phase 2 server findings": the shape of `tool_calls` (id, function.name, function.arguments as a JSON *string*), `finish_reason`, whether `content`/`reasoning_content` are set alongside, and what the final answer looks like after we send a `role: "tool"` result back.
- Verify: 2 curl requests by hand (call → result → answer). If the calls are malformed, update llama.cpp before going on.

### Task 8: First working tool call, end to end · M
"open notepad" opens Notepad, and Jarvis says it did.
- `tools.py`: `TOOLS` (open_app schema; `name` is an `enum` of the allowlist keys, so the template tells the model the valid names), `run_tool(name, arguments_json) -> str`, and the log line.
- `config.py`: `APPS` (notepad, calculator, chrome, edge, vscode, using paths found on this laptop) + `MAX_TOOL_ROUNDS = 5`.
- `llm.py`: `chat(messages, tools=None)` returns the message object.
- `jarvis.py`: the tool loop + rollback on error.
- Accept: "open notepad" opens it; the `[tool]` line prints; `tool_calls.log` gets a line; "what is 2+2" still answers with no tool call; a follow-up ("which app did you just open?") works, so history is right.
- Verify: manual, you watching.

### Task 9: Bad calls and the cap · S
- Accept: "open photoshop" → the model gets "Unknown app…" and tells you what it *can* open (no crash); broken argument JSON or an unknown tool name → an error result, no crash; the cap stops a looping model (tested by temporarily setting `MAX_TOOL_ROUNDS = 0`); Ctrl+C mid-loop rolls history back cleanly.
- Verify: manual + one small `tests/test_tools.py` (pytest) for `run_tool`'s error paths, which never start an app.

### Checkpoint D (Phase 2 done)
- [ ] All Task 8–9 checks pass, seen by you
- [ ] You can explain the loop in `jarvis.py` and why the allowlist makes it safe
- [ ] Commit + push when you say so

### Later (not in Phase 2 unless you want it)
- Thinking on/off for tool commands (roadmap says "consider… measure"). Only if the delay bothers you.

## Risks
| Risk | Mitigation |
|------|-----------|
| Gemma 4 tool-call template bugs | Task 7 checks first; update llama.cpp if needed |
| 2B model calls a tool when it shouldn't (or doesn't when it should) | System prompt line on when to use tools; `enum` limits names; check in Task 8 |
| Tool schemas + results use up the 4096-token context | Watch it; this is when deferred Task 5 (trimming) comes back |
| Chrome/VS Code paths change after updates | Paths live in one dict; a missing path gives a clear error result |

## Phase 2 server findings (Task 7, 2026-10-29, build b11963)
- **Tool calls work on this build. No llama.cpp update needed.** Request: system + "open notepad" + the `open_app` schema (`name` as an enum of 5 apps).
- Reply: `finish_reason: "tool_calls"`, `content: ""` (empty string, not null), `reasoning_content` set (thinking still happens first, ~160 tokens / ~3 s), and
  `tool_calls: [{"type":"function","id":"<32 random chars>","function":{"name":"open_app","arguments":"{\"name\":\"notepad\"}"}}]`.
  `arguments` is a **JSON string**, so we need `json.loads`.
- Sending back the assistant message (with `tool_calls`) + `{"role":"tool","tool_call_id":<id>,"content":"Opened notepad"}` → `finish_reason: "stop"`, content "Notepad is open."
- The tool schema costs few tokens: the whole first request was 116 prompt tokens.
- "what is 2+2" with tools attached → plain answer "4", no tool call.
- "open photoshop" (not in the enum) → no tool call; it answered "I cannot open Photoshop. I can only open notepad, calculator, chrome, edge, or vscode." The enum steers it. Task 9 still has to handle a bad name in code, because a model can ignore the enum.

# Plan: Front end, basic window (PySide6)

## Context
Kush wants a Windows app window, not the terminal or a website. This first window only proves the path works end to end (window → `reply()` → llama-server → tools → answer). Kush will provide the real design later, and it replaces this window.

## Decisions
- PySide6 (Kush's choice). New `app.py`; `jarvis.py` stays as the terminal client.
- `jarvis.ask(messages, text)` holds one full turn (with rollback on errors). Terminal and window both call it.
- The model call runs in a `QThread`, so the window doesn't freeze. Input is disabled while waiting.
- Out of scope until the design arrives: styling, tool rows in the window, Clear button, shortcut, `start.ps1` changes.

### Task F1: Basic window, end to end · S
Files: `requirements.txt`, `jarvis.py`, `app.py`.
Accept: chat works in the window; multi-turn memory; "open notepad" works; server off → friendly error; `jarvis.py` + pytest unchanged.

## Design port: "Quiet Glass" (2026-10-31)

### Overview
Port Kush's chosen design (canvas https://claude.ai/artifact/DF9Db4xD7GgbfWeoJPzKQJ: Option B and its state boards B1 first open, B2 working, B4 longer answer, B5 error) into `app.py`, replacing the F1 test window. The core stays the same: `jarvis.ask` → `reply` → `llm` / `tools`. Kush won't read the front-end code, so how it looks is what counts; core changes stay small and readable.

### Architecture decisions
- **Native Qt widgets styled with QSS, no web view.** (A web view would be a website in a window, which Kush ruled out.) Colors come from the design: background `#0f0f14`, text `#ececf3`, muted `#9a9aac`, accent `#a9a4ff`, user bubble `#23232e`, input pill `#1a1a23` with border `#2c2c3a`, error `#ffb48a` on `#261a16`.
- **Native Windows title bar, made dark** (DWM via `ctypes`). It looks close to the design, and snap, resize and Win11 rounded corners keep working. A custom frameless bar means more code and loses snap.
- **Orb** = one painted `QWidget` (radial gradient + glow) with three looks: ready, working (extra rings), offline (grey).
- **Font:** Segoe UI. Manrope isn't installed; adding it is a separate download step if wanted.
- **Assistant text is rendered as Markdown** (`Qt.MarkdownText`), because Gemma answers in Markdown (B4).
- **Two small core changes, done in the slice that needs them:** `tools.on_call = print` (hook for tool rows, F3) and `jarvis.ask` returning `(text, ok)` (error state, F4).

### Dependency graph
```
jarvis.ask / reply / tools   (exist, F1)
        │
        F2  styled window + normal chat ──┬── F3 working state + tool rows (tools.on_call hook)
                                          ├── F4 error state + Try again (ask → (text, ok))
                                          └── F5 dark title bar
```
F3, F4 and F5 each depend only on F2, but they all edit `app.py`, so they run one at a time.

### Task F2: Quiet Glass chat, normal flow · M
**Description:** Rewrite `app.py` in the Quiet Glass look. The first open shows B1. After the first message the window switches to the Option B chat layout.

**Acceptance criteria:**
- [ ] First open: big glowing orb, "How can I help?", "Type below.", a rounded input pill with a round accent Send button (Enter or a click sends)
- [ ] After a message: small orb + "Ready" at the top; a centred 640 px column; user bubble on the right (radius 20/20/6/20); Jarvis on the left with a small orb avatar; the list scrolls to the newest message
- [ ] Long Markdown answers (lists, code) wrap inside the column and scroll

**Verification:**
- [ ] Tests pass: `.venv\Scripts\python -m pytest`
- [ ] Builds: `.venv\Scripts\python -m py_compile app.py`
- [ ] Manual: `.venv\Scripts\python app.py`, compare with boards B1 and Option B, chat 3 turns (memory works)

**Dependencies:** F1 · **Files:** `app.py`

### Task F3: Working state and tool rows (B2) · S
**Description:** Show that Jarvis is busy, and show each tool call as it happens.

**Acceptance criteria:**
- [ ] While waiting: the orb gets rings, the label says "Working", the input is disabled with "Jarvis is working…"
- [ ] Each tool call adds a row with a check icon in a card under the turn, e.g. "open_app(notepad): Opened notepad"; "Error: …" results are muted
- [ ] The terminal client still prints `[tool] …` (hook default = `print`)

**Verification:**
- [ ] Tests pass: `.venv\Scripts\python -m pytest`
- [ ] Manual: "open notepad" in the app → Working, then the tool row, then the answer; `python jarvis.py` prints the tool line as before

**Dependencies:** F2 · **Files:** `app.py`, `tools.py`

### Task F4: Error state with "Try again" (B5) · S
**Description:** Show failures as the B5 error card instead of as a normal reply, and allow a one-click retry.

**Acceptance criteria:**
- [ ] `jarvis.ask` returns `(text, ok)`; the terminal prints exactly what it does today
- [ ] On error: grey orb, orange status ("Can't reach llama-server"), card "I couldn't finish that" + the message, a "Try again" button that resends the same text (history was already rolled back)
- [ ] The next successful turn brings back the normal look

**Verification:**
- [ ] Tests pass: `.venv\Scripts\python -m pytest`
- [ ] Manual: server stopped → send → error card; start the server → Try again → the answer arrives; `python jarvis.py` with the server stopped prints the same friendly line

**Dependencies:** F2 · **Files:** `jarvis.py`, `app.py`

### Task F5: Dark title bar · XS
**Description:** Make the native title bar match the window, and set the size and title.

**Acceptance criteria:**
- [ ] Dark-mode caption in color `#0f0f14`, window 1000×680, title "Jarvis"
- [ ] Snap, maximise and resize still work; if the DWM calls fail (older Windows), the app still starts

**Verification:**
- [ ] Manual: on Windows 11 the title bar blends into the window; Win+Left snaps it

**Dependencies:** F2 · **Files:** `app.py`

### Checkpoint G: design port done
- [ ] F2–F5 checked by Kush against the design boards
- [ ] pytest passes; `python jarvis.py` behaves as before
- [ ] Commit + push when Kush says so

### Out of scope (nothing behind it yet)
Mic button, "say Jarvis" and board B3 (voice, Phase 6) · "Use the local model instead" (cloud, Phase 5) · Stop button (needs streaming to cancel cleanly) · Copy card in B4 · typing while Jarvis works.

### Risks and mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| QSS can't do soft glows/shadows like CSS | Low | The orb glow is painted by hand; the input pill shadow uses `QGraphicsDropShadowEffect` or is dropped |
| Markdown in `QLabel` is basic (no syntax highlighting) | Low | Good enough for Gemma's answers; revisit if code answers look bad |
| DWM caption color is Win11-only | Low | Wrapped in try/except, so it falls back to the default bar |
| Long chats overflow the 4096-token context | Med | Shows as an error card (F4); history trimming is the deferred Task 5 |

### Open questions
- Manrope font: download and bundle it, or is Segoe UI fine?

## Animations (2026-10-31)
Kush picked every animation offered, at the **subtle** level. Only `app.py` changes.
- One helper `animate(start, end, ms, on_value)` (a `QVariantAnimation`) for every fade, slide, colour change and hover. Looping motion uses a ~30 fps `QTimer` per small widget, stopped while hidden. Opacity effects are removed when each fade ends.
- Timings: breathing 3.5 s · ripple 2.4 s · fade + slide 250 ms · colour 400 ms · orb shrink 450 ms · hover 150 ms, all ease-out.

### Task A1: Living orb · S
Breathing glow when idle, ripples while working, a 400 ms purple ↔ grey blend on error and recovery. Accept: all three visible; ~0 % CPU when minimised.
### Task A2: First-message transition · M
The heading and hint fade out, and the orb shrinks from the centre into the top orb. Accept: no jump or flash, lands exactly, survives a resize.
### Task A3: Chat motion · M
Messages fade and slide in, typing dots while working, tool rows pop in with a self-drawing tick, smooth scroll. Accept: dots → row → answer with no jumps.
### Task A4: Controls · S
Send hover/press/nudge, input focus glow, Try again hover. Accept: soft, and no hover while disabled.
### Checkpoint H
Kush checks all four against the live server; pytest (6) passes; `jarvis.py` unchanged; commit when Kush says so.
