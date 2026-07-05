from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class TokenModel(BaseModel):
    q: str = Field(description="Query string yang di-hash")
    nonce: str = Field(description="Nonce unik untuk request")
    sig: str = Field(description="Signature untuk validasi")

    model_config = {"frozen": True}


class ConversationResponse(BaseModel):
    id: str = Field(description="ID percakapan unik")
    symmetric_key: str | None = Field(default=None, description="Kunci enkripsi simetris untuk percakapan ini")
    bo_callback_share_link: str | None = Field(default=None, description="Link untuk share percakapan")
    bo_callback_open_modal: str | None = Field(default=None, description="Link untuk buka modal")

    model_config = {"frozen": True}


class SignedParams(BaseModel):
    conversation: str = Field(description="ID percakapan")
    index: int = Field(description="Index tool call")
    q: str = Field(description="Query")
    sig: str = Field(description="Signature")
    nonce: str = Field(description="Nonce")

    model_config = {"frozen": True}


class ToolUseEvent(BaseModel):
    type: Literal["tool_use"] = "tool_use"
    id: str = Field(description="ID unik tool use")
    name: str = Field(description="Nama tool yang dipanggil")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Argumen tool")
    signed_params: SignedParams = Field(description="Parameter yang ditandatangani")


class Infobox(BaseModel):
    """Entity card yang ditampilkan browser di sisi response (misal panel Wikipedia)."""

    title: str | None = Field(default=None, description="Nama entitas")
    subtitle: str | None = Field(default=None, description="Deskripsi singkat entitas")
    image_url: str | None = Field(default=None, description="URL gambar entitas")
    url: str | None = Field(default=None, description="URL sumber utama (misal Wikipedia)")
    description: str | None = Field(default=None, description="Deskripsi panjang entitas")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Atribut tambahan entitas")


class ImageResult(BaseModel):
    url: str = Field(description="URL gambar")
    title: str | None = Field(default=None, description="Judul gambar")
    thumbnail: str | None = Field(default=None, description="URL thumbnail")
    source: str | None = Field(default=None, description="Sumber gambar")
    width: int | None = Field(default=None, description="Lebar gambar")
    height: int | None = Field(default=None, description="Tinggi gambar")

    @field_validator("url", "thumbnail")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("URL harus dimulai dengan http:// atau https://")
        return v


class WebResult(BaseModel):
    url: str = Field(description="URL halaman web")
    title: str | None = Field(default=None, description="Judul halaman")
    description: str | None = Field(default=None, description="Deskripsi halaman")
    favicon: str | None = Field(default=None, description="URL favicon")
    thumbnail: str | None = Field(default=None, description="URL thumbnail gambar halaman")
    thumbnail_original: str | None = Field(default=None, description="URL thumbnail gambar asli (sebelum resize)")


class VideoResult(BaseModel):
    url: str = Field(description="URL video")
    title: str | None = Field(default=None, description="Judul video")
    thumbnail: str | None = Field(default=None, description="URL thumbnail video")
    duration: str | None = Field(default=None, description="Durasi video")
    channel: str | None = Field(default=None, description="Channel video")


class SearchWebResult(BaseModel):
    """Satu item hasil pencarian web dari SERP Brave Search."""

    url: str = Field(description="URL halaman")
    title: str | None = Field(default=None, description="Judul halaman")
    description: str | None = Field(default=None, description="Deskripsi/snippet halaman")
    favicon: str | None = Field(default=None, description="URL favicon")
    age: str | None = Field(default=None, description="Umur konten (misal '2 days ago')")
    extra_snippets: list[str] = Field(default_factory=list, description="Snippet tambahan jika ada")


class SearchNewsResult(BaseModel):
    """Satu item berita dari SERP Brave Search."""

    url: str = Field(description="URL berita")
    title: str | None = Field(default=None, description="Judul berita")
    description: str | None = Field(default=None, description="Deskripsi berita")
    age: str | None = Field(default=None, description="Umur berita")
    thumbnail: str | None = Field(default=None, description="URL thumbnail berita")
    source: str | None = Field(default=None, description="Nama sumber/outlet berita")


class SuggestItem(BaseModel):
    """Satu item saran pencarian dari /api/suggest."""

    text: str = Field(description="Teks saran")
    is_entity: bool = Field(default=False, description="Apakah saran ini adalah entitas (orang/tempat/dll)")
    thumbnail: str | None = Field(default=None, description="URL thumbnail entitas jika ada")
    entity_type: str | None = Field(default=None, description="Tipe entitas (Person, Place, dll)")


class SearchResult(BaseModel):
    """Kumpulan hasil dari satu request search ke Brave Search SERP."""

    query: str = Field(description="Query yang digunakan")
    web: list[SearchWebResult] = Field(default_factory=list, description="Hasil web organik")
    news: list[SearchNewsResult] = Field(default_factory=list, description="Hasil berita")
    offset: int = Field(default=0, description="Offset halaman yang digunakan")

    @property
    def has_results(self) -> bool:
        return bool(self.web or self.news)

    @property
    def urls(self) -> list[str]:
        """Semua URL dari hasil web."""
        return [r.url for r in self.web]


__all__ = [
    "ConversationResponse",
    "ImageResult",
    "Infobox",
    "SearchNewsResult",
    "SearchResult",
    "SearchWebResult",
    "SignedParams",
    "SuggestItem",
    "TokenModel",
    "ToolUseEvent",
    "VideoResult",
    "WebResult",
]
