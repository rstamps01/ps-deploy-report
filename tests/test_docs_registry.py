"""Guards for the in-app documentation surfaced by the Docs tab.

The Docs tab renders raw markdown off disk, so anything an author types stays
frozen while the app moves on. That is how a 1.6.0 build ended up telling users
to download ``VAST-Reporter-v1.5.0-mac.dmg``. Authors now write substitution
tokens and these tests keep literals from creeping back in, alongside checks
that every registered document actually exists and ships in the packaged app.
"""

import re
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from app import _DOC_REGISTRY, doc_substitutions, _apply_doc_substitutions  # noqa: E402

# Release history is a record of what shipped, so literal versions are its
# content rather than drift. Everything else must use tokens.
_VERSION_LITERAL_EXEMPT = {"CHANGELOG.md"}

# The README's version badge is kept in step by scripts/check-version-sync.sh,
# which is a stronger guarantee than a token would give.
_FOOTER_EXEMPT = _VERSION_LITERAL_EXEMPT | {"README.md"}

_ARTIFACT_LITERAL = re.compile(r"VAST-Reporter-v\d")
_VERSION_FOOTER = re.compile(r"\*\*Version\*\*:\s*\d")


def _registry_paths():
    return [doc["path"] for doc in _DOC_REGISTRY]


class TestDocRegistryIntegrity(unittest.TestCase):
    def test_every_registered_document_exists(self):
        for rel_path in _registry_paths():
            with self.subTest(doc=rel_path):
                self.assertTrue((PROJECT_ROOT / rel_path).is_file(), f"{rel_path} is registered but missing")

    def test_registry_ids_are_unique(self):
        ids = [doc["id"] for doc in _DOC_REGISTRY]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_registered_document_is_bundled_by_pyinstaller(self):
        """A doc missing from the spec renders as "not found" in the packaged app.

        The spec lists some documents individually and pulls others in by their
        containing directory, so a path counts as bundled if it or any ancestor
        appears in ``datas``.
        """
        spec = (PROJECT_ROOT / "packaging" / "vast-reporter.spec").read_text(encoding="utf-8")

        def _referenced(path: Path) -> bool:
            needle = " / ".join(f'"{part}"' for part in path.parts)
            return needle in spec

        for rel_path in _registry_paths():
            with self.subTest(doc=rel_path):
                path = Path(rel_path)
                candidates = [path, *path.parents]
                bundled = any(_referenced(c) for c in candidates if str(c) != ".")
                # Repo-root files appear in datas as ROOT / "NAME.md".
                self.assertTrue(bundled, f"{rel_path} is registered but neither it nor its directory is in datas")


class TestDocVersionTokens(unittest.TestCase):
    def test_no_literal_artifact_filenames(self):
        for rel_path in _registry_paths():
            if Path(rel_path).name in _VERSION_LITERAL_EXEMPT:
                continue
            text = (PROJECT_ROOT / rel_path).read_text(encoding="utf-8")
            with self.subTest(doc=rel_path):
                found = _ARTIFACT_LITERAL.findall(text)
                self.assertEqual(
                    found,
                    [],
                    f"{rel_path} hardcodes a release artifact name; "
                    f"use {{{{MAC_ARM64_DMG}}}}, {{{{MAC_X64_DMG}}}} or {{{{WIN_ZIP}}}}",
                )

    def test_no_literal_version_footers(self):
        for rel_path in _registry_paths():
            if Path(rel_path).name in _FOOTER_EXEMPT:
                continue
            text = (PROJECT_ROOT / rel_path).read_text(encoding="utf-8")
            with self.subTest(doc=rel_path):
                self.assertIsNone(
                    _VERSION_FOOTER.search(text),
                    f"{rel_path} has a hardcoded version footer; use **Version**: {{{{APP_VERSION}}}}",
                )


class TestDocSubstitution(unittest.TestCase):
    def test_tokens_resolve_to_the_running_version(self):
        subs = doc_substitutions("9.9.9")
        self.assertEqual(subs["{{APP_VERSION}}"], "9.9.9")
        self.assertEqual(subs["{{MAC_ARM64_DMG}}"], "VAST-Reporter-v9.9.9-mac-arm64.dmg")
        self.assertEqual(subs["{{MAC_X64_DMG}}"], "VAST-Reporter-v9.9.9-mac-x64.dmg")
        self.assertEqual(subs["{{WIN_ZIP}}"], "VAST-Reporter-v9.9.9-win.zip")

    def test_substitution_replaces_every_occurrence(self):
        rendered = _apply_doc_substitutions("{{APP_VERSION}} and again {{APP_VERSION}}")
        self.assertNotIn("{{APP_VERSION}}", rendered)

    def test_registered_docs_leave_no_unresolved_tokens(self):
        """A typo'd token would render literally to the user."""
        known = set(doc_substitutions())
        pattern = re.compile(r"\{\{[A-Z0-9_]+\}\}")
        for rel_path in _registry_paths():
            text = (PROJECT_ROOT / rel_path).read_text(encoding="utf-8")
            with self.subTest(doc=rel_path):
                unknown = {token for token in pattern.findall(text) if token not in known}
                self.assertEqual(unknown, set(), f"{rel_path} uses undefined tokens: {sorted(unknown)}")


if __name__ == "__main__":
    unittest.main()
