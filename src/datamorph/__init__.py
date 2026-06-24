"""DataMorph package — batch format converter with streaming."""
from .converters import (
    ConversionResult,
    ValidationResult,
    convert,
    convert_batch,
    detect_format,
    supported_formats,
    validate,
)
from . import __version__

__all__ = [
    "__version__",
    "convert",
    "convert_batch",
    "validate",
    "detect_format",
    "supported_formats",
    "ConversionResult",
    "ValidationResult",
]
