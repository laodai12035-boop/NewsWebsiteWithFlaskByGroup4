from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Iterable

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


@dataclass(frozen=True)
class UploadResult:
    ok: bool
    error: str | None = None
    # Stored as a static-relative path, e.g. "uploads/abc.png"
    static_path: str | None = None


def _allowed_ext(filename: str, allowed_exts: Iterable[str]) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in {e.lower().lstrip(".") for e in allowed_exts}


def save_image_upload(file: FileStorage | None) -> UploadResult:
    """Save an uploaded image into `static/uploads/` with basic validation."""
    if not file or not file.filename:
        return UploadResult(ok=True, static_path=None)

    allowed_exts = current_app.config.get(
        "ALLOWED_IMAGE_EXTENSIONS", {"png", "jpg", "jpeg", "webp", "gif"}
    )
    max_size = int(current_app.config.get("MAX_IMAGE_BYTES", 2 * 1024 * 1024))

    filename = secure_filename(file.filename)
    if not _allowed_ext(filename, allowed_exts):
        return UploadResult(ok=False, error="Định dạng ảnh không hợp lệ (png/jpg/jpeg/webp/gif).")

    # Validate size (read stream length without loading entire file if possible).
    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > max_size:
        return UploadResult(ok=False, error=f"Ảnh quá lớn. Tối đa {max_size // (1024 * 1024)}MB.")

    ext = filename.rsplit(".", 1)[1].lower()
    new_name = f"{uuid.uuid4().hex}.{ext}"

    upload_dir = os.path.join(current_app.static_folder, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    abs_path = os.path.join(upload_dir, new_name)
    file.save(abs_path)
    return UploadResult(ok=True, static_path=f"uploads/{new_name}")

