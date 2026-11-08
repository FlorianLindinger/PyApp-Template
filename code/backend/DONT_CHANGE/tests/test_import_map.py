"""Import-map downloads accept expected HTTPS sources and reject unsafe redirects."""

import sys
import unittest
import urllib.request
from http.client import HTTPMessage
from io import BytesIO
from unittest import mock

from project_location import DONT_CHANGE

with mock.patch.object(sys, "path", [str(DONT_CHANGE / "scripts" / "tools"), *sys.path]):
    import make_import_map


class ImportMapDownloadTests(unittest.TestCase):
    def test_expected_sources_are_accepted(self):
        for url in (
            *make_import_map.RANKING_URLS,
            "https://pypi.org/pypi/example/json",
            "https://files.pythonhosted.org/packages/example.whl",
        ):
            with self.subTest(url=url):
                make_import_map._validate_download_url(url)

    def test_unapproved_urls_are_rejected_before_network_access(self):
        urls = (
            "file:///C:/private.txt",
            "http://pypi.org/pypi/example/json",
            "ftp://pypi.org/example",
            "https://localhost/example",
            "https://pypi.org.evil.example/example",
            "https://user:password@pypi.org/example",
            "https://pypi.org:8443/example",
        )
        with mock.patch.object(make_import_map.urllib.request, "build_opener") as build:
            for url in urls:
                with self.subTest(url=url), self.assertRaises(ValueError):
                    make_import_map.fetch(url)
            build.assert_not_called()

    def test_redirects_cannot_escape_the_download_policy(self):
        handler = make_import_map._DownloadRedirectHandler()
        request = urllib.request.Request("https://pypi.org/example")
        for url in ("file:///C:/private.txt", "http://pypi.org/example", "https://example.com/example"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                handler.redirect_request(request, BytesIO(), 302, "Found", HTTPMessage(), url)
        redirected = handler.redirect_request(
            request, BytesIO(), 302, "Found", HTTPMessage(), "https://files.pythonhosted.org/example.whl"
        )
        if redirected is None:
            self.fail("The permitted GET redirect did not produce a request.")
        self.assertEqual(redirected.full_url, "https://files.pythonhosted.org/example.whl")

    def test_fetch_preserves_range_headers_and_returns_bytes(self):
        opener = mock.MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = b"wheel data"
        with mock.patch.object(make_import_map.urllib.request, "build_opener", return_value=opener):
            data = make_import_map.fetch("https://files.pythonhosted.org/example.whl", {"Range": "bytes=0-9"}, 5)
        self.assertEqual(data, b"wheel data")
        request = opener.open.call_args[0][0]
        self.assertEqual(request.get_header("Range"), "bytes=0-9")
        self.assertEqual(opener.open.call_args[1]["timeout"], 5)


if __name__ == "__main__":
    unittest.main()
