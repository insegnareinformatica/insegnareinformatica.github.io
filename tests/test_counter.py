from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen


@unittest.skipUnless(shutil.which("php"), "PHP CLI is not installed; these tests also run in CI")
class CounterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        source = Path(__file__).resolve().parents[1] / "server/home-counter/counter.php"
        shutil.copyfile(source, cls.root / "counter.php")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        cls.server = subprocess.Popen(
            ["php", "-S", "127.0.0.1:" + str(port), "-t", str(cls.root)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.url = "http://127.0.0.1:" + str(port) + "/counter.php"
        for _ in range(50):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    break
            except OSError:
                time.sleep(0.05)
        else:
            cls.server.terminate()
            cls.server.wait()
            cls.temp.cleanup()
            raise RuntimeError("PHP server did not start")

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        cls.server.wait(timeout=5)
        cls.temp.cleanup()

    def setUp(self):
        (self.root / "counter.txt").unlink(missing_ok=True)

    def request(self, origin="https://informaticainclasse.it", method="GET"):
        request = Request(self.url, method=method,
                          headers={"Origin": origin} if origin else {})
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            body = response.read()
            return response.status, response.headers, json.loads(body) if body else None

    def test_counts_each_request_and_writes_only_an_integer(self):
        for expected in range(1, 4):
            status, headers, data = self.request()
            self.assertEqual(status, 200)
            self.assertEqual(data, {"value": expected})
            self.assertIsNone(headers.get("Set-Cookie"))
            self.assertEqual(headers["Access-Control-Allow-Origin"], "https://informaticainclasse.it")
        self.assertEqual((self.root / "counter.txt").read_text(), "3")

    def test_concurrent_requests_are_not_lost(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            responses = list(pool.map(lambda _: self.request(), range(40)))
        self.assertTrue(all(response[0] == 200 for response in responses))
        self.assertEqual((self.root / "counter.txt").read_text(), "40")

    def test_rejected_methods_and_origins_do_not_increment(self):
        for origin in ("", "https://untrusted.test", "null", "http://informaticainclasse.it"):
            self.assertEqual(self.request(origin=origin)[0], 403)
        self.assertEqual(self.request(method="OPTIONS")[0], 204)
        self.assertEqual(self.request(method="HEAD")[0], 405)
        self.assertEqual(self.request(method="POST")[0], 405)
        self.assertFalse((self.root / "counter.txt").exists())

    def test_corrupt_counter_is_not_silently_reset(self):
        path = self.root / "counter.txt"
        path.write_text("broken")
        self.assertEqual(self.request()[0], 500)
        self.assertEqual(path.read_text(), "broken")


if __name__ == "__main__":
    unittest.main()
