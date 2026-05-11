from __future__ import annotations

import logging
from pathlib import Path

import pymupdf

logger = logging.getLogger(__name__)


class TextExtractor:
    """Extracts raw text content from files.

    Supports PDF (via PyMuPDF) and plain text files.
    Easily extensible for DOCX, HTML, etc.
    """

    SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}

    def extract(self, file_path: Path) -> str:
        """Extract text from a file based on its extension.

        Raises ValueError for unsupported file types.
        """
        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            return self._extract_pdf(file_path)
        elif suffix in {".txt", ".md"}:
            return self._extract_text(file_path)
        else:
            raise ValueError(
                f"Unsupported file type: {suffix}. "
                f"Supported: {self.SUPPORTED_EXTENSIONS}"
            )

    def _extract_pdf(self, file_path: Path) -> str:
        """Extract text from PDF using PyMuPDF."""
        logger.info("Extracting PDF: %s", file_path.name)
        doc = pymupdf.open(str(file_path))

        pages: list[str] = []
        for page in doc:
            text = page.get_text()
            if text.strip():
                pages.append(text)

        doc.close()

        full_text = "\n\n".join(pages)
        logger.info("Extracted %d chars from %d pages", len(full_text), len(pages))
        return full_text

    @staticmethod
    def _extract_text(file_path: Path) -> str:
        """Read plain text or markdown files."""
        logger.info("Reading text file: %s", file_path.name)
        return file_path.read_text(encoding="utf-8")
