"""
Multimodal utilities for Microsoft Agent Framework.

Based on: azure_responses_multimodal.py sample
"""

import base64
from pathlib import Path
from typing import Optional


def load_pdf_from_file(pdf_path: str) -> bytes:
    """
    Load PDF file from disk.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        PDF file contents as bytes
        
    Raises:
        FileNotFoundError: If PDF file doesn't exist
        IOError: If file can't be read
    """
    pdf_file = Path(pdf_path)
    
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    if not pdf_file.suffix.lower() == '.pdf':
        raise ValueError(f"File is not a PDF: {pdf_path}")
    
    try:
        with open(pdf_file, 'rb') as f:
            return f.read()
    except Exception as e:
        raise IOError(f"Could not read PDF file {pdf_path}: {e}")


def load_sample_pdf() -> bytes:
    """Load the sample PDF from the data directory."""
    data_dir = Path(__file__).parent.parent / "data"
    pdf_file = data_dir / "MSFT 2025 10K.pdf"
    
    return load_pdf_from_file(str(pdf_file))


def create_sample_image_data_uri() -> str:
    """Create a simple base64 image for testing multimodal capabilities."""
    # Simple 1x1 red pixel in PNG format (base64 encoded)
    png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    return f"data:image/png;base64,{png_base64}"


def load_image_from_file(image_path: str) -> str:
    """
    Load image file and convert to data URI.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Data URI string for the image
    """
    image_file = Path(image_path)
    
    if not image_file.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Determine MIME type from extension
    extension = image_file.suffix.lower()
    mime_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp'
    }
    
    mime_type = mime_types.get(extension, 'application/octet-stream')
    
    try:
        with open(image_file, 'rb') as f:
            image_data = f.read()
            base64_data = base64.b64encode(image_data).decode('utf-8')
            return f"data:{mime_type};base64,{base64_data}"
    except Exception as e:
        raise IOError(f"Could not read image file {image_path}: {e}")


def get_data_directory() -> Path:
    """Get the data directory path."""
    return Path(__file__).parent.parent / "data"


def list_available_files() -> dict[str, list[str]]:
    """List all available files in the data directory by type."""
    data_dir = get_data_directory()
    
    if not data_dir.exists():
        return {"pdfs": [], "images": [], "other": []}
    
    files = {"pdfs": [], "images": [], "other": []}
    
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
    
    for file_path in data_dir.iterdir():
        if file_path.is_file():
            extension = file_path.suffix.lower()
            if extension == '.pdf':
                files["pdfs"].append(file_path.name)
            elif extension in image_extensions:
                files["images"].append(file_path.name)
            else:
                files["other"].append(file_path.name)
    
    return files