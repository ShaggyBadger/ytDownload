from rich.console import Console
from pathlib import Path
from typing import Optional
import time

from joshlib.gemini import GeminiClient
from config import config

class Formatter:
    def __init__(self):
        self.console = Console()
        self.gemini_client = GeminiClient()

    def run(self, job_directory: Path, input_file_path: Path) -> Optional[Path]:
        """
        Orchestrates the formatting of a transcription. Reads the input,
        formats it using Gemini, and saves the result to disk.
        """
        max_retries = 3
        word_loss_threshold = 1.5 # Percentage

        try:
            self.console.print(f"  Reading transcription from [bold blue]{input_file_path.name}[/bold blue]...", highlight=False)
            transcript_text = input_file_path.read_text(encoding='utf-8')
            original_word_count = self._count_words(transcript_text)
            
            formatted_text = None
            for attempt in range(max_retries):
                self.console.print(f"  Calling Gemini for text formatting (Attempt {attempt + 1}/{max_retries})...", highlight=False)
                formatted_text = self._format_text(transcript_text)
                
                if formatted_text is None: # Quota error or API error
                    self.console.print("  [yellow]Warning: Gemini API quota exceeded or another API error occurred during formatting. Aborting retries.[/yellow]")
                    return None
                
                formatted_word_count = self._count_words(formatted_text)
                if original_word_count > 0: # Avoid division by zero
                    word_loss_percentage = ((original_word_count - formatted_word_count) / original_word_count) * 100
                else: # If original has no words, any formatted text is fine
                    word_loss_percentage = 0 

                if word_loss_percentage <= word_loss_threshold:
                    self.console.print(f"  Word loss ({word_loss_percentage:.2f}%) within acceptable limits (<= {word_loss_threshold}%).", highlight=False)
                    break # Success, break out of retry loop
                else:
                    self.console.print(f"  [yellow]Word loss ({word_loss_percentage:.2f}%) exceeds threshold ({word_loss_threshold}%). Retrying...[/yellow]", highlight=False)
                    time.sleep(2) # Wait a bit before retrying

            if formatted_text is None or word_loss_percentage > word_loss_threshold:
                self.console.print(f"  [bold red]Failed to format text after {max_retries} attempts due to excessive word loss.[/bold red]")
                return None # Indicate persistent failure after retries

            output_file_path = job_directory / config.FORMATED_TRANSCRIPT_NAME
            self.console.print(f"  Saving formatted transcription to [bold blue]{output_file_path.name}[/bold blue]...", highlight=False)
            output_file_path.write_text(formatted_text, encoding='utf-8')
            
            return output_file_path

        except RuntimeError as e:
            self.console.print(f"  [bold red]Error during formatting process: {e}[/bold red]")
            raise # Re-raise the runtime error
        except Exception as e:
            self.console.print(f"  [bold red]An unexpected error occurred during formatting: {e}[/bold red]")
            raise

    def _build_big_paragraph(self, text: str) -> str:
        """Removes all the extra spaces and new lines etc."""
        paragraph = " ".join(text.split())
        return paragraph

    def _format_text(self, text: str) -> Optional[str]:
        """
        Submits the text to Gemini for formatting and returns the response.
        Returns None if a quota error or API error occurs.
        """
        prompt_path = Path(__file__).parent / 'prompts/formatter/format-paragraph.txt'
        prompt = prompt_path.read_text(encoding='utf-8')
        
        # Ensure the text is built into a big paragraph before sending to LLM
        clean_text = self._build_big_paragraph(text)
        prompt = prompt.format(SERMON_TEXT=clean_text)
        
        response = self.gemini_client.submit_prompt(prompt)
        return response

    def _count_words(self, text: Optional[str]) -> int:
        """Counts the number of words in a given string."""
        if not text:
            return 0
        return len(text.split())
