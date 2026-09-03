"""Errors raised by the PT converter."""


class PTConverterError(Exception):
    """Base class for errors that should be shown without a traceback."""


class ConfigurationError(PTConverterError):
    """The converter configuration is missing or invalid."""


class SourceReadError(PTConverterError):
    """A required source file or object could not be read."""


class TranslationError(PTConverterError):
    """Source information could not be translated safely."""


class ValidationError(PTConverterError):
    """Converted information failed a validation rule."""


class OutputWriteError(PTConverterError):
    """An output could not be written safely."""
