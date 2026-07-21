from __future__ import annotations

from app.schemas.common import IdentifiedDto


class MediaAssetDto(IdentifiedDto):
    name: str
    mimeType: str
    sizeBytes: int
    url: str
