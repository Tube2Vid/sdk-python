import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from tube2vid import Tube2VidApiError, Tube2VidClient


class FakeApi:
    """A local HTTP server that replays queued (status, headers, body) responses and records requests."""

    def __init__(self):
        self.responses = []
        self.requests = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def handle_one(self):
                length = int(self.headers.get("content-length") or 0)
                fake.requests.append((self.command, self.path, dict(self.headers), self.rfile.read(length)))
                status, headers, body = fake.responses.pop(0)
                payload = body if isinstance(body, bytes) else json.dumps(body).encode()
                self.send_response(status)
                for name, value in headers.items():
                    self.send_header(name, value)
                self.send_header("content-length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            do_GET = do_POST = handle_one

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class ClientTest(unittest.TestCase):
    def setUp(self):
        self.api = FakeApi()
        self.addCleanup(self.api.close)

    def test_sends_api_key_and_parses_errors(self):
        self.api.responses.append((402, {}, {"error": "Insufficient credits", "code": "no_credits"}))
        client = Tube2VidClient(api_key="tv_live_x", base_url=self.api.url + "/")
        with self.assertRaises(Tube2VidApiError) as caught:
            client.submit_job({"url": "https://youtu.be/x"})
        self.assertEqual(caught.exception.status, 402)
        self.assertEqual(caught.exception.message, "Insufficient credits")
        self.assertEqual(caught.exception.code, "no_credits")
        method, path, headers, body = self.api.requests[0]
        self.assertEqual((method, path), ("POST", "/v1/jobs"))
        self.assertEqual(headers["Authorization"], "Bearer tv_live_x")
        self.assertEqual(json.loads(body), {"url": "https://youtu.be/x"})

    def test_reads_key_from_env(self):
        with mock.patch.dict(os.environ, {"TUBE2VID_API_KEY": "tv_live_env"}):
            self.assertEqual(Tube2VidClient().api_key, "tv_live_env")

    def test_without_key_submit_uses_public_route(self):
        self.api.responses.append((200, {}, {"jobId": "j", "status": "queued", "platform": "youtube", "estimatedCredits": 0}))
        with mock.patch.dict(os.environ, {}, clear=True):
            job = Tube2VidClient(base_url=self.api.url).submit_job({"url": "https://youtu.be/x"})
        self.assertEqual(job["jobId"], "j")
        _, path, headers, _ = self.api.requests[0]
        self.assertEqual(path, "/v1/public/jobs")
        self.assertNotIn("Authorization", headers)

    def test_download_follows_signed_redirect_without_key(self):
        client = Tube2VidClient(api_key="tv_live_x", base_url=self.api.url)
        self.api.responses.append((302, {"location": "/signed/file.mp4?sig=1"}, b""))
        self.api.responses.append((200, {}, b"bytes"))
        with client.download_job("job 1") as file:
            self.assertEqual(file.read(), b"bytes")
        self.assertEqual(self.api.requests[0][1], "/v1/jobs/job%201/download")
        self.assertEqual(self.api.requests[1][1], "/signed/file.mp4?sig=1")
        self.assertNotIn("Authorization", self.api.requests[1][2])

        self.api.responses.append((302, {"location": "https://cdn.test/f.mp4"}, b""))
        self.assertEqual(client.get_download_link("j"), "https://cdn.test/f.mp4")

    def test_download_link_raises_when_not_ready(self):
        self.api.responses.append((409, {}, {"error": "Job is not completed"}))
        with self.assertRaises(Tube2VidApiError) as caught:
            Tube2VidClient(api_key="k", base_url=self.api.url).get_download_link("j")
        self.assertEqual(caught.exception.status, 409)

    def test_wait_for_job_polls_until_terminal(self):
        for status in ("queued", "running", "completed"):
            self.api.responses.append((200, {}, {"id": "j", "status": status, "progress": 0}))
        seen = []
        final = Tube2VidClient(api_key="k", base_url=self.api.url).wait_for_job("j", interval=0.001, on_update=lambda j: seen.append(j["status"]))
        self.assertEqual(final["status"], "completed")
        self.assertEqual(seen, ["queued", "running", "completed"])

    def test_status_history_query(self):
        self.api.responses.append((200, {}, []))
        Tube2VidClient(base_url=self.api.url).get_status_history(20, "youtube")
        self.assertEqual(self.api.requests[0][1], "/v1/status/history?limit=20&platform=youtube")


if __name__ == "__main__":
    unittest.main()
