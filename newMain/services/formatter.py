"""
This module provides the Formatter class, which is responsible for taking raw transcription text
and applying paragraph breaks for improved readability. It implements a tiered approach,
attempting to use the Gemini AI for formatting first, with a fallback to the Ollama AI
if Gemini encounters issues (e.g., API quota, significant word count discrepancies).

The class handles text cleaning, AI interaction, word count integrity checks,
retries, and interactive user prompts for fallback decisions.
"""
import logging
from rich.console import Console
from rich.prompt import Prompt
from pathlib import Path
from typing import Optional, List, Tuple
import time
import re
import json

from joshlib.gemini import GeminiClient
from joshlib.ollama import OllamaClient, OllamaProcessingError
from config import config

# Set up the logger for this module.
logger = logging.getLogger(__name__)

# Silence verbose logging from external libraries to keep logs clean.
logging.getLogger("paramiko").setLevel(logging.WARNING)
logging.getLogger("cryptography").setLevel(logging.WARNING)


class Formatter:
    """
    Orchestrates the text formatting process, initially attempting with Gemini AI,
    and falling back to Ollama AI based on success criteria and user preference.
    It cleans text, manages AI calls, performs integrity checks, and handles retries.
    """
    def __init__(self):
        """
        Initializes the Formatter with Rich Console for CLI output,
        OllamaClient for local LLM interactions, and GeminiClient for Google's AI.
        """
        self.console = Console()
        # Initialize Ollama client with a specific model and temperature for paragraphing.
        self.ollama_client = OllamaClient(model="llama3.2:3b", temperature=0.1)
        # Initialize Gemini client for potentially higher quality formatting.
        self.gemini_client = GeminiClient()
        # Configuration for Ollama's sentence-based chunking.
        self.sentence_chunk_size = 25
        self.context_paragraph_count = 1
        logger.debug("Formatter initialized.")

    def _clean_text(self, text: str) -> str:
        """
        Cleans the raw transcript text by fixing hard line breaks and collapsing
        multiple whitespace characters into single spaces. This prepares the text
        for AI processing by making it a continuous block.

        Args:
            text (str): The raw input text from the transcription.

        Returns:
            str: The cleaned text, suitable for AI processing.
        """
        # Remove single hard line breaks, converting them to spaces.
        # This preserves paragraph breaks (double newlines) but cleans up accidental line wraps.
        text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

        # Collapse any sequence of whitespace characters (including newlines and tabs)
        # into a single space and remove leading/trailing whitespace.
        # This ensures the text is effectively a "one big block" for the Gemini prompt.
        text = re.sub(r"\s+", " ", text).strip()

        # Removed: Deduplication logic for repetitive stutters, as per user request
        # to preserve original phrasing and rhetorical impact.

        return text

    def run(self, job_directory: Path, input_file_path: Path) -> Optional[Path]:
        """
        Executes the main formatting workflow. It first attempts to use Gemini,
        and if that fails or produces an unsatisfactory result (based on word count),
        it offers a fallback to Ollama, potentially after multiple Gemini retries.

        Args:
            job_directory (Path): The directory for the current job, where output will be saved.
            input_file_path (Path): The path to the raw (or whisper-transcribed) text file.

        Returns:
            Optional[Path]: The path to the formatted output file if successful, otherwise None.
        """
        try:
            raw_text = input_file_path.read_text(encoding="utf-8")

            # Prepare the text: remove weird mid-sentence breaks and make it one big block.
            clean_text = self._clean_text(raw_text)
            
            # Initialize variables for the Gemini retry loop.
            max_gemini_attempts = 3
            formatted_text = None
            last_attempt_result = None
            original_word_count = len(clean_text.split())

            # Tier 1: Attempt Gemini formatting with retries for word count integrity.
            for attempt in range(1, max_gemini_attempts + 1):
                logger.info(f"Attempting Gemini formatting (Attempt {attempt}/{max_gemini_attempts}).")
                self.console.print(f"[bold green]Attempting Gemini formatting (Attempt {attempt}/{max_gemini_attempts})...[/bold green]")
                
                # Call Gemini for formatting.
                temp_formatted = self._run_gemini_formatting(clean_text)
                
                if temp_formatted:
                    last_attempt_result = temp_formatted
                    # Perform an integrity check: Compare word counts to detect significant changes.
                    formatted_word_count = len(temp_formatted.split())
                    
                    variance = 0
                    if original_word_count > 0:
                        variance = abs(original_word_count - formatted_word_count) / original_word_count
                    
                    if variance <= 0.02:  # If variance is within the 2% threshold, we accept the result.
                        formatted_text = temp_formatted
                        logger.info("Gemini formatting successful (within word count threshold).")
                        self.console.print("[bold green]Gemini formatting successful![/bold green]")
                        break  # Exit the retry loop as a satisfactory result was obtained.
                    else:
                        logger.warning(f"Attempt {attempt} word count variance too high: {variance:.2%}")
                        self.console.print(f"[bold yellow]Warning: Attempt {attempt} resulted in a {variance:.2%} change in word count ({formatted_word_count} vs {original_word_count} words).[/bold yellow]")
                else:
                    logger.warning(f"Attempt {attempt} failed to return a result from Gemini.")

                # If not the last attempt, pause before retrying.
                if attempt < max_gemini_attempts:
                    self.console.print(f"[bold yellow]Sleeping for 15 seconds before attempt {attempt + 1}...[/bold yellow]")
                    time.sleep(15)

            # If after all Gemini attempts, we still don't have a satisfactory formatted_text.
            if not formatted_text:
                logger.warning("All Gemini formatting attempts failed (or threshold exceeded).")
                self.console.print("[bold red]Gemini formatting failed or was rejected after 3 attempts.[/bold red]")
                
                # If Gemini did return a result, even if it failed the threshold, offer to proceed with it.
                if last_attempt_result:
                    gemini_count = len(last_attempt_result.split())
                    diff = gemini_count - original_word_count
                    # Prompt user to accept the high-variance Gemini result or discard it.
                    if Prompt.ask(
                        f"[bold yellow]Word count mismatch detected. Gemini: {gemini_count} Original: {original_word_count}. Difference: {diff} words. Proceed?[/bold yellow]",
                        choices=["y", "n"],
                        default="n"
                    ).lower() == "y":
                        formatted_text = last_attempt_result  # User chose to accept the divergent Gemini result.
                
                # If we still don't have formatted_text (either no Gemini result or user rejected it).
                if not formatted_text:
                    # Tier 2: Offer Ollama as a fallback.
                    if Prompt.ask(
                        "[bold cyan]Would you like to use Ollama as a fallback for formatting?[/bold cyan]",
                        choices=["y", "n"],
                        default="y"
                    ).lower() == "y":
                        logger.info("User opted for Ollama fallback.")
                        self.console.print("[bold blue]Starting Ollama fallback formatting (this may take a while)...[/bold blue]")
                        paragraphs = self._run_ollama_formatting(clean_text)
                        if paragraphs:
                            formatted_text = "\n\n".join(paragraphs)
                            self.console.print("[bold green]Ollama fallback successful.[/bold green]")
                        else:
                            logger.error("Ollama fallback also failed.")
                            self.console.print("[bold red]Ollama fallback failed.[/bold red]")
                            return None  # Ollama fallback also failed.
                    else:
                        logger.info("User declined Ollama fallback.")
                        return None  # User declined all formatting options.

            # Save the final formatted text to a file.
            output_path = job_directory / "formatted_transcript.txt"
            output_path.write_text(formatted_text, encoding="utf-8")

            logger.info(f"Done! Saved to: {output_path.name}")
            return output_path

        except Exception as e:
            logger.exception("An unexpected error occurred during the formatting process.")
            raise

    def _run_gemini_formatting(self, text: str) -> Optional[str]:
        """
        Submits the entire cleaned text block to Gemini for paragraph formatting.

        Args:
            text (str): The cleaned, continuous text to be formatted.

        Returns:
            Optional[str]: The Gemini-formatted text if successful, otherwise None.
        """
        # Construct the path to the Gemini prompt file.
        prompt_path = Path(__file__).parent / "prompts" / "formatter" / "gemini-format-paragraphs.txt"
        if not prompt_path.exists():
            logger.error(f"Gemini prompt file not found at {prompt_path}")
            return None
            
        # Read the prompt template and inject the sermon text.
        prompt_template = prompt_path.read_text(encoding="utf-8")
        prompt = prompt_template.format(SERMON_TEXT=text)
        
        try:
            # Submit the prompt to the Gemini client.
            # retries=1 is set here because the Formatter.run method handles higher-level retries.
            result = self.gemini_client.submit_prompt(prompt, retries=1)
            if result.ok:
                return result.output
            else:
                logger.error(f"Gemini formatting failed: {result.error_message}")
                # Provide user feedback if a quota error is explicitly detected.
                if "quota" in str(result.error_message).lower():
                    self.console.print("[bold red]Gemini API quota exceeded.[/bold red]")
                return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during the Gemini formatting call: {e}")
            return None

    def _run_ollama_formatting(self, clean_text: str) -> Optional[List[str]]:
        """
        Implements the original Ollama paragraphing logic as a fallback.
        It breaks the text into sentences, processes them in chunks, and uses Ollama
        to determine optimal paragraph breaks.

        Args:
            clean_text (str): The cleaned, continuous text to be formatted by Ollama.

        Returns:
            Optional[List[str]]: A list of formatted paragraphs if successful, otherwise None.
        """
        # Split the cleaned text into individual sentences.
        sentences = self._split_into_sentences(clean_text)
        if not sentences:
            logger.warning("No sentences found for Ollama formatting.")
            return None

        paragraphs: List[str] = []
        current_idx = 0
        total = len(sentences)

        try:
            # Loop through sentences, sending chunks to Ollama for paragraph breaking decisions.
            while current_idx < total:
                logger.info(
                    f"Processing: {current_idx}/{total} sentences for paragraphing (Ollama)."
                )

                chunk = sentences[current_idx : current_idx + self.sentence_chunk_size]
                # Provide context from previous paragraphs to help Ollama make better decisions.
                context = paragraphs[-self.context_paragraph_count :]

                prompt = self._build_ollama_prompt(context, chunk)

                try:
                    ollama_response = self.ollama_client.submit_prompt(prompt)
                    if ollama_response.ok:
                        response_text = ollama_response.output
                        # Parse Ollama's response to get the sentence index for the paragraph break.
                        break_offset = self._parse_ollama_response(
                            response_text, len(chunk)
                        )
                    else:
                        error_message = (
                            ollama_response.error_message
                            or "Unknown Ollama error during formatting."
                        )
                        logger.error(
                            f"Ollama formatting failed at sentence {current_idx}: {error_message}"
                        )
                        # If Ollama fails, append the rest of the text as one paragraph and break.
                        paragraphs.append(" ".join(sentences[current_idx:]).strip())
                        break

                    # Logic Guard: Avoid creating very short 1-2 sentence paragraphs unless
                    # the topic truly dictates it or it's the end of the text.
                    if (
                        break_offset is not None
                        and break_offset < 3
                        and (current_idx + break_offset < total)
                    ):
                        move_by = len(chunk) # Take the whole chunk if break is too short.
                    elif break_offset and break_offset > 0:
                        move_by = break_offset # Use Ollama's suggested break point.
                    else:
                        move_by = len(chunk) # Default: take the whole chunk.

                    # Join the sentences to form a new paragraph and add to the list.
                    new_para = " ".join(sentences[current_idx : current_idx + move_by])
                    paragraphs.append(new_para.strip())
                    current_idx += move_by # Advance the current index.

                except Exception as e:
                    logger.error(f"An error occurred at sentence {current_idx} during Ollama processing: {e}")
                    paragraphs.append(" ".join(sentences[current_idx:]).strip())
                    break
            
            return paragraphs
        except Exception as e:
            logger.error(f"The Ollama formatting loop encountered an unexpected error: {e}")
            return None

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Splits a continuous block of text into a list of sentences.
        Sentences are primarily split by periods, exclamation marks, or question marks.

        Args:
            text (str): The input text.

        Returns:
            List[str]: A list of individual sentences.
        """
        # Split on '.', '!', or '?' followed by a space, and strip whitespace from each resulting sentence.
        return [s.strip() for s in re.split(r"(?<=[.?!])\s+", text) if s.strip()]

    def _build_ollama_prompt(self, context_paras: List[str], chunk: List[str]) -> str:
        """
        Constructs the prompt for Ollama, instructing it to identify the best
        paragraph break point within a given chunk of sentences, considering prior context.

        Args:
            context_paras (List[str]): Previously generated paragraphs for context.
            chunk (List[str]): The current list of sentences to evaluate for a paragraph break.

        Returns:
            str: The formatted prompt for Ollama.
        """
        prompt = [
            "### INSTRUCTION",
            "You are an editor. Identify the best index to start a NEW paragraph based on topic shifts.",
            "Avoid creating very short paragraphs (less than 3 sentences) unless the topic completely changes.",
            "",
        ]

        if context_paras:
            prompt.append("### PREVIOUS CONTEXT")
            prompt.append(context_paras[-1])  # Only the last context paragraph is usually sufficient.
            prompt.append("---")

        prompt.append("### SENTENCES")
        for i, s in enumerate(chunk):
            prompt.append(f"{i}: {s}")

        prompt.append("\n### RESPONSE")
        # Ollama is instructed to respond only with an index number.
        prompt.append(f"Respond ONLY with the index number (0-{len(chunk)-1}).")
        prompt.append(f"If no break is needed, respond with {len(chunk)}.")

        return "\n".join(prompt)

    def _parse_ollama_response(self, response: str, max_val: int) -> Optional[int]:
        """
        Parses Ollama's response to extract the integer representing the desired
        paragraph break point.

        Args:
            response (str): The raw text response from Ollama.
            max_val (int): The maximum valid index that Ollama can return (length of the chunk).

        Returns:
            Optional[int]: The parsed integer index, or None if no valid number is found.
        """
        # Extract the first integer number found in the response string.
        match = re.search(r"\b\d+\b", response.strip())
        if match:
            val = int(match.group(0))
            # Ensure the returned value is within valid bounds.
            return min(max(0, val), max_val)
        return None
