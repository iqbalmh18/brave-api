# Referensi API

Bagian ini dibuat otomatis dari docstring dan signature package. API publik
tersedia dari `brave_api`; gunakan `BraveClient` sebagai pintu masuk utama,
`ClientConfig` untuk pengaturan, model untuk hasil typed, dan exception untuk
penanganan kegagalan.

## Client utama

- `BraveClient`: `open()`, `close()`, `health_check()`, `ask()`,
  `ask_stream()`, `conversation()`, `search()`, `search_images()`,
  `search_news()`, `search_videos()`, `search_goggles()`, dan `suggest()`.
- `ClientConfig`: konfigurasi immutable untuk URL, bahasa, lokasi, safe search,
  timeout, retry, concurrency, header, dan proxy.
- `Conversation`: lifecycle percakapan, `collect()`, dan `stream_events()`.

## Model hasil

`StreamResult`, `StreamEvent`, `ConversationResponse`, `SearchResult`,
`WebResult`, `NewsResult`, `ImageResult`, `VideoResult`, `Infobox`,
`SuggestResult`, dan `SuggestItem` adalah model Pydantic typed. Baca field
masing-masing melalui dot notation atau `.model_dump()`.

## Enum dan exception

Enum publik meliputi `QueryType`, `SearchType`, `StreamEventType`, dan
`StreamState`. Semua error berakar pada `BraveAPIError`; subclass pentingnya
adalah `HTTPStatusError`, `TransportError`, `ResponseParseError`,
`ConversationError`, `ChallengeRequiredError`, `StreamAbortedError`, dan
`TokenExtractionError`.

Signature dan docstring lengkap tersedia di [English API Reference](api.md).

Referensi API lengkap dihasilkan langsung dari type hint dan docstring source
code. Gunakan [API Reference bahasa Inggris](https://brave-api.readthedocs.io/api/)
untuk daftar class, method, model, enum, dan exception lengkap.

Ruang lingkup utama:

- `BraveClient` untuk Ask, percakapan, dan search verticals.
- Konfigurasi endpoint, token, timeout, retry, proxy, dan locale.
- Model Pydantic untuk response web, image, news, video, dan Goggles.
- Hierarki exception untuk error request, response, autentikasi, dan parsing.
