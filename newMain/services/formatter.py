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
        logger.info(
            f"Starting transcription formatting for job directory: {job_directory}, input file: {input_file_path}"
        )
        max_retries = 3
        word_loss_threshold = 1.5  # Percentage

        try:
            transcript_text = input_file_path.read_text(encoding="utf-8")
            original_word_count = self._count_words(transcript_text)
            logger.debug(f"Original transcript word count: {original_word_count}")

            formatted_text = None

            for attempt in range(max_retries):
                status_msg = f"Formatting text (Attempt {attempt + 1}/{max_retries})..."
                logger.info(status_msg)
                # with self.console.status(status_msg, spinner=config.SPINNER):
                gemini_result = self._format_text(transcript_text)

                if not gemini_result.ok:
                    logger.error(
                        f"Gemini call failed (Attempt {attempt + 1}). Error: {gemini_result.error_message}"
                    )
                    if "quota" in str(gemini_result.error_message).lower():
                        self.console.print(
                            "[bold red]Gemini quota error. Aborting.[/bold red]"
                        )
                        return None
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    else:
                        self.console.print(
                            "[bold red]Gemini call failed after multiple retries. Aborting.[/bold red]"
                        )
                        return None

                # Gemini call was successful, now check word loss
                current_formatted_text = gemini_result.output
                current_formatted_text = re.sub(
                    r"\n+", "\n", current_formatted_text
                ).strip()

                formatted_word_count = self._count_words(current_formatted_text)

                word_loss_percentage = 0
                if original_word_count > 0:
                    word_loss_percentage = (
                        (original_word_count - formatted_word_count)
                        / original_word_count
                    ) * 100

                logger.debug(
                    f"Attempt {attempt + 1}: Formatted words: {formatted_word_count}, Word loss: {word_loss_percentage:.2f}%"
                )

                if word_loss_percentage <= word_loss_threshold:
                    logger.info(
                        f"Word loss ({word_loss_percentage:.2f}%) is within tolerance. Success."
                    )
                    formatted_text = current_formatted_text
                    break  # Success
                else:
                    logger.warning(
                        f"Word loss ({word_loss_percentage:.2f}%) exceeds threshold of {word_loss_threshold}%. Retrying..."
                    )
                    if attempt < max_retries - 1:
                        time.sleep(2)
                    else:
                        logger.error("Exceeded max retries due to high word loss.")
                        self.console.print(
                            "[bold red]Failed to format due to high word loss after multiple retries.[/bold red]"
                        )
                        return None

            if formatted_text is None:
                logger.error("Formatting failed after all retries. No result to save.")
                return None

            output_file_path = job_directory / config.FORMATED_TRANSCRIPT_NAME
            output_file_path.write_text(formatted_text, encoding="utf-8")

            logger.info(
                f"Formatted transcription saved to {output_file_path}. Returning path."
            )
            return output_file_path

        except Exception as e:
            logger.critical(
                f"An unexpected error occurred during formatting for {input_file_path}: {e}",
                exc_info=True,
            )
            self.console.print(
                f"  [bold red]An unexpected error occurred during formatting: {e}[/bold red]"
            )
            raise

    def _build_big_paragraph(self, text: str) -> str:
        """Removes all the extra spaces and new lines etc."""
        logger.debug(f"Building big paragraph from text (length: {len(text)}).")
        paragraph = " ".join(text.split())
        logger.debug(f"Big paragraph built (length: {len(paragraph)}).")
        return paragraph

    def _format_text(self, text: str):
        """
        Submits the text to Gemini for formatting and returns the result dataclass.
        """
        logger.debug(f"Calling Gemini for formatting text (length: {len(text)}).")
        prompt_path = Path(__file__).parent / "prompts/formatter/format-paragraph.txt"
        logger.debug(f"Loading prompt from: {prompt_path}")
        try:
            prompt_template = prompt_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.critical(f"Prompt file not found at {prompt_path}.", exc_info=True)
            raise  # Propagate this critical error

        clean_text = self._build_big_paragraph(text)
        prompt = prompt_template.format(SERMON_TEXT=clean_text)
        logger.debug(f"Prompt prepared (length: {len(prompt)}). Submitting to Gemini.")

        return self.gemini_client.submit_prompt(prompt)

    def _count_words(self, text: Optional[str]) -> int:
        """Counts the number of words in a given string."""
        if not text:
            logger.debug("Counting words in empty or None text. Result: 0")
            return 0
        count = len(text.split())
        logger.debug(f"Counted {count} words in text (length: {len(text)}).")
        return count
