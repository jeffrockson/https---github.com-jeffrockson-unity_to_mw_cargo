"""
Orchestrates conversion of AssetRipper extracted project to cargo-query-ready mediawiki data.
"""
from sys import stdout
from pathlib import Path

from unity_assemble_guid_index import assemble_guid_index
from unity_build_model_registry import build_model_registry
from unity_compile_domain_data import compile_domain_data
from unity_deploy_standardization import deploy_standardization
from unity_extract_cargo_manifest import extract_cargo_manifest
from unity_format_wiki_pages import format_wiki_pages
from unity_go_bot_upload import go_bot_upload



ROOT_PATH = Path(__file__).parent

REGISTRY_ASSET_PATHS = [
    ROOT_PATH / "Assets" / "MonoBehaviour" / "Settings.asset",
]



if __name__ == "__main__":
    stdout.write("Starting Unity game data pipeline\n---\n")
    guid_index = assemble_guid_index()
    model_registry = build_model_registry(REGISTRY_ASSET_PATHS)
    domain_data = compile_domain_data(model_registry, guid_index)
    standardized = deploy_standardization(domain_data)
    cargo_manifest = extract_cargo_manifest(standardized)
    wiki_content = format_wiki_pages(cargo_manifest)
    go_bot_upload(wiki_content, verbose=True)
    stdout.write("\n---\nFinished Unity game data pipeline\n")