"""The agent loop, written by hand so every step is visible.

An "agent" is a loop around one API call:

    send the conversation -> Claude replies
        if the reply asks for tools: run them, append the results, loop again
        otherwise: Claude is done, return the answer

Everything else (memory, planning, sub-agents) is built on top of this loop.
"""

import anthropic

from punchy.tools import TOOLS, run_tool

MODEL = "claude-opus-5-5"
MAX_STEPS = 20  # Stop a runaway loop if Claude keeps calling tools.

SYSTEM_PROMPT = """You are Punchy, a helpful assistant running in a terminal.
Use your tools when they help: the calculator for arithmetic, and list_files / read_file
to look at files in the user's workspace. Keep answers short and concrete."""


class Agent:
    def __init__(self, verbose: bool = False):
        self.client = anthropic.Anthropic()
        # The whole conversation. The API is stateless, so we resend all of it on
        # every call. Only ever append to it: editing earlier turns invalidates
        # the model's saved thinking.
        self.messages: list = []
        self.verbose = verbose

    def _log(self, text: str) -> None:
        if self.verbose:
            print(f"  \033[2m{text}\033[0m")

    def ask(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})

        for step in range(MAX_STEPS):
            response = self.client.beta.messages.create(
                model=MODEL,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=self.messages,
                output_config={"effort": "medium"},
                # If a safety classifier declines, retry on a fallback model
                # instead of stopping.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
            self._log(
                f"step {step + 1}: stop_reason={response.stop_reason} "
                f"tokens in/out={response.usage.input_tokens}/{response.usage.output_tokens}"
            )

            # Append Claude's reply exactly as returned (including thinking and
            # tool_use blocks). The next request needs it.
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "refusal":
                return "[Claude declined this request.]"
            if response.stop_reason == "max_tokens":
                return _text(response) + "\n[Response was cut off at max_tokens.]"
            if response.stop_reason != "tool_use":
                return _text(response)

            # Claude asked for one or more tools. Run each one, and send all of
            # the results back together in a single user message.
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                output, is_error = run_tool(block.name, block.input)
                self._log(f"tool {block.name}({block.input}) -> {'ERROR: ' if is_error else ''}{output[:200]!r}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                    "is_error": is_error,
                })
            self.messages.append({"role": "user", "content": tool_results})

        return f"[Stopped after {MAX_STEPS} steps without a final answer.]"


def _text(response) -> str:
    return "".join(b.text for b in response.content if b.type == "text")
