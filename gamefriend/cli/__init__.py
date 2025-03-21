"""
Command-line interface for GameFriend.
"""

import os
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt

from gamefriend.chat.companion import GameCompanion
from gamefriend.scraper import GameFAQsScraper

# Default console instance
default_console = Console()


@click.group()
def cli():
    """GameFriend - Your AI Gaming Companion"""
    pass


@cli.command()
@click.argument("url")
@click.option("-o", "--output", help="Output file path")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
def download(url: str, output: str = None, verbose: bool = False):
    """Download a game guide from GameFAQs."""
    try:
        scraper = GameFAQsScraper(verbose=verbose)
        content, output_path = scraper.download_guide(url, output)

        if verbose:
            print(f"Got content (length: {len(content)})")
            print("First 1000 chars:")
            print(content[:1000])

        # Ensure parent directories exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the guide
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Saving to: {output_path}")
        print(f"Wrote {len(content)} bytes to {output_path}")
        print(f"Successfully downloaded guide to {output_path}")

    except Exception as e:
        print(f"Error: {str(e)}")
        raise click.Abort()


@cli.command()
@click.argument("game_name")
@click.option("--api-key", envvar="MISTRAL_API_KEY", help="Mistral API key")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
def chat(game_name: str, api_key: str = None, verbose: bool = False):
    """Start a chat session with GameFriend about a specific game."""
    # Check for API key first, before any interactive elements
    if not api_key:
        print("Error: Mistral API key not provided. Set MISTRAL_API_KEY environment variable or use --api-key")
        raise click.Abort()

    try:
        companion = GameCompanion(game_name=game_name, api_key=api_key, verbose=verbose)

        print(f"\nGameFriend - Your AI Gaming Companion for {game_name}")
        print("Type 'quit', 'exit', or press Ctrl+C to end the chat\n")

        while True:
            try:
                # Get user input
                message = input("\nYou: ")

                # Check for exit command
                if message.lower() in ["quit", "exit"]:
                    break

                # Get response
                print("\nGameFriend is thinking...", end="")
                response = companion.chat(message)

                # Print response
                print("\nGameFriend:")
                print(response)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\nError: {str(e)}")
                if verbose:
                    import traceback
                    print(traceback.format_exc())

    except Exception as e:
        print(f"\nError: {str(e)}")
        if verbose:
            import traceback
            print(traceback.format_exc())
        raise click.Abort()


if __name__ == "__main__":
    cli()
