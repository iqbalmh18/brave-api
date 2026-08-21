# Troubleshooting dan keandalan

## Periksa koneksi

`health_check()` melakukan pemeriksaan ringan dan mengembalikan `False` jika
base URL tidak dapat dijangkau:

```python
async with BraveClient() as client:
    if not await client.health_check():
        raise RuntimeError("Brave Search tidak dapat dijangkau")
```

Ini hanya membuktikan bahwa base URL merespons, bukan menjamin semua operasi
Ask atau Search berhasil.

## Lifecycle client

Pola yang disarankan:

```python
async with BraveClient() as client:
    result = await client.search("Python")
```

Untuk aplikasi dengan lifecycle sendiri, panggil `open()` sekali dan `close()`
saat shutdown. Jangan membuat client baru untuk setiap item loop; gunakan satu
client agar session HTTP, retry, batas concurrency, dan proxy pool dapat dipakai
ulang. `client.is_open` menunjukkan status session.

## Error dan retry

Error transient yang sesuai akan dicoba ulang hingga `max_retries` dengan
exponential backoff. Tangkap exception yang paling spesifik: `HTTPStatusError`
untuk status HTTP, `TransportError` untuk koneksi, `ResponseParseError` untuk
format respons, dan `BraveAPIError` sebagai fallback.

`ChallengeRequiredError` berarti upstream meminta browser challenge;
`ConversationError` dan `StreamAbortedError` berarti percakapan atau streaming
terganggu. Jangan mencatat cookie, password proxy, atau payload mentah lengkap
ke log production.

## Gejala umum

| Gejala | Pemeriksaan |
|---|---|
| `ModuleNotFoundError` | Install pada environment yang sama dengan `uv run`. |
| Timeout | Naikkan `timeout`/`stream_timeout` dan periksa proxy. |
| HTTP 403/challenge | Periksa availability upstream; retry saja mungkin tidak cukup. |
| Hasil kosong | Gunakan field vertical yang benar dan periksa `has_results`. |
| Bahasa salah | Atur `language` dan `ui_lang`. |
| MCP error | Jalankan `--log-level info` dan periksa environment variable. |

Test lokal memakai fake transport dan fixture. Test lulus tidak menjamin
perubahan response, rate limit, atau challenge policy layanan live.
