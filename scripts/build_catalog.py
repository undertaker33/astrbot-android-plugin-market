import argparse
import copy
import datetime as dt
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


DEFAULT_CATALOG_URL = (
    "https://raw.githubusercontent.com/undertaker33/"
    "astrbot-android-plugin-market/main/catalog.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_plugin_entries(plugins_dir: Path) -> list[dict]:
    entries: list[dict] = []
    for path in sorted(plugins_dir.glob("*.json")):
        entry = load_json(path)
        if entry.get("pluginId") != path.stem:
            raise ValueError(
                f"Plugin entry filename mismatch: {path.name} does not match "
                f"pluginId {entry.get('pluginId')!r}"
            )
        entries.append(entry)
    return entries


def parse_github_release_download_url(package_url: str) -> tuple[str, str, str] | None:
    parsed = urlparse(package_url)
    if parsed.netloc != "github.com":
        return None

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 6:
        return None
    owner, repo, release_segment, download_segment, tag = parts[:5]
    if release_segment != "releases" or download_segment != "download":
        return None
    return owner, repo, tag


def fetch_release_published_at_millis(package_url: str) -> int:
    release_ref = parse_github_release_download_url(package_url)
    if not release_ref:
        raise ValueError(
            "Missing publishedAt and packageUrl is not a standard GitHub Release "
            f"download URL: {package_url}"
        )

    owner, repo, tag = release_ref
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "astrbot-android-plugin-market-builder",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(api_url, headers=headers)
    with urlopen(request) as response:
        payload = json.loads(response.read().decode("utf-8"))

    published_at = payload.get("published_at")
    if not published_at:
        raise ValueError(f"GitHub release {owner}/{repo}@{tag} has no published_at value")

    return int(dt.datetime.fromisoformat(published_at.replace("Z", "+00:00")).timestamp() * 1000)


def hydrate_plugin_entries(entries: list[dict]) -> list[dict]:
    hydrated = copy.deepcopy(entries)
    for entry in hydrated:
        for version in entry.get("versions", []):
            published_at = version.get("publishedAt")
            if isinstance(published_at, int) and published_at > 0:
                continue
            version["publishedAt"] = fetch_release_published_at_millis(version["packageUrl"])
    return hydrated


def compute_updated_at(entries: list[dict]) -> int:
    timestamps = [
        version.get("publishedAt", 0)
        for entry in entries
        for version in entry.get("versions", [])
        if isinstance(version.get("publishedAt", 0), int)
    ]
    return max(timestamps, default=0)


def build_catalog(repo_root: Path) -> dict:
    metadata = load_json(repo_root / "catalog.metadata.json")
    entries = hydrate_plugin_entries(load_plugin_entries(repo_root / "plugins"))
    return {
        "sourceId": metadata["sourceId"],
        "title": metadata["title"],
        "catalogUrl": metadata.get("catalogUrl", DEFAULT_CATALOG_URL),
        "updatedAt": compute_updated_at(entries),
        "plugins": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default="catalog.json")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = repo_root / output_path

    catalog = build_catalog(repo_root)
    output_path.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
