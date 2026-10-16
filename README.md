# punchy-practice

A practice ground for building AI agents and ML systems from first principles.

`punchy` is a minimal terminal agent built on the Claude API. The agent loop is
written by hand (about 60 lines in `src/punchy/agent.py`) so every step is visible:
send the conversation, run the tools Claude asks for, send the results back, and repeat.

## Setup

```bash
python3 -m venv .venv            # if ensurepip is missing: python3 -m venv --without-pip .venv
                                 #   then use: pip3 --python .venv/bin/python install -e '.[dev]'
.venv/bin/pip install -e '.[dev]'
export ANTHROPIC_API_KEY=sk-ant-...   # https://console.anthropic.com/settings/keys
```

## Run

```bash
.venv/bin/punchy -v      # -v shows each loop step, token counts and tool calls
```

Try: `what's 17% of 2340?`, `what files are here?`, `summarize src/punchy/agent.py`.

Tests (no API key needed): `.venv/bin/pytest`

## Layout

| File | What it teaches |
|---|---|
| `src/punchy/tools.py` | Tool schemas, safe tool execution, and returning errors to the model |
| `src/punchy/agent.py` | The agent loop: stop reasons, message history, tool_use and tool_result |
| `src/punchy/cli.py` | The REPL and API error handling |

## Practice roadmap

Each step is a small, self-contained exercise:

1. **Add a tool.** Write a `write_file` tool and ask for confirmation in the CLI before it runs (human in the loop).
2. **Streaming.** Print tokens as they arrive with `client.messages.stream(...)`.
3. **Memory.** Save and reload `agent.messages` so sessions resume. Then add a "notes" tool for long-term facts.
4. **Evals.** Write 10 to 20 tasks with expected outcomes, then score the agent's answers automatically. This is where agent-building becomes engineering.
5. **Compare with the framework.** Rebuild the loop with the SDK's Tool Runner (`client.beta.messages.tool_runner`) and see what it saves you.
6. **ML side.** Give the agent tools that train and evaluate a small scikit-learn model, and let it iterate on its own experiments.
7. **Multi-agent.** Have a planner agent hand subtasks to worker agents (each one is just another `Agent` instance).
