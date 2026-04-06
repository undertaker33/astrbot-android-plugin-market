# AstrBot Android Plugin Market

AstrBot Android Plugin Market is the central index repository for Android Native plugins.

This repository is an index only:

- It does not store plugin source code.
- It does not store plugin zip packages.
- Every plugin must live in its own independent repository.
- This repository only maintains the market catalog consumed by the Android client.

## Repository Layout

```text
astrbot-android-plugin-market/
  plugins/
    <pluginId>.json
  scripts/
    build_catalog.py
  catalog.metadata.json
  catalog.json
  catalog.schema.json
  plugin-entry.schema.json
```

## How It Works

1. Each plugin author maintains an independent GitHub repository.
2. The plugin author publishes a plugin zip in that repository, usually through GitHub Releases.
3. The plugin author submits or updates exactly one file here:
   - `plugins/<pluginId>.json`
4. GitHub Actions validates the entry file and rebuilds the root `catalog.json`.
5. The Android client fetches this repository's `catalog.json`.
6. The market page shows plugins from the catalog and installs packages through each plugin's `packageUrl`.

## Author Contribution Model

Plugin authors should not edit the root `catalog.json` directly.

Instead:

- create or update `plugins/<pluginId>.json`
- keep `pluginId` stable
- publish plugin packages in the plugin's own repository
- update the `versions` list when publishing a new release

The root `catalog.json` is a generated file.

Version-level `publishedAt` may be omitted in `plugins/<pluginId>.json` when the package URL is a standard GitHub Release download URL. The catalog builder will derive it automatically from the release metadata.

## Current Files

- `plugins/`: one file per plugin entry
- `catalog.metadata.json`: top-level source metadata
- `catalog.json`: the generated live market index
- `catalog.schema.json`: reference schema for catalog maintenance
- `plugin-entry.schema.json`: schema for single plugin entry files
- `scripts/build_catalog.py`: builds the root catalog from `plugins/*.json`
- `CONTRIBUTING.md`: how plugin authors add or update entries

## Distribution

The first-stage distribution model is static:

- `catalog.json` is published through GitHub Raw or GitHub Pages.
- Plugin packages are published through each plugin repository's GitHub Releases.

The Android client should fetch a direct `catalog.json` URL. It should not use:

- a GitHub repository homepage
- a GitHub Release page
- a GitHub `blob` page

## Current Market Source

- Repository: `https://github.com/undertaker33/astrbot-android-plugin-market`
- Raw catalog URL: `https://raw.githubusercontent.com/undertaker33/astrbot-android-plugin-market/main/catalog.json`
