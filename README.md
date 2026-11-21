# Tube2Vid Python SDK

**The official Python client for the Tube2Vid video downloader API: download YouTube, TikTok, Instagram, X, Reddit and 1,800+ other sites as MP4 or MP3 from Python.**

[![CI](https://github.com/Tube2Vid/sdk-python/actions/workflows/ci.yml/badge.svg)](https://github.com/Tube2Vid/sdk-python/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/tube2vid.svg)](https://pypi.org/project/tube2vid/)
[![Python versions](https://img.shields.io/pypi/pyversions/tube2vid.svg)](https://pypi.org/project/tube2vid/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[Tube2Vid](https://tube2vid.com) turns a media URL into a downloadable file. This package wraps its REST API with typed responses, a polling helper and safe signed-URL downloads. It has no dependencies beyond the Python standard library.

## Install

```bash
pip install tube2vid
```

Requires Python 3.11 or newer. [Get an API key](https://tube2vid.com/pricing) and export it:

```bash
export TUBE2VID_API_KEY=tv_live_...
```

## Quickstart

```python
from tube2vid import Tube2VidClient

client = Tube2VidClient()  # reads TUBE2VID_API_KEY

job = client.submit_job({"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "format": "mp4"})
done = client.wait_for_job(job["jobId"], on_update=lambda j: print(j["status"], j["progress"]))

if done["status"] == "completed":
    print(client.get_download_link(job["jobId"]))  # short-lived signed URL, no auth needed
else:
    print("failed:", done.get("errorCode"), done.get("errorMessage"))
```

For audio only, pass `{"url": ..., "mode": "audio", "format": "mp3"}`. To save the file directly:

```python
import shutil

with client.download_job(job_id) as response, open("video.mp4", "wb") as out:
    shutil.copyfileobj(response, out)
```

## Methods

| Method | Endpoint |
| --- | --- |
| `submit_job(input)` | `POST /v1/jobs` (or `/v1/public/jobs` without a key) |
| `get_job_status(job_id)` / `get_job_events(job_id)` | `GET /v1/jobs/{id}`, `/events` |
| `wait_for_job(job_id, interval=2.0, timeout=900, on_update=None)` | polls until `completed` or `failed` |
| `get_download_link(job_id)` / `download_job(job_id)` | `GET /v1/jobs/{id}/download` |
| `get_usage()` | `GET /v1/usage` |
| `list_api_keys()` / `create_api_key(input)` | `/v1/api-keys` |
| `create_checkout(input)` | `POST /v1/billing/checkout` |
| `list_platforms()` / `get_platform_health()` / `get_status_history(limit, platform)` | public, no key |
| `get_health()` / `get_operational_metrics()` | public, no key |

Responses are plain dicts typed with `TypedDict` (see `tube2vid.types`), so keys match the [API docs](https://tube2vid.com/docs) exactly.

## Error handling

Every non-2xx response raises `Tube2VidApiError` with the HTTP `status`, the API's `message`, an optional machine-readable `code`, and the raw `body` and parsed `data`.

```python
from tube2vid import Tube2VidApiError

try:
    client.submit_job({"url": "https://www.tiktok.com/@user/video/123"})
except Tube2VidApiError as error:
    if error.status == 402:
        print("Out of credits:", error.data.get("creditBalance"))
    else:
        print(error.status, error.code, error.message)
```

| Status | Meaning |
| --- | --- |
| 400 | Invalid body or `unsupported_platform` |
| 401 | Missing or invalid API key |
| 402 | Not enough credits |
| 403 | The key lacks the scope, or the job is not yours |
| 404 | Unknown job |
| 409 | The job has not completed yet |
| 410 | The file has expired |
| 502 | The job could not be queued; retry |

`wait_for_job` raises the built-in `TimeoutError` if the job is still running after `timeout` seconds. A failed job is returned, not raised: check `status`, `errorCode` and `errorMessage`. Its reserved credits are refunded.

## Configuration

```python
client = Tube2VidClient(
    api_key="tv_live_...",              # default: TUBE2VID_API_KEY
    base_url="https://tube2vid.com",    # override for staging or a proxy
    headers={"x-request-source": "my-app"},
    timeout=60.0,                        # per-request socket timeout, seconds
)
```

## Links

- [Tube2Vid online video downloader](https://tube2vid.com)
- [Tube2Vid API documentation](https://tube2vid.com/docs)
- [Pricing and API keys](https://tube2vid.com/pricing)
- [Live platform status](https://tube2vid.com/status)

Other languages: [TypeScript](https://github.com/Tube2Vid/sdk), [Python](https://github.com/Tube2Vid/sdk-python), [Go](https://github.com/Tube2Vid/sdk-go), [Java](https://github.com/Tube2Vid/sdk-java), [C#](https://github.com/Tube2Vid/sdk-dotnet), [PHP](https://github.com/Tube2Vid/sdk-php), [Ruby](https://github.com/Tube2Vid/sdk-ruby), [Rust](https://github.com/Tube2Vid/sdk-rust), [Swift](https://github.com/Tube2Vid/sdk-swift).

## License

[MIT](LICENSE) © 2026 Tube2Vid
