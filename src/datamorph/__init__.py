"""DataMorph package — batch format converter with streaming."""

__version__ = "0.1.1"
from .converters import (
    ConversionResult,
    ValidationResult,
    convert,
    convert_batch,
    detect_format,
    supported_formats,
    validate,
)

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
