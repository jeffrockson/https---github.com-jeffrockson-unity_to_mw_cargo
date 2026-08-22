"""
Orchestrates conversion of AssetRipper extracted project to cargo-query-ready mediawiki data.
"""
import json
from pathlib import Path

from unity_assemble_guid_index import assemble_guid_index
from unity_build_model_registry import build_model_registry
from unity_compile_domain_data import compile_domain_data
from unity_develop_cargo_manifest import develop_cargo_manifest



ROOT_PATH = Path(__file__).parent

REGISTRY_ASSET_PATHS = [
    ROOT_PATH / "Assets" / "MonoBehaviour" / "Settings.asset.meta",
]



if __name__ == "__main__":
    guid_index = assemble_guid_index()
    model_registry = build_model_registry(REGISTRY_ASSET_PATHS, guid_index)
    domain_data = compile_domain_data(model_registry, guid_index)
    cargo_manifest = develop_cargo_manifest(domain_data)
    with open(ROOT_PATH / "cargo_manifest.json", "w", encoding="utf-8") as cargo_manifest_file:
        json.dump(cargo_manifest, cargo_manifest_file, indent=4)
