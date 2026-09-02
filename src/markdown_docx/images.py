from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx
from PIL import Image, UnidentifiedImageError

from markdown_docx.errors import AssetError
from markdown_docx.metadata import EMU_PER_INCH
from markdown_docx.models import ImageOptions

MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
MAX_IMAGE_PIXELS = 50_000_000
DOWNLOAD_TIMEOUT_SECONDS = 15.0


@dataclass(slots=True, frozen=True)
class ImageAsset:
    data: bytes
    natural_width: int
    natural_height: int


class ImageLoader:
    def __init__(self, base_dir: Path, *, allow_remote: bool) -> None:
        self.base_dir = base_dir
        self.allow_remote = allow_remote
        self.cache: dict[str, ImageAsset] = {}

    def load(self, source: str, *, line: int, input_path: str | None) -> ImageAsset:
        if source in self.cache:
            return self.cache[source]
        if source.startswith(("http://", "https://")):
            if not self.allow_remote:
                raise AssetError(
                    "image_download_failed",
                    f"Remote images are disabled: {_safe_url(source)}",
                    line=line,
                    input_path=input_path,
                )
            data = self._download(source, line=line, input_path=input_path)
        else:
            path = Path(source)
            if not path.is_absolute():
                path = self.base_dir / path
            path = path.resolve()
            if not path.is_file():
                raise AssetError("image_not_found", f"Image does not exist: {path}", line=line, input_path=input_path)
            if path.stat().st_size > MAX_DOWNLOAD_BYTES:
                raise AssetError(
                    "image_too_large", f"Image exceeds the 25 MiB limit: {path}", line=line, input_path=input_path
                )
            data = path.read_bytes()
        asset = _decode_image(data, source=source, line=line, input_path=input_path)
        self.cache[source] = asset
        return asset

    def _download(self, source: str, *, line: int, input_path: str | None) -> bytes:
        safe_source = _safe_url(source)
        try:
            with httpx.Client(follow_redirects=True, timeout=DOWNLOAD_TIMEOUT_SECONDS) as client:
                with client.stream("GET", source) as response:
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                    if not content_type.startswith("image/"):
                        raise AssetError(
                            "image_download_failed",
                            f"Remote image response is not an image: {safe_source}",
                            line=line,
                            input_path=input_path,
                        )
                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > MAX_DOWNLOAD_BYTES:
                        raise AssetError(
                            "image_too_large",
                            f"Remote image exceeds the 25 MiB limit: {safe_source}",
                            line=line,
                            input_path=input_path,
                        )
                    chunks: list[bytes] = []
                    total = 0
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > MAX_DOWNLOAD_BYTES:
                            raise AssetError(
                                "image_too_large",
                                f"Remote image exceeds the 25 MiB limit: {safe_source}",
                                line=line,
                                input_path=input_path,
                            )
                        chunks.append(chunk)
                    return b"".join(chunks)
        except AssetError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise AssetError(
                "image_download_failed",
                f"Could not download image: {safe_source}",
                line=line,
                input_path=input_path,
            ) from exc


def rendered_width(asset: ImageAsset, options: ImageOptions, *, usable_width: int, line: int, input_path: str) -> int:
    if options.width is None:
        return min(asset.natural_width, usable_width)
    if options.width_is_percent:
        return round(usable_width * float(options.width) / 100)
    width = int(options.width)
    if width > usable_width:
        raise AssetError(
            "image_too_wide",
            "Explicit image width exceeds the active section's usable width.",
            line=line,
            input_path=input_path,
        )
    return width


def _decode_image(data: bytes, *, source: str, line: int, input_path: str | None) -> ImageAsset:
    try:
        with Image.open(BytesIO(data)) as image:
            width_px, height_px = image.size
            if width_px * height_px > MAX_IMAGE_PIXELS:
                raise AssetError(
                    "image_too_large",
                    f"Image exceeds the 50 megapixel limit: {_safe_source(source)}",
                    line=line,
                    input_path=input_path,
                )
            dpi = image.info.get("dpi", (72, 72))
            dpi_x = float(dpi[0]) if isinstance(dpi, tuple) and dpi and dpi[0] else 72.0
            dpi_y = float(dpi[1]) if isinstance(dpi, tuple) and len(dpi) > 1 and dpi[1] else dpi_x
            image.verify()
    except AssetError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, TypeError) as exc:
        raise AssetError(
            "image_invalid",
            f"Image is corrupt or uses an unsupported format: {_safe_source(source)}",
            line=line,
            input_path=input_path,
        ) from exc
    natural_width = max(1, round(width_px / dpi_x * EMU_PER_INCH))
    natural_height = max(1, round(height_px / dpi_y * EMU_PER_INCH))
    return ImageAsset(data=data, natural_width=natural_width, natural_height=natural_height)


def _safe_url(url: str) -> str:
    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, host, parts.path, parts.query, parts.fragment))


def _safe_source(source: str) -> str:
    return _safe_url(source) if source.startswith(("http://", "https://")) else source
