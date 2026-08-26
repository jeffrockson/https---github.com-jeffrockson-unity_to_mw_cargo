# Unity game data → MediaWiki Cargo

**Run `py unity_orchestrator.py` from this folder** after you have extracted the Unity game assets with AssetRipper or similar, placed these scripts beside `Assets/`, configured your game in `unity_setup_domain_config.json`, and set up pywikibot to connect with your MediaWiki instance with the [Cargo](https://www.mediawiki.org/wiki/Extension:Cargo) extension. Orchestrator command walks the full pipeline: GUID index → domain data → data normalization → wiki pages → bot upload.

---

## What this does

These scripts turn a Unity game asset export into queryable Cargo tables on a MediaWiki wiki. They read YAML assets under `Assets/`, follow the game's central asset registry (for example, a centralized `Settings.asset` or multiple assets identifying primary relationships), normalize records into domains (that is, game mechanics like buildings, effects, perks, professions, etc.), and upload `Template:Dataloader/…` plus `Data:…` pages that Cargo ingests.

The orchestrator runs, in order:

1. `unity_assemble_guid_index` — scan `Assets/` → `guid_index.json`
2. `unity_build_model_registry` — read registry roots → `model_registry.json`
3. `unity_compile_domain_data` — expand assets per config → `domain_data.json`
4. `unity_deploy_standardization` — uniform record shape → `standardized_domain_data.json`
5. `unity_extract_cargo_manifest` — flatten for Cargo → `cargo_ready_manifest.json`
6. `unity_format_wiki_pages` — page content and pagination payloads → `pages_wiki_content.json`
7. `unity_go_bot_upload` — push pages to the wiki via pywikibot

Each step writes intermediate JSON in this folder for inspection and research.

For new games that haven't yet been configured:
a. find the central asset registry .asset files
b. run each script individually, research the relationships in the output file, and plan the configuration to get the most out of the Cargo queries.
Cargo SQL query limitations (1000 maximum expression depth) is a real limitation on the data pipeline that configuration attempts to resolve.

---

## Setup

### 1. Game install

Install the game normally. You need its data files on disk so AssetRipper can read them.

### 2. AssetRipper export

1. Open the game in [AssetRipper](https://github.com/AssetRipper/AssetRipper).
2. Export as a **Unity project** (not loose files only).
3. Note the export folder — it contains an `Assets/` subfolder.

### 3. Place these scripts there

Copy or clone this script collection into the **same folder as `Assets/`** (the AssetRipper export root). Example layout:

```text
ExportedProject/
  Assets/
  unity_orchestrator.py
  unity_setup_domain_config.json
  unity_*.py
  …
```

### 4. Configure the game (`unity_setup_domain_config.json`)

This file drives per-domain behavior for **your** game. The included config targets *Against the Storm*; for another title you must adapt it.

Typical knobs:

- **`all_domains`** — fields to (a) exclude in all records that contain it and (b) expand, or inline assets that are not in other domains since assets not in the registry domains will not be populated to the cargo tables
- **Per-domain blocks** (`Buildings`, `Relics`, …) — domain-specific exclude/expand/separate rules
- **`global_rename`** — rename fields that collide with SQL reserved words (`order`, `interval`, …)
- **`deduplication`** — cross-domain dedup (e.g. drop Buildings records whose `m_Name` already exists in Relics)
- **`separate`** — move a heavy or deep sub-tree into its own new top-level queryable domain (e.g. `Buildings/expeditions` → `buildingExpeditions`)

The registry root is set in `unity_orchestrator.py` (`REGISTRY_ASSET_PATHS`). Point it at your game's settings/meta asset.

English display strings are read from `Assets/Resources/texts/en.json` at compile; change the constant in the script to point to your game's string tables.

### 5. Python dependencies

```text
pip install pywikibot flatten-dict
```

PHP must be on `PATH` for Cargo maintenance during upload.

### 6. MediaWiki + Cargo

You need a running MediaWiki with Cargo installed. The upload script calls PHP maintenance scripts against your wiki install.

In `unity_go_bot_upload.py`, set `MEDIAWIKI_PATH` to your MediaWiki root (default in repo: `C:/tools/mediawiki-1.44.2` don't @ me I game on Windows).

Recommended wiki setting during bulk import: `$wgJobRunRate = 0` in `LocalSettings.php`, so jobs run when the upload script calls `runJobs` instead of mid-save.

### 7. pywikibot

Bot upload uses [pywikibot](https://www.mediawiki.org/wiki/Manual:Pywikibot). Follow upstream docs for install, bot passwords, and family configuration.

This repo includes a minimal localhost setup:

- `user-config.py` — family, username, password file location
- `families/localhost_family.py` — wiki URL (default `http://localhost:4000`)
- `user-password.cfg` — bot password (create locally; do not commit secrets)

Set `PYWIKIBOT_DIR` to this folder (the upload script does this automatically). Point the family at your wiki URL and credentials before running the orchestrator.

---

## Run

From the export root (where `Assets/` and `unity_orchestrator.py` live):

```text
py unity_orchestrator.py
```

Full import including upload can take on the order of **20+ minutes** depending on wiki server connection speed and domain depth.

All scripts can be run individually. This is helpful during research or to fix later-stage issues and avoid re-running the entire pipeline, for example, with the server connection:

```text
py unity_go_bot_upload.py
```

Use `dry_run=True` in `go_bot_upload()` (or edit the `__main__` call) to print what would be uploaded without saving.

---

## Outputs

| File | Contents |
|------|----------|
| `guid_index.json` | GUID → asset path |
| `model_registry.json` | Domain → list of registry GUIDs |
| `domain_data.json` | Expanded, compiled domain records + schema metadata |
| `standardized_domain_data.json` | Records coerced to uniform shape |
| `cargo_ready_manifest.json` | Cargo declare/store templates + per-record template calls |
| `pages_wiki_content.json` | Ready-to-upload Template and Data page bodies in very long JSON strings |

After upload, query data with Cargo on the wiki as usual (e.g. `{{#cargo_query: … }}`).

---

## Troubleshooting

- **Missing assets / GUID warnings** — export incomplete or `Assets/` path wrong.
- **Cargo column explosion / SQL errors** — too many flattened columns on one domain; use `deduplication`, `separate`, or exclude heavy nested fields in config.
- **Empty Data pages for a domain** — re-run extract after config changes; check `domains_manifests_data` in the manifest is populated.
- **PHP temp / job errors during upload** — run `php maintenance/run.php runJobs` manually from the MediaWiki root; clear stale `mw-GlobalIdGenerator*` files in `%TEMP%` if locks persist.
