import logging
from rich.console import Console
from pathlib import Path
from typing import Optional, List, Tuple
import time
import re
import json

from joshlib.gemini import GeminiClient
from joshlib.ollama import OllamaClient, OllamaProcessingError
from config import config

# set up the logging
logger = logging.getLogger(__name__)

# Silence paramiko's verbose logging and cryptography
logging.getLogger("paramiko").setLevel(logging.WARNING)
logging.getLogger("cryptography").setLevel(logging.WARNING)


# Rename OllamaFormatter to Formatter
class Formatter: # Renamed from OllamaFormatter
    def __init__(self):
        self.console = Console()
        self.ollama_client = OllamaClient(model='llama3.2:3b', temperature=0.1)
        self.sentence_chunk_size = 25
        self.context_paragraph_count = 1
        logger.debug("Formatter initialized (formerly OllamaFormatter).")

    def _clean_text(self, text: str) -> str:
        """Fixes hard line breaks, repetitive 'stutters', and extra whitespace."""
        # 1. Remove hard line breaks (single newlines)
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
        
        # 2. Collapse all whitespace into single spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 3. Deduplicate exact sentence stutters (common in sermon AI transcripts)
        # Finds phrases repeated 2-3 times in a row and keeps only one.
        text = re.sub(r'(.+?)\1+', r'\1', text)
        
        return text

    def run(self, job_directory: Path, input_file_path: Path) -> Optional[Path]:
        try:
            raw_text = input_file_path.read_text(encoding="utf-8")
            
            # Normalize the text to remove weird mid-sentence breaks
            clean_text = self._clean_text(raw_text)
            sentences = self._split_into_sentences(clean_text)
            
            if not sentences:
                logger.warning(f"No sentences found in {input_file_path.name}")
                return None

            paragraphs: List[str] = []
            current_idx = 0
            total = len(sentences)
            
            # Removed nested rich.console.status to prevent flickering
            while current_idx < total:
                logger.info(f"Processing: {current_idx}/{total} sentences for paragraphing.")
                
                chunk = sentences[current_idx : current_idx + self.sentence_chunk_size]
                context = paragraphs[-self.context_paragraph_count:]
                
                prompt = self._build_ollama_prompt(context, chunk)
                
                try:
                    response = self.ollama_client.submit_prompt(prompt)
                    break_offset = self._parse_ollama_response(response, len(chunk))
                    
                    # Logic Guard: Avoid tiny 1-2 sentence paragraphs unless necessary
                    if break_offset is not None and break_offset < 3 and (current_idx + break_offset < total):
                        # If it's a very small break, just take the whole chunk to maintain flow
                        move_by = len(chunk)
                    elif break_offset and break_offset > 0:
                        move_by = break_offset
                    else:
                        move_by = len(chunk)
                    
                    # Join and save paragraph
                    new_para = " ".join(sentences[current_idx : current_idx + move_by])
                    paragraphs.append(new_para.strip())
                    
                    current_idx += move_by
                    
                except Exception as e:
                    logger.error(f"Error at sentence {current_idx}: {e}")
                    # Fallback: dump the rest and exit
                    paragraphs.append(" ".join(sentences[current_idx:]).strip())
                    break

            # Save with double spacing
            formatted_text = "\n\n".join(paragraphs)
            output_path = job_directory / "formatted_transcript.txt"
            output_path.write_text(formatted_text, encoding="utf-8")
            
            logger.info(f"Done! Saved to: {output_path.name}")
            return output_path

        except Exception as e:
            logger.exception("Formatter failed")
            raise

    def _split_into_sentences(self, text: str) -> List[str]:
        # Split on . ! or ? followed by a space
        return [s.strip() for s in re.split(r'(?<=[.?!])\s+', text) if s.strip()]

    def _build_ollama_prompt(self, context_paras: List[str], chunk: List[str]) -> str:
        prompt = [
            "### INSTRUCTION",
            "You are an editor. Identify the best index to start a NEW paragraph based on topic shifts.",
            "Avoid creating very short paragraphs (less than 3 sentences) unless the topic completely changes.",
            ""
        ]
        
        if context_paras:
            prompt.append("### PREVIOUS CONTEXT")
            prompt.append(context_paras[-1])
            prompt.append("---")
            
        prompt.append("### SENTENCES")
        for i, s in enumerate(chunk):
            prompt.append(f"{i}: {s}")
            
        prompt.append("\n### RESPONSE")
        prompt.append(f"Respond ONLY with the index number (0-{len(chunk)-1}).")
        prompt.append(f"If no break is needed, respond with {len(chunk)}.")
        
        return "\n".join(prompt)

    def _parse_ollama_response(self, response: str, max_val: int) -> Optional[int]:
        # Extract the first number found in the response
        match = re.search(r'\b\d+\b', response.strip())
        if match:
            val = int(match.group(0))
            return min(max(0, val), max_val)
        return None
