from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from http.client import HTTPResponse
from typing import Any, Callable, Optional, cast

from . import types as t

__version__ = "0.1.0"
DEFAULT_BASE_URL = "https://tube2vid.com"


class Tube2VidApiError(Exception):
    """Raised for any non-2xx API response."""

    def __init__(self, status: int, body: str = "") -> None:
        data: Any = None
        try:
            data = json.loads(body) if body else None
        except ValueError:
            pass
        fields = data if isinstance(data, dict) else {}
        message = fields.get("error")
        super().__init__(message if isinstance(message, str) else body or f"Tube2Vid API request failed with {status}")
        self.status = status
        #: Raw response body, if any.
        self.body: Optional[str] = body or None
        #: Machine-readable error code when the API sent one (e.g. "turnstile_failed").
        self.code: Optional[str] = fields.get("code") if isinstance(fields.get("code"), str) else None
        #: Parsed JSON body, if the body was JSON.
        self.data: Any = data

    @property
    def message(self) -> str:
        return str(self.args[0])


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    # The download endpoint redirects to a signed URL; we read it ourselves so the API key never reaches the storage host.
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


class Tube2VidClient:
    """Client for the Tube2Vid media download API.

    The API key comes from ``api_key`` or the ``TUBE2VID_API_KEY`` environment variable.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        headers: Optional[dict[str, str]] = None,
        timeout: float = 60.0,
    ) -> None:
        key = api_key if api_key is not None else os.environ.get("TUBE2VID_API_KEY")
        self.api_key: Optional[str] = (key or "").strip() or None
        self.base_url = base_url.rstrip("/")
        self.headers = dict(headers or {})
        self.timeout = timeout
        self._opener = urllib.request.build_opener(_NoRedirect)

    # Public, no API key needed.

    def get_health(self) -> t.ServiceHealth:
        return self._get("/healthz")

    def list_platforms(self) -> list[t.PlatformSummary]:
        return self._get("/v1/platforms")

    def get_platform_health(self) -> list[t.PlatformHealthRow]:
        return self._get("/v1/platforms/health")

    def get_recent_downloads(self, limit: int = 18) -> list[t.RecentDownload]:
        return self._get(f"/v1/public/recent-downloads?{urllib.parse.urlencode({'limit': limit})}")

    def get_status_history(self, limit: int = 50, platform: Optional[str] = None) -> list[t.StatusHistoryItem]:
        query: dict[str, Any] = {"limit": limit}
        if platform:
            query["platform"] = platform
        return self._get(f"/v1/status/history?{urllib.parse.urlencode(query)}")

    def get_operational_metrics(self) -> t.OperationalMetrics:
        return self._get("/v1/ops/metrics")

    def get_pow_challenge(self) -> t.PowChallenge:
        return self._get("/v1/challenges/pow")

    def submit_public_job(self, input: t.JobSubmitInput) -> t.QueuedJobResponse:
        """Anonymous submission, as the website does it. Requires ``pow`` (and ``turnstileToken`` where the human check is on)."""
        return self._post("/v1/public/jobs", input)

    def get_public_job_status(self, job_id: str) -> t.PublicJobStatus:
        return self._get(f"/v1/public/jobs/{_q(job_id)}")

    def get_public_download_url(self, job_id: str) -> str:
        """Direct link to an anonymous job's file; it redirects to a short-lived signed URL."""
        return f"{self.base_url}/v1/public/jobs/{_q(job_id)}/download"

    def get_public_thumbnail_url(self, job_id: str) -> str:
        return f"{self.base_url}/v1/public/jobs/{_q(job_id)}/thumbnail"

    # Authenticated, needs an API key.

    def submit_authenticated_job(self, input: t.JobSubmitInput) -> t.QueuedJobResponse:
        return self._post("/v1/jobs", input)

    def submit_job(self, input: t.JobSubmitInput) -> t.QueuedJobResponse:
        """Uses /v1/jobs with an API key, /v1/public/jobs without one."""
        return self.submit_authenticated_job(input) if self.api_key else self.submit_public_job(input)

    def get_job_status(self, job_id: str) -> t.JobStatus:
        return self._get(f"/v1/jobs/{_q(job_id)}")

    def get_job_events(self, job_id: str) -> list[t.JobEvent]:
        return self._get(f"/v1/jobs/{_q(job_id)}/events")

    def wait_for_job(
        self,
        job_id: str,
        interval: float = 2.0,
        timeout: float = 15 * 60,
        on_update: Optional[Callable[[t.JobStatus], None]] = None,
    ) -> t.JobStatus:
        """Polls get_job_status until the job is completed or failed and returns the final job either way.

        Raises TimeoutError after ``timeout`` seconds.
        """
        deadline = time.monotonic() + timeout
        while True:
            job = self.get_job_status(job_id)
            if on_update:
                on_update(job)
            if job["status"] in ("completed", "failed"):
                return job
            if time.monotonic() + interval > deadline:
                raise TimeoutError(f"Timed out waiting for job {job_id}")
            time.sleep(interval)

    def get_download_url(self, job_id: str) -> str:
        """The authenticated download endpoint. It needs the bearer header, so prefer get_download_link or download_job."""
        return f"{self.base_url}/v1/jobs/{_q(job_id)}/download"

    def get_download_link(self, job_id: str) -> str:
        """Resolves a completed job to its short-lived signed file URL, which needs no auth."""
        response = self._send(self.get_download_url(job_id))
        location = self._redirect_location(response)
        response.close()
        if location:
            return location
        raise Tube2VidApiError(response.status, "This API serves the file directly; use download_job instead.")

    def download_job(self, job_id: str) -> HTTPResponse:
        """Opens a completed job's file as a streaming response. Read it with ``.read()`` and close it when done."""
        response = self._send(self.get_download_url(job_id))
        location = self._redirect_location(response)
        if not location:
            return response
        response.close()
        # The signed URL carries its own auth; the API key must not be sent to the storage host.
        try:
            return cast(HTTPResponse, urllib.request.urlopen(location, timeout=self.timeout))
        except urllib.error.HTTPError as error:
            raise _api_error(error) from None

    def get_usage(self) -> t.UsageSummary:
        return self._get("/v1/usage")

    def list_api_keys(self) -> list[t.ApiKeySummary]:
        """Needs the keys:read scope."""
        return self._get("/v1/api-keys")

    def create_api_key(self, input: t.ApiKeyCreateInput) -> t.CreatedApiKey:
        """Needs the keys:write scope. The returned ``key`` is shown only once."""
        return self._post("/v1/api-keys", input)

    def create_checkout(self, input: t.CheckoutInput) -> t.CheckoutSession:
        """Needs the billing:write scope. Open ``checkoutUrl`` to pay."""
        return self._post("/v1/billing/checkout", input)

    def _get(self, path: str) -> Any:
        return _read_json(self._send(f"{self.base_url}{path}"))

    def _post(self, path: str, body: Any) -> Any:
        data = json.dumps(body).encode()
        return _read_json(self._send(f"{self.base_url}{path}", data, {"content-type": "application/json"}))

    def _send(self, url: str, data: Optional[bytes] = None, extra: Optional[dict[str, str]] = None) -> HTTPResponse:
        headers = {"user-agent": f"tube2vid-python/{__version__}", "accept": "application/json"}
        if self.api_key:
            headers["authorization"] = f"Bearer {self.api_key}"
        headers.update(self.headers)
        headers.update(extra or {})
        request = urllib.request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
        try:
            return cast(HTTPResponse, self._opener.open(request, timeout=self.timeout))
        except urllib.error.HTTPError as error:
            if 300 <= error.code < 400 and error.headers.get("location"):
                return cast(HTTPResponse, error)
            raise _api_error(error) from None

    def _redirect_location(self, response: HTTPResponse) -> Optional[str]:
        location = response.headers.get("location")
        if 300 <= response.status < 400 and location:
            return urllib.parse.urljoin(self.base_url + "/", location)
        return None


def _q(value: str) -> str:
    return urllib.parse.quote(value, safe="")


def _read_json(response: HTTPResponse) -> Any:
    with response:
        return json.loads(response.read())


def _api_error(error: urllib.error.HTTPError) -> Tube2VidApiError:
    try:
        body = error.read().decode("utf-8", "replace")
    except Exception:
        body = ""
    finally:
        error.close()
    return Tube2VidApiError(error.code, body)
