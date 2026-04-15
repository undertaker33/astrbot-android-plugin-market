import argparse
import copy
import datetime as dt
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import os


DEFAULT_CATALOG_URL = (
    "https://raw.githubusercontent.com/undertaker33/"
    "ElymBot-plugin-market/main/catalog.json"
)
DEFAULT_PROTOCOL_VERSION = 1


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require_non_blank_string(value: object, field_name: str, *, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} is missing required non-blank field {field_name!r}")
    return value.strip()


def validate_plugin_version(version: dict, *, plugin_id: str, index: int) -> None:
    context = f"plugins/{plugin_id}.json versions[{index}]"
    require_non_blank_string(version.get("version"), "version", context=context)
    require_non_blank_string(version.get("packageUrl"), "packageUrl", context=context)
    require_non_blank_string(version.get("minHostVersion"), "minHostVersion", context=context)

    published_at = version.get("publishedAt")
    if published_at is not None and (not isinstance(published_at, int) or published_at < 0):
        raise ValueError(f"{context} has invalid publishedAt {published_at!r}")


def validate_plugin_entry(entry: dict, path: Path) -> None:
    plugin_id = require_non_blank_string(entry.get("pluginId"), "pluginId", context=str(path))
    for field_name in ("title", "author", "description", "entrySummary"):
        require_non_blank_string(entry.get(field_name), field_name, context=f"plugins/{plugin_id}.json")

    versions = entry.get("versions")
    if not isinstance(versions, list) or not versions:
        raise ValueError(f"plugins/{plugin_id}.json must define a non-empty versions list")
    for index, version in enumerate(versions):
        if not isinstance(version, dict):
            raise ValueError(f"plugins/{plugin_id}.json versions[{index}] must be an object")
        validate_plugin_version(version, plugin_id=plugin_id, index=index)

    scenarios = entry.get("scenarios", [])
    if not isinstance(scenarios, list):
        raise ValueError(f"plugins/{plugin_id}.json scenarios must be a list")
    for index, scenario in enumerate(scenarios):
        require_non_blank_string(
            scenario,
            f"scenarios[{index}]",
            context=f"plugins/{plugin_id}.json",
        )


def load_plugin_entries(plugins_dir: Path) -> list[dict]:
    entries: list[dict] = []
    for path in sorted(plugins_dir.glob("*.json")):
        entry = load_json(path)
        if entry.get("pluginId") != path.stem:
            raise ValueError(
                f"Plugin entry filename mismatch: {path.name} does not match "
                f"pluginId {entry.get('pluginId')!r}"
            )
        validate_plugin_entry(entry, path)
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
        "User-Agent": "elymbot-plugin-market-builder",
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
        repo_url = entry.get("repoUrl")
        if isinstance(repo_url, str) and repo_url.strip() and not entry.get("repositoryUrl"):
            entry["repositoryUrl"] = repo_url.strip()

        for version in entry.get("versions", []):
            version.setdefault("protocolVersion", DEFAULT_PROTOCOL_VERSION)
            version.setdefault("maxHostVersion", "")
            version.setdefault("permissions", [])
            version.setdefault("changelog", "")
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
