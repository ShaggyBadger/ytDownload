import logging
from rich.console import Console
from pathlib import Path
from typing import Optional
import time
import re

from joshlib.gemini import GeminiClient
from config import config

logger = logging.getLogger(__name__)

class Formatter:
    def __init__(self):
        self.console = Console()
        self.gemini_client = GeminiClient()
        logger.debug("Formatter service initialized.")

    def run(self, job_directory: Path, input_file_path: Path) -> Optional[Path]:
        """
        Orchestrates the formatting of a transcription. Reads the input,
        formats it using Gemini, and saves the result to disk.
        """
        logger.info(f"Starting transcription formatting for job directory: {job_directory}, input file: {input_file_path}")
        max_retries = 3
        word_loss_threshold = 1.5 # Percentage

        try:
            logger.debug(f"Reading transcription from {input_file_path.name}")
            # self.console.print(f"  Reading transcription from [bold blue]{input_file_path.name}[/bold blue]...", highlight=False)
            transcript_text = input_file_path.read_text(encoding='utf-8')
            original_word_count = self._count_words(transcript_text)
            logger.debug(f"Original transcript word count: {original_word_count}")
            
            formatted_text = None
            word_loss_percentage = 100.0 # Initialize to a high value

            for attempt in range(max_retries):
                logger.info(f"Calling Gemini for text formatting (Attempt {attempt + 1}/{max_retries}).")
                # self.console.print(f"  Calling Gemini for text formatting (Attempt {attempt + 1}/{max_retries})...", highlight=False)
                formatted_text = self._format_text(transcript_text)

                if formatted_text is None: # Quota error or API error caught in _format_text
                    logger.warning("Gemini API quota exceeded or another API error occurred during formatting. Aborting retries.")
                    # self.console.print("  [yellow]Warning: Gemini API quota exceeded or another API error occurred during formatting. Aborting retries.[/yellow]")
                    return None
                
                # clean up extra paragraph breaks
                formatted_text = re.sub(r'\n+', '\n', formatted_text).strip()
                
                formatted_word_count = self._count_words(formatted_text)
                if original_word_count > 0:
                    word_loss_percentage = ((original_word_count - formatted_word_count) / original_word_count) * 100
                else:
                    word_loss_percentage = 0 # If original has no words, any formatted text is fine
                
                logger.debug(f"Attempt {attempt + 1}: Formatted words: {formatted_word_count}, Word loss: {word_loss_percentage:.2f}% (Threshold: {word_loss_threshold}%)")

                if word_loss_percentage <= word_loss_threshold:
                    logger.info(f"Word loss ({word_loss_percentage:.2f}%) within acceptable limits (<= {word_loss_threshold}%). Formatting successful.")
                    # self.console.print(f"  Word loss ({word_loss_percentage:.2f}%) within acceptable limits (<= {word_loss_threshold}%).", highlight=False)
                    break # Success, break out of retry loop
                else:
                    logger.warning(f"Word loss ({word_loss_percentage:.2f}%) exceeds threshold ({word_loss_threshold}%). Retrying...")
                    # self.console.print(f"  [yellow]Word loss ({word_loss_percentage:.2f}%) exceeds threshold ({word_loss_threshold}%). Retrying...[/yellow]", highlight=False)
                    time.sleep(2) # Wait a bit before retrying

            if formatted_text is None or word_loss_percentage > word_loss_threshold:
                logger.error(f"Failed to format text after {max_retries} attempts due to excessive word loss ({word_loss_percentage:.2f}%).")
                # self.console.print(f"  [bold red]Failed to format text after {max_retries} attempts due to excessive word loss.[/bold red]")
                return None

            output_file_path = job_directory / config.FORMATED_TRANSCRIPT_NAME
            logger.info(f"Saving formatted transcription to {output_file_path.name}")
            # self.console.print(f"  Saving formatted transcription to [bold blue]{output_file_path.name}[/bold blue]...", highlight=False)
            output_file_path.write_text(formatted_text, encoding='utf-8')
            
            logger.info(f"Formatted transcription saved to {output_file_path}. Returning path.")
            return output_file_path

        except RuntimeError as e:
            logger.error(f"RuntimeError during formatting process for {input_file_path}: {e}", exc_info=True)
            # self.console.print(f"  [bold red]Error during formatting process: {e}[/bold red]")
            raise # Re-raise the runtime error
        except Exception as e:
            logger.critical(f"An unexpected error occurred during formatting for {input_file_path}: {e}", exc_info=True)
            # self.console.print(f"  [bold red]An unexpected error occurred during formatting: {e}[/bold red]")
            raise

    def _build_big_paragraph(self, text: str) -> str:
        """Removes all the extra spaces and new lines etc."""
        logger.debug(f"Building big paragraph from text (length: {len(text)}).")
        paragraph = " ".join(text.split())
        logger.debug(f"Big paragraph built (length: {len(paragraph)}).")
        return paragraph

    def _format_text(self, text: str) -> Optional[str]:
        """
        Submits the text to Gemini for formatting and returns the response.
        Returns None if a quota error or API error occurs.
        """
        logger.debug(f"Calling Gemini for formatting text (length: {len(text)}).")
        prompt_path = Path(__file__).parent / 'prompts/formatter/format-paragraph.txt'
        logger.debug(f"Loading prompt from: {prompt_path}")
        try:
            prompt = prompt_path.read_text(encoding='utf-8')
        except FileNotFoundError:
            logger.critical(f"Prompt file not found at {prompt_path}.", exc_info=True)
            raise
        
        clean_text = self._build_big_paragraph(text)
        prompt = prompt.format(SERMON_TEXT=clean_text)
        logger.debug(f"Prompt prepared (length: {len(prompt)}). Submitting to Gemini.")
        
        try:
            response = self.gemini_client.submit_prompt(prompt)
            if response is None: # Explicitly check for None return for quota issues
                logger.warning("GeminiClient returned None, indicating a quota error or similar API issue. Returning None.")
                return None
            logger.debug(f"Received response from Gemini (length: {len(response) if response else 0}).")
            return response
        except RuntimeError as e: # Catch specific RuntimeError raised by GeminiClient
            logger.error("Gemini CLI call failed with RuntimeError: %s.", e, exc_info=True)
            return None
        except Exception as e: # Catch any other unexpected exceptions
            logger.critical("An unhandled exception occurred during Gemini CLI call: %s.", e, exc_info=True)
            return None

    def _count_words(self, text: Optional[str]) -> int:
        """Counts the number of words in a given string."""
        if not text:
            logger.debug("Counting words in empty or None text. Result: 0")
            return 0
        count = len(text.split())
        logger.debug(f"Counted {count} words in text (length: {len(text)}).")
        return count