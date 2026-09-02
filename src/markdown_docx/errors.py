from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_PARSE = 3
EXIT_TEMPLATE = 4
EXIT_ASSET = 5
EXIT_UNSUPPORTED = 6
EXIT_RENDER = 7
EXIT_INTERNAL = 8


@dataclass(slots=True)
class ErrorContext:
    code: str
    message: str
    exit_code: int
    line: int | None = None
    input_path: str | None = None
    metadata_kind: str | None = None
    details: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return {key: value for key, value in payload.items() if value is not None and key != "exit_code"}


class MarkdownDocxError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        exit_code: int,
        line: int | None = None,
        input_path: str | None = None,
        metadata_kind: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.context = ErrorContext(
            code=code,
            message=message,
            exit_code=exit_code,
            line=line,
            input_path=input_path,
            metadata_kind=metadata_kind,
            details=details,
        )


class UsageError(MarkdownDocxError):
    def __init__(self, message: str) -> None:
        super().__init__("usage_error", message, exit_code=EXIT_USAGE)


class InputError(MarkdownDocxError):
    def __init__(self, code: str, message: str, *, input_path: str | None = None) -> None:
        super().__init__(code, message, exit_code=EXIT_USAGE, input_path=input_path)


class ParseError(MarkdownDocxError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        line: int | None = None,
        input_path: str | None = None,
        metadata_kind: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code,
            message,
            exit_code=EXIT_PARSE,
            line=line,
            input_path=input_path,
            metadata_kind=metadata_kind,
            details=details,
        )


class TemplateError(MarkdownDocxError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(code, message, exit_code=EXIT_TEMPLATE, details=details)


class AssetError(MarkdownDocxError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        line: int | None = None,
        input_path: str | None = None,
    ) -> None:
        super().__init__(code, message, exit_code=EXIT_ASSET, line=line, input_path=input_path)


class UnsupportedFeatureError(MarkdownDocxError):
    def __init__(
        self,
        message: str,
        *,
        line: int | None = None,
        input_path: str | None = None,
        code: str = "unsupported_feature",
    ) -> None:
        super().__init__(code, message, exit_code=EXIT_UNSUPPORTED, line=line, input_path=input_path)


class RenderError(MarkdownDocxError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(code, message, exit_code=EXIT_RENDER, details=details)
