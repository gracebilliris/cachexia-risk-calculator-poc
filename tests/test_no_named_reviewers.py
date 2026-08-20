from __future__ import annotations

import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLOCKED_NAMES = ("Mari" + "ana", "Nami" + "tha")
TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".txt",
    ".yml",
    ".yaml",
}
WORKBOOK_SUFFIXES = {".xlsx", ".xlsm"}


class NamedReviewerPrivacyTests(unittest.TestCase):
    def test_repository_text_and_workbooks_do_not_name_reviewers(self):
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            if path.suffix.lower() in TEXT_SUFFIXES:
                self._assert_anonymous(path, path.read_bytes())
            elif path.suffix.lower() in WORKBOOK_SUFFIXES:
                with zipfile.ZipFile(path) as archive:
                    for member in archive.namelist():
                        self._assert_anonymous(
                            path,
                            archive.read(member),
                            member,
                        )

    def _assert_anonymous(
        self,
        path: Path,
        content: bytes,
        member: str | None = None,
    ) -> None:
        folded = content.lower()
        location = f"{path.relative_to(ROOT)}"
        if member:
            location += f":{member}"
        for name in BLOCKED_NAMES:
            self.assertNotIn(
                name.lower().encode("utf-8"),
                folded,
                f"Named reviewer found in {location}",
            )


class PublishedSiteTests(unittest.TestCase):
    def test_site_does_not_publish_workbook_downloads(self):
        page = (ROOT / "prototype" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn(".xlsx", page.casefold())
        self.assertNotIn(".xlsm", page.casefold())
        self.assertNotIn("downloads/", page.casefold())

        workflow = (
            ROOT / ".github" / "workflows" / "pages.yml"
        ).read_text(encoding="utf-8")
        self.assertNotIn("_site/downloads", workflow)
        self.assertNotIn("cp excel/", workflow)


if __name__ == "__main__":
    unittest.main()
