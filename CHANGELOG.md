# Changelog

## 0.1.0 (2026-11-21)

- First release: typed client for the Tube2Vid API (`/v1`), covering job submission, polling (`wait_for_job`), signed download links and streaming downloads, usage, API keys, billing checkout and the public platform and status endpoints.
- `Tube2VidApiError` with `status`, `message`, `code`, `body` and `data`.
- No runtime dependencies (standard library `urllib`).
