# pylint: disable=line-too-long, too-many-arguments
"""
Generates wiki-ready templates from domain data for storing by Cargo Mediawiki extension.

The manifest has four sections:
- analysis metadata
- #cargo_declare templates - MANIFEST_TEMPLATES_DECLARE
- #cargo_store templates - MANIFEST_TEMPLATES_STORE
- data - MANIFEST_DATA
- page index (division of data into pages) - MANIFEST_DATA_PAGES
"""
import json
import re
from sys import stdout
from pathlib import Path

from unity_compile_domain_data import classify_field_type



ROOT_PATH = Path(__file__).parent
WRITE_CARGO_DATA_PATH = ROOT_PATH / "cargo_ready_domain_data.txt"

DOMAIN_DATA_KEY = "domains_data"

META_KEY_PREFIX = "META_MANIFEST"
META_KEY_PAGES = META_KEY_PREFIX + "_PAGES"

MANIFEST_KEY_PREFIX = "domains_manifests"
MANIFEST_TEMPLATES_DECLARE = MANIFEST_KEY_PREFIX + "_declare_templates"
MANIFEST_TEMPLATES_STORE = MANIFEST_KEY_PREFIX + "_store_templates"
MANIFEST_DATA = MANIFEST_KEY_PREFIX + "_data"
MANIFEST_PAGES = MANIFEST_KEY_PREFIX + "_data_pages"

LIST_FIELD_TYPES = "seen_types"
FINAL_FIELD_TYPE = "type"

PATH_JOIN_CHARACTER = "_"

TEMPLATES_NAMESPACE = "Template"
DATA_NAMESPACE = "Data"

TESTING_ITERATION_LIMIT = 10



def build_domain_manifest(domain: str, domain_data: dict, manifest: dict, verbose: bool) -> dict:
    """Builds the manifest for a domain."""
    manifest[MANIFEST_TEMPLATES_DECLARE][domain] = {}
    manifest[MANIFEST_TEMPLATES_STORE][domain] = {}
    manifest[MANIFEST_DATA][domain] = {}
    manifest[MANIFEST_PAGES][domain] = {}
    template_fields = {}
    later_key_queue = []
    prototype = next(iter(domain_data))
    for prototype_key in prototype.keys():
        template_fields[prototype_key] = {
            LIST_FIELD_TYPES: {}
        }
        for guid, record in domain_data.items():
            if prototype_key not in record:
                later_key_queue.append(prototype_key)
                continue
            field_type = classify_field_type(prototype_key, record[prototype_key])
            template_fields[prototype_key][LIST_FIELD_TYPES].setdefault(field_type, []).append(guid)



def develop_cargo_manifest(all_domain_data: dict, verbose: bool = False, testing: bool = False) -> str:
    """Converts domain data and meta data into cargo-ready manifest."""
    manifest = {
        META_KEY_PAGES: {},
        MANIFEST_KEY_PREFIX: {
            MANIFEST_TEMPLATES_DECLARE: {},
            MANIFEST_TEMPLATES_STORE: {},
            MANIFEST_DATA: {},
            MANIFEST_PAGES: {}
        }
    }
    for domain, domain_data in all_domain_data[DOMAIN_DATA_KEY].items():
        if verbose:
            stdout.write(f"Developing manifest for domain {domain}...\n")
        build_domain_manifest(domain, domain_data, manifest, verbose, testing)
        if testing and domain > TESTING_ITERATION_LIMIT:
            break
    return manifest



if __name__ == "__main__":
    with open(ROOT_PATH / "guid_index.json", "r", encoding="utf-8") as file:
        loaded_guid_index = json.load(file)
    with open(ROOT_PATH / "domain_data.json", "r", encoding="utf-8") as file:
        loaded_domain_data = json.load(file)
    stdout.write("Developing domain data into cargo manifest...\n")
    cargo_manifest = develop_cargo_manifest(loaded_domain_data)#, verbose=True, testing=True)
    with open(WRITE_CARGO_DATA_PATH, "w", encoding="utf-8") as file:
        json.dump(cargo_manifest, file, indent=4)
    stdout.write("...done saving cargo-ready data.\n")
