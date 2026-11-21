# Changelog

## 0.2.0 (2026-11-21)

- The anonymous browser flow now uses an Atlas captcha: `submit_public_job` takes `captchaToken` instead of `pow` and `turnstileToken`, and a failed check comes back with code `captcha_failed`.
- Removed `get_pow_challenge`, `PowChallenge` and `ProofOfWork`: the API no longer serves `GET /v1/challenges/pow`. Calls with an API key are unchanged.

## 0.1.0 (2026-11-21)

- First release: typed client for the Tube2Vid API (`/v1`), covering job submission, polling (`wait_for_job`), signed download links and streaming downloads, usage, API keys, billing checkout and the public platform and status endpoints.
- `Tube2VidApiError` with `status`, `message`, `code`, `body` and `data`.
- No runtime dependencies (standard library `urllib`).
