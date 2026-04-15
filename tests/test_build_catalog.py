import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_catalog  # type: ignore  # noqa: E402


class BuildCatalogTest(unittest.TestCase):
    def test_builds_catalog_from_plugin_entry_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            plugins_dir = repo_root / "plugins"
            plugins_dir.mkdir(parents=True, exist_ok=True)
            (repo_root / "catalog.metadata.json").write_text(
                json.dumps(
                    {
                        "sourceId": "undertaker33.elymbot.plugin.market",
                        "title": "ElymBot Plugin Market",
                        "catalogUrl": "https://raw.githubusercontent.com/undertaker33/ElymBot-plugin-market/main/catalog.json",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            entry = {
                "pluginId": "cc.astrbot.android.plugin.demo",
                "title": "Demo Plugin",
                "author": "tester",
                "description": "A demo plugin entry.",
                "entrySummary": "Demo summary.",
                "repoUrl": "https://github.com/example/demo-plugin",
                "scenarios": ["demo"],
                "versions": [
                    {
                        "version": "1.0.0",
                        "packageUrl": "https://github.com/example/demo-plugin/releases/download/v1/demo.zip",
                        "publishedAt": 1776000000000,
                        "protocolVersion": 1,
                        "minHostVersion": "0.4.0",
                        "maxHostVersion": "",
                        "permissions": [],
                        "changelog": "Initial release."
                    }
                ]
            }

            (plugins_dir / "cc.astrbot.android.plugin.demo.json").write_text(
                json.dumps(entry, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            output_path = repo_root / "catalog.json"
            subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve().parents[1] / "scripts" / "build_catalog.py"),
                    "--repo-root",
                    str(repo_root),
                    "--output",
                    str(output_path),
                ],
                check=True,
            )

            built = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(
                built["catalogUrl"],
                "https://raw.githubusercontent.com/undertaker33/ElymBot-plugin-market/main/catalog.json",
            )
            self.assertEqual(built["updatedAt"], 1776000000000)
            self.assertEqual(len(built["plugins"]), 1)
            self.assertEqual(built["plugins"][0]["pluginId"], "cc.astrbot.android.plugin.demo")

    def test_fills_missing_published_at_from_github_release(self) -> None:
        entries = [
            {
                "pluginId": "cc.astrbot.android.plugin.demo",
                "title": "Demo Plugin",
                "author": "tester",
                "description": "A demo plugin entry.",
                "entrySummary": "Demo summary.",
                "repoUrl": "https://github.com/example/demo-plugin",
                "versions": [
                    {
                        "version": "1.0.0",
                        "packageUrl": "https://github.com/example/demo-plugin/releases/download/v1/demo.zip",
                        "protocolVersion": 1,
                        "minHostVersion": "0.4.0",
                        "maxHostVersion": "",
                        "permissions": [],
                        "changelog": "Initial release."
                    }
                ],
            }
        ]

        with mock.patch.object(
            build_catalog,
            "fetch_release_published_at_millis",
            return_value=1776000000000,
        ) as fetch_mock:
            hydrated = build_catalog.hydrate_plugin_entries(entries)

        self.assertEqual(
            hydrated[0]["versions"][0]["publishedAt"],
            1776000000000,
        )
        fetch_mock.assert_called_once_with(
            "https://github.com/example/demo-plugin/releases/download/v1/demo.zip"
        )

    def test_hydrate_adds_repository_url_alias_and_version_defaults(self) -> None:
        entries = [
            {
                "pluginId": "cc.astrbot.android.plugin.demo",
                "title": "Demo Plugin",
                "author": "tester",
                "description": "A demo plugin entry.",
                "entrySummary": "Demo summary.",
                "repoUrl": "https://github.com/example/demo-plugin",
                "versions": [
                    {
                        "version": "1.0.0",
                        "packageUrl": "https://github.com/example/demo-plugin/releases/download/v1/demo.zip",
                        "publishedAt": 1776000000000,
                        "minHostVersion": "0.4.0",
                    }
                ],
            }
        ]

        hydrated = build_catalog.hydrate_plugin_entries(entries)

        self.assertEqual(
            hydrated[0]["repositoryUrl"],
            "https://github.com/example/demo-plugin",
        )
        self.assertEqual(hydrated[0]["versions"][0]["protocolVersion"], 1)
        self.assertEqual(hydrated[0]["versions"][0]["maxHostVersion"], "")
        self.assertEqual(hydrated[0]["versions"][0]["permissions"], [])
        self.assertEqual(hydrated[0]["versions"][0]["changelog"], "")

    def test_load_plugin_entries_rejects_filename_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plugins_dir = Path(temp_dir)
            (plugins_dir / "wrong-name.json").write_text(
                json.dumps(
                    {
                        "pluginId": "cc.astrbot.android.plugin.demo",
                        "title": "Demo Plugin",
                        "author": "tester",
                        "description": "A demo plugin entry.",
                        "entrySummary": "Demo summary.",
                        "versions": [
                            {
                                "version": "1.0.0",
                                "packageUrl": "https://github.com/example/demo-plugin/releases/download/v1/demo.zip",
                                "publishedAt": 1776000000000,
                                "minHostVersion": "0.4.0",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "filename mismatch"):
                build_catalog.load_plugin_entries(plugins_dir)

    def test_hydrate_requires_published_at_for_non_release_download_urls(self) -> None:
        entries = [
            {
                "pluginId": "cc.astrbot.android.plugin.demo",
                "title": "Demo Plugin",
                "author": "tester",
                "description": "A demo plugin entry.",
                "entrySummary": "Demo summary.",
                "repoUrl": "https://github.com/example/demo-plugin",
                "versions": [
                    {
                        "version": "1.0.0",
                        "packageUrl": "https://downloads.example.com/demo.zip",
                        "minHostVersion": "0.4.0",
                    }
                ],
            }
        ]

        with self.assertRaisesRegex(ValueError, "Missing publishedAt"):
            build_catalog.hydrate_plugin_entries(entries)


if __name__ == "__main__":
    unittest.main()
