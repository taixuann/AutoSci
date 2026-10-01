"""Unit tests for the pure helpers in tools/zotero_fetch.py (no network, no API key)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import zotero_fetch  # noqa: E402


class ParseItemRefTest(unittest.TestCase):
    def test_bare_key(self):
        self.assertEqual(zotero_fetch.parse_item_ref("ABCD1234"), "ABCD1234")

    def test_bare_key_lowercased_is_normalized(self):
        self.assertEqual(zotero_fetch.parse_item_ref("abcd1234"), "ABCD1234")

    def test_zotero_prefix(self):
        self.assertEqual(zotero_fetch.parse_item_ref("zotero:ABCD1234"), "ABCD1234")

    def test_user_item_url(self):
        self.assertEqual(
            zotero_fetch.parse_item_ref(
                "https://zotero.org/users/1234567/items/ABCD1234"
            ),
            "ABCD1234",
        )

    def test_group_item_url_with_trailing_slash(self):
        self.assertEqual(
            zotero_fetch.parse_item_ref(
                "http://zotero.org/groups/12345/items/EFGH5678/"
            ),
            "EFGH5678",
        )

    def test_www_item_url_with_query_string(self):
        self.assertEqual(
            zotero_fetch.parse_item_ref(
                "https://www.zotero.org/users/1/items/ABCD1234?queue=1"
            ),
            "ABCD1234",
        )

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            zotero_fetch.parse_item_ref("")

    def test_rejects_wrong_length(self):
        with self.assertRaises(ValueError):
            zotero_fetch.parse_item_ref("ABCD123")
        with self.assertRaises(ValueError):
            zotero_fetch.parse_item_ref("ABCD12345")

    def test_rejects_arbitrary_text(self):
        with self.assertRaises(ValueError):
            zotero_fetch.parse_item_ref("not a zotero ref")

    def test_rejects_foreign_domain(self):
        with self.assertRaises(ValueError):
            zotero_fetch.parse_item_ref(
                "https://example.com/users/1/items/ABCD1234"
            )

    def test_rejects_url_without_items_segment(self):
        with self.assertRaises(ValueError):
            zotero_fetch.parse_item_ref("https://zotero.org/users/1/items/")


class NormalizeItemTest(unittest.TestCase):
    def test_rich_article(self):
        raw = {
            "key": "ABCD1234",
            "version": 7,
            "data": {
                "itemType": "journalArticle",
                "title": "A Study of Things",
                "creators": [
                    {"lastName": "Doe", "firstName": "Jane",
                     "creatorType": "author"},
                    {"lastName": "Smith", "firstName": "John",
                     "creatorType": "author"},
                ],
                "date": "2023-05-01",
                "DOI": "10.1234/abc",
                "publicationTitle": "Journal of Studies",
                "abstractNote": "An abstract.",
                "tags": [{"tag": "nlp"}, {"tag": "llm"}],
                "collections": ["COLL1234"],
            },
        }
        rec = zotero_fetch.normalize_item(raw)
        self.assertEqual(rec["item_key"], "ABCD1234")
        self.assertEqual(rec["item_type"], "journalArticle")
        self.assertEqual(rec["title"], "A Study of Things")
        self.assertEqual(rec["creators"], ["Doe, Jane", "Smith, John"])
        self.assertEqual(rec["year"], "2023")
        self.assertEqual(rec["doi"], "10.1234/abc")
        self.assertEqual(rec["publication_title"], "Journal of Studies")
        self.assertEqual(rec["tags"], ["nlp", "llm"])
        self.assertEqual(rec["collections"], ["COLL1234"])

    def test_institutional_creator_and_bare_data_dict(self):
        raw = {
            "itemType": "report",
            "title": "Report",
            "creators": [{"name": "Some Lab", "creatorType": "author"}],
            "date": "2021",
        }
        rec = zotero_fetch.normalize_item(raw)
        self.assertEqual(rec["creators"], ["Some Lab"])
        self.assertEqual(rec["year"], "2021")

    def test_minimal_item_yields_empty_fields(self):
        rec = zotero_fetch.normalize_item({"data": {"itemType": "note"}})
        self.assertEqual(rec["title"], "")
        self.assertEqual(rec["creators"], [])
        self.assertIsNone(rec["year"])
        self.assertIsNone(rec["doi"])
        self.assertIsNone(rec["publication_title"])
        self.assertEqual(rec["tags"], [])
        self.assertEqual(rec["collections"], [])


class SelectPdfAttachmentTest(unittest.TestCase):
    @staticmethod
    def _child(content_type="application/pdf", filename="paper.pdf",
                link_mode="imported_file"):
        return {"data": {"itemType": "attachment",
                         "contentType": content_type,
                         "filename": filename,
                         "linkMode": link_mode}}

    def test_selects_pdf_child(self):
        html = self._child(content_type="text/html", filename="snap.html")
        pdf = self._child()
        self.assertIs(zotero_fetch.select_pdf_attachment([html, pdf]), pdf)

    def test_prefers_imported_file_over_linked(self):
        linked = self._child(link_mode="linked_file")
        imported = self._child(link_mode="imported_file")
        self.assertIs(
            zotero_fetch.select_pdf_attachment([linked, imported]), imported
        )

    def test_filename_fallback_when_content_type_missing(self):
        child = {"data": {"itemType": "attachment", "filename": "paper.pdf"}}
        self.assertIs(zotero_fetch.select_pdf_attachment([child]), child)

    def test_returns_none_without_pdf(self):
        self.assertIsNone(
            zotero_fetch.select_pdf_attachment(
                [self._child(content_type="text/html", filename="snap.html")]
            )
        )

    def test_returns_none_for_empty_list(self):
        self.assertIsNone(zotero_fetch.select_pdf_attachment([]))


class RequireCredentialsTest(unittest.TestCase):
    def test_returns_credentials_with_default_type(self):
        creds = zotero_fetch.require_credentials(
            {"ZOTERO_LIBRARY_ID": "1234567", "ZOTERO_API_KEY": "k" * 24}
        )
        self.assertEqual(creds, ("1234567", "k" * 24, "user"))

    def test_group_type_passthrough(self):
        creds = zotero_fetch.require_credentials(
            {"ZOTERO_LIBRARY_ID": "9", "ZOTERO_API_KEY": "k",
             "ZOTERO_LIBRARY_TYPE": "group"}
        )
        self.assertEqual(creds, ("9", "k", "group"))

    def test_missing_api_key_exits_nonzero(self):
        with self.assertRaises(SystemExit) as ctx:
            zotero_fetch.require_credentials({"ZOTERO_LIBRARY_ID": "1"})
        self.assertNotEqual(ctx.exception.code, 0)

    def test_missing_library_id_exits_nonzero(self):
        with self.assertRaises(SystemExit) as ctx:
            zotero_fetch.require_credentials({"ZOTERO_API_KEY": "k"})
        self.assertNotEqual(ctx.exception.code, 0)


class SafeFilenameTest(unittest.TestCase):
    def test_strips_path_separators(self):
        name = zotero_fetch.safe_filename("../../evil/name")
        self.assertNotIn("/", name)
        self.assertNotIn("..", name)

    def test_enforces_pdf_suffix(self):
        self.assertTrue(zotero_fetch.safe_filename("report").endswith(".pdf"))
        self.assertTrue(zotero_fetch.safe_filename("report.pdf").endswith(".pdf"))
        self.assertEqual(zotero_fetch.safe_filename("report.PDF"), "report.PDF")

    def test_fallback_for_empty_input(self):
        self.assertEqual(zotero_fetch.safe_filename(""), "item.pdf")


class ReadCappedTest(unittest.TestCase):
    def test_concatenates_under_limit(self):
        chunks = [b"%PD", b"F-1.7", b" rest"]
        self.assertEqual(zotero_fetch.read_capped(chunks, limit=100),
                         b"%PDF-1.7 rest")

    def test_empty_input(self):
        self.assertEqual(zotero_fetch.read_capped([], limit=10), b"")

    def test_over_limit_raises(self):
        with self.assertRaises(zotero_fetch.DownloadError):
            zotero_fetch.read_capped([b"x" * 6, b"y" * 6], limit=10)


class LooksLikePdfTest(unittest.TestCase):
    def test_pdf_magic(self):
        self.assertTrue(zotero_fetch.looks_like_pdf(b"%PDF-1.7\n..."))
        self.assertTrue(zotero_fetch.looks_like_pdf(b"%PDF"))

    def test_html_and_empty_rejected(self):
        self.assertFalse(zotero_fetch.looks_like_pdf(b"<!doctype html>"))
        self.assertFalse(zotero_fetch.looks_like_pdf(b""))


class AttachmentUrlTest(unittest.TestCase):
    def test_http_and_https_accepted(self):
        self.assertEqual(
            zotero_fetch.attachment_url({"data": {"url": "https://a.example/x.pdf"}}),
            "https://a.example/x.pdf",
        )
        self.assertEqual(
            zotero_fetch.attachment_url({"data": {"url": "http://a.example/x.pdf"}}),
            "http://a.example/x.pdf",
        )

    def test_non_http_scheme_rejected(self):
        self.assertIsNone(
            zotero_fetch.attachment_url({"data": {"url": "file:///etc/passwd"}})
        )
        self.assertIsNone(
            zotero_fetch.attachment_url({"data": {"url": "javascript:alert(1)"}})
        )

    def test_missing_or_bare_data(self):
        self.assertIsNone(zotero_fetch.attachment_url({"data": {}}))
        self.assertIsNone(zotero_fetch.attachment_url({}))


if __name__ == "__main__":
    unittest.main()
