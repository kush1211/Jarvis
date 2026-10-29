# Jarvis: Personal Local AI Assistant (Full Project Context)

This file holds everything about the project so far: the goal, decisions, setup, what's done, what was learned, the roadmap, and how to work with me. Read all of it before starting any work.

---

## 1. Who I am and how to work with me

I'm **Kush**, an AI/ML engineer (~7 months of professional experience). At work I build multi-agent systems and RAG systems with LLM APIs, so tool calling, agent loops, and backends are familiar to me. **Local model hosting (llama.cpp, GPU/VRAM, quantization) is new to me**, and learning it is a main goal of this project.

How I want you to work:

- **This is a learning project.** Explain what you do and why, step by step, in simple words. Not too basic, not too advanced.
- **Before teaching a concept, ask what I already know** and start from there.
- **Don't use analogies from unrelated domains** (kitchens, cars, etc.). Explain things directly in terms of the actual system.
- **Plan before code.** For each step: explain the plan, ask about anything unclear, wait for my OK, then write code.
- **Small steps.** One working piece at a time, tested before moving on.
- **Be honest.** If my idea or approach is weak, say so and explain why. Don't just agree.
- **Ask questions** when requirements or approaches are ambiguous.
- No frameworks (LangChain, LangGraph, etc.) unless we explicitly decide on one. Plain Python, so I see how things work.

---

## 2. The vision

A **Jarvis-style assistant** that runs **always-on on my own Windows laptop**, which I can talk to and which can **do things on my system** through tools.

Decisions already made:

- **Hybrid LLM:** local model + cloud LLM option. **Starting local-only**, because I want to learn local model hosting. Cloud comes later (I've researched free tiers: OpenRouter, Groq, DeepSeek).
- **Engine: llama.cpp** (not Ollama). I've used Ollama before; llama.cpp gives more control and teaches more.
- **Text first, voice later.**
- **First features:** opening apps, then tasks like sending WhatsApp messages.
- **No fine-tuning** for now.

---

## 3. Hardware and environment

- **OS:** Windows (PowerShell)
- **CPU:** Intel i5-12500H
- **RAM:** 16 GB (15.7 usable); usually 9–10 GB already in use by other apps
- **GPU:** NVIDIA RTX 3050 Laptop, **4 GB VRAM** (shows as **GPU 0** in Task Manager); Intel Iris Xe integrated graphics is GPU 1 (not used)
- **NVIDIA driver:** 32.0.15.9282 (dated 2026-06-03)
- **Dev tools I use:** Claude Code, Cursor, Python

---

## 4. What's done so far (Phase 0, complete)

1. **Installed llama.cpp** from the official GitHub releases (`github.com/ggml-org/llama.cpp/releases`). Downloaded two zips and extracted both into **`C:\llama.cpp`**:
   - the **Windows x64 CUDA 12** build (`llama-cli.exe`, `llama-server.exe`, etc.)
   - the **CUDA 12.4 DLLs** (`cudart-...`), the CUDA runtime libraries, so the full CUDA toolkit isn't needed
   - Build: `b11963-39febd2ad`
   - Note: `llama-cpp.com` is NOT official. Download only from GitHub.
2. **Model:** **Gemma 4 E2B instruct, Q4_K_M** (`unsloth/gemma-4-E2B-it-GGUF:Q4_K_M`), about 3.4 GB. Downloaded automatically by llama.cpp with `-hf` and cached locally. A vision/audio projector file (`mmproj-BF16.gguf`) was also downloaded; the model supports text, vision, audio, and video input.
3. **Verified GPU works:** `llama-cli.exe --list-devices` shows `CUDA0: NVIDIA GeForce RTX 3050 Laptop GPU (4095 MiB)`.
4. **Ran it in chat mode** (`llama-cli`) and measured performance (see section 6).
5. **Ran `llama-server`** and chatted through its built-in web UI in the browser. Works.

### Why Gemma 4 E2B

- Released by Google (March 2026) in sizes E2B, E4B, 26B A4B, 31B. **E2B and E4B support function calling.**
- "E" = **effective** parameters: these models use Per-Layer Embeddings, so the file is bigger than the "effective" size suggests. E4B has about 8B total parameters.
- **E2B fits fully on my 4 GB GPU.** E4B is smarter but likely won't fully fit, so part would run on CPU (slower). Plan: get everything working on E2B, then compare E4B.
- Also known: **FunctionGemma** (270M, Dec 2025), built for function calling but too small for general chat. Possible later use as a fast tool router.
- Caution: early reports (April 2026) mentioned Gemma 4 tool-calling bugs at launch. **If tool calls look broken, update llama.cpp first** before assuming our code is wrong.

---

## 5. Commands

**Chat in terminal (testing only):**
```
cd C:\llama.cpp
.\llama-cli.exe -hf unsloth/gemma-4-E2B-it-GGUF:Q4_K_M -c 4096 -ngl 99
```

**Server (what Jarvis uses). Keep this PowerShell window open while using Jarvis:**
```
cd C:\llama.cpp
.\llama-server.exe -hf unsloth/gemma-4-E2B-it-GGUF:Q4_K_M -c 4096 -ngl 99 --jinja --port 8080
```

| Option | Meaning |
|---|---|
| `-hf <repo>:<quant>` | get the model from Hugging Face (downloads once, then uses the cached copy) |
| `-c 4096` | context size in tokens; without it, it may try the model's huge default context and run out of VRAM |
| `-ngl 99` | number of layers to put on the GPU; 99 = all of them |
| `--jinja` | use the model's own chat template; required for tool calling |
| `--port 8080` | fixed port. Without it, the server once started on **9931**. Code must read the URL from config. |

Other useful checks:
- `.\llama-cli.exe --list-devices` shows which GPUs llama.cpp can see.
- `http://127.0.0.1:8080/` is the built-in chat web UI.
- `http://127.0.0.1:8080/v1/models` returns raw API info about the loaded model.

**Only run one of llama-cli / llama-server at a time.** Each loads its own copy of the model into VRAM, and two copies don't fit.

---

## 6. Measurements and what I learned

| Run | VRAM used | Shared GPU memory | Generation speed |
|---|---|---|---|
| Without `-ngl 99` (only ~3.3 GB VRAM free then) | not measured | not measured | **38.4 t/s** |
| With `-ngl 99`, GPU empty before start | **2.8 / 4.0 GB** | 0.1 GB (no spill) | **~72–77 t/s** |

GPU temperature went from 45 °C to 64 °C during generation.

Lessons:
- **Without `-ngl 99`, llama.cpp split the model between GPU and CPU on its own**, because VRAM was partly used by other apps. Forcing all layers on the GPU with free VRAM **doubled** the speed.
- **Free VRAM matters.** Other GPU-using apps push layers onto the CPU and roughly halve speed.
- **About 1.2 GB VRAM is still free** with `-c 4096`. That can be spent on a bigger context later.
- VRAM use (2.8 GB) is less than the file size (3.4 GB) because llama.cpp keeps part of the E-model's weights (embeddings) in normal RAM by design.
- **CPU usage rising during generation is normal** even on GPU. The CPU still coordinates each step.
- **Task Manager's GPU "Utilization" shows 0% for llama.cpp.** Its default graphs (3D, Copy, Video) don't count CUDA work. Use **Dedicated GPU memory**, **Shared GPU memory** (rising = spilling into slow RAM), and temperature instead. A graph can be switched to "Cuda"/"Compute_0" if that option exists.
- Each reply shows `[ Prompt: X t/s | Generation: Y t/s ]`:
  - **Prompt** = speed of reading the input. It's processed in parallel batches, so longer inputs show much higher numbers (saw 70 to 2105 t/s).
  - **Generation** = speed of writing the answer, one token at a time. **This is the number to compare between setups.**
- **Gemma 4 "thinking" mode is on by default.** It writes a `[Start thinking] ... [End thinking]` section before every answer, even for "hi". Good for hard questions, wasted time for simple commands. Needs handling in Jarvis (hide it, and possibly disable or limit it for simple tasks).

### Key concepts (short glossary)

- **llama.cpp** = the inference engine (the program). **GGUF** = the model file format it loads.
- **Quantization (Q4_K_M, Q5, Q8)** = weights compressed to fewer bits. Smaller file and less VRAM, slight quality loss.
- **VRAM** = the GPU's own fast memory (4 GB). **RAM** = normal system memory (16 GB), slower for the model.
- **Layers** = the model is a stack of layers. Each one on the GPU is computed fast; each one left in RAM is computed by the CPU.
- **Context / KV cache** = memory for the conversation. A bigger `-c` uses more VRAM.
- **CUDA** = NVIDIA's system for running computations on the GPU.
- **llama-server** = runs the model as a local **OpenAI-compatible API** (`/v1/chat/completions`), so any program can use it.
- **localhost / 127.0.0.1** = this computer only. **Port** = the number identifying which program to talk to.

---

## 7. Architecture

```
You (terminal now, voice later)
        |
        v
Jarvis (Python program)  <-- this is what we build
  - keeps conversation history
  - sends messages + tool definitions to the LLM
  - executes tool calls itself (open app, etc.)
  - sends tool results back to the LLM
        |
        v  HTTP, OpenAI-compatible API
llama-server on localhost:8080  (Gemma 4 E2B on the RTX 3050)
        (later: cloud LLM via the same API format, for hard tasks)
```

**Core principle: the model never does anything by itself. It only outputs text.** When it "calls a tool", it only outputs a request like "call open_app with name=chrome". The Jarvis Python code decides whether to run it, runs it, and returns the result. All control and safety live in our code.

---

## 8. Roadmap

### Phase 1: Python chat client (NEXT)

A terminal chat loop in Python that talks to llama-server. This is the skeleton tools get added to.

Requirements:
1. **Use the `openai` Python library** with `base_url` pointed at the local server and a dummy API key, so switching to a cloud model later is only a config change.
2. **Config in a `.env` file** (base URL, model name, API key), plus a committed `.env.example`. Default URL: `http://127.0.0.1:8080/v1`.
3. **Conversation memory:** a list of messages (system + user + assistant), sent in full each turn.
4. **System prompt** kept in one place: it's "Jarvis", a helpful assistant on Kush's laptop, short direct replies.
5. **Handle the thinking output.** With `--jinja`, llama-server may return thinking separately (e.g. a `reasoning_content` field) or inline. **Check what the server actually returns first.** Print only the final answer by default; a setting like `SHOW_THINKING=true` shows the thinking too.
6. **Streaming:** print replies token by token. Build the non-streaming version first, then add streaming as a second milestone, so I understand both.
7. **Commands:** `/exit` to quit, `/clear` to reset history (keep the system prompt).
8. **Friendly errors:** if the server is down or the port is wrong, show "Can't reach llama-server at <url>. Is it running?" instead of a stack trace.
9. **Context limit:** the context is 4096 tokens. Show token usage per reply if returned. When history gets long, trim the oldest turns (never the system prompt). Keep it simple.

Structure (small, but ready for tools):
- config module
- LLM client module (send messages, return reply; streaming and non-streaming)
- chat loop / CLI entry point
- `requirements.txt`, `.env.example`, short `README.md` (how to start the server, how to run the client)
- a virtual environment; give me the exact PowerShell commands to create it and install dependencies

Done when:
- [ ] Multi-turn conversation works, and the model remembers earlier messages.
- [ ] Thinking is hidden by default and visible with the setting.
- [ ] Replies stream token by token.
- [ ] `/clear` and `/exit` work.
- [ ] With the server stopped, a clear error is shown instead of a crash.
- [ ] I understand every file.

### Phase 2: Tool calling, first tool `open_app`

- Define tools as JSON schemas, send them with the request, detect tool-call responses, execute in Python, send results back, get the final answer.
- Write the loop ourselves (no framework) so I see every step. Put a **maximum number of tool iterations** per user message to prevent infinite loops.
- `open_app` opens apps from an **allowlist** (e.g. a config mapping like `"chrome" -> path/command`). Never pass model output straight into a shell.
- Log every tool call (name, arguments, result) so I can see what the model decided.
- A 2B model will sometimes pick the wrong tool or produce bad arguments: validate arguments and return clear error messages to the model.
- Consider turning thinking off/low for simple commands to cut delay; measure the difference.
- If tool calls come back malformed: update llama.cpp first (known Gemma 4 launch bugs), and confirm `--jinja` is on.

### Phase 3: More system tools

Candidates: current time/date, system info (battery, RAM, VRAM), reading files in specific allowed folders, opening URLs, media/volume controls.
- **Safety tiers:** safe read-only tools run directly; anything that changes or sends something requires my **confirmation in the terminal**.
- No general "run any shell command" tool, at least not early.

### Phase 4: WhatsApp messaging

Options need researching when we get here (they change often). Known directions: automating WhatsApp Desktop/Web, or the official WhatsApp Business Cloud API (needs a business number). Compare reliability, terms-of-service risk, and setup effort before choosing. Sending messages **always requires my confirmation** (recipient + text shown before sending).

### Phase 5: Hybrid local + cloud

- Same OpenAI-compatible client, different `base_url`/key per provider.
- Routing rule to decide: e.g. local by default, cloud for hard/long tasks or when the local model fails. Decide the rule together later.
- Never send sensitive local data to the cloud without a clear rule for it.

### Phase 6: Voice

- Speech-to-text, text-to-speech, and maybe a wake word. Research current options when we get here.
- **VRAM is the constraint:** the LLM already uses ~2.8 of 4 GB. STT/TTS may need to run on CPU. Measure.
- Gemma 4 E2B accepts **audio input natively** (the mmproj file; `llama-cli` has an `/audio` command). Worth testing whether it can replace a separate STT model.

### Phase 7: Always-on

Start llama-server and Jarvis automatically at login, run in the background (maybe a tray icon), restart if they crash, and free VRAM when idle if needed.

### Learning track (in parallel, my own pace)

I'll study GPU theory, then run experiments and log the numbers (generation t/s, VRAM, shared memory, answer quality) in a notes file:
- vary `-ngl` (e.g. 0, 10, 20, 99) to see the CPU/GPU split effect
- vary `-c` (2048, 4096, 8192, 16384) to see context cost in VRAM
- compare quantizations (Q4_K_M vs Q5_K_M vs Q8_0)
- compare E2B vs E4B
- thinking on vs off: speed and answer quality
- later: build llama.cpp from source to learn the build process

---

## 9. Safety rules for Jarvis (apply in every phase)

1. The model only proposes actions; our code executes them, and only through defined tools.
2. Allowlists over free-form input (apps, folders, contacts).
3. Confirmation before anything that sends, deletes, modifies, or costs money.
4. Never execute raw model output as a shell command.
5. Log all tool calls.
6. Cap tool iterations per request.
7. Keep secrets (API keys) in `.env`, never in code or logs; `.env` is in `.gitignore`.

---

## 10. Open questions (decide together when we reach them)

- Exact routing rule between local and cloud models.
- WhatsApp approach.
- Voice stack (separate STT vs Gemma's native audio).
- Whether to move to E4B if E2B's tool calling is too unreliable.
- Thinking mode: always off, always on, or chosen per request.
