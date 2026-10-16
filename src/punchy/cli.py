import argparse

import anthropic

from punchy.agent import Agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat with Punchy, a minimal Claude agent.")
    parser.add_argument("-v", "--verbose", action="store_true", help="show each loop step and tool call")
    args = parser.parse_args()

    agent = Agent(verbose=args.verbose)
    print("Punchy is ready. Type 'exit' or press Ctrl-D to quit.")
    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user_input in {"exit", "quit"}:
            break
        if not user_input:
            continue
        try:
            print(agent.ask(user_input))
        except anthropic.AuthenticationError:
            print("Authentication failed. Set ANTHROPIC_API_KEY and try again.")
            break
        except anthropic.RateLimitError:
            print("Rate limited. Wait a moment and try again.")
        except anthropic.APIStatusError as e:
            print(f"API error ({e.status_code}): {e.message}")
        except anthropic.APIConnectionError:
            print("Network error. Check your connection.")


if __name__ == "__main__":
    main()
