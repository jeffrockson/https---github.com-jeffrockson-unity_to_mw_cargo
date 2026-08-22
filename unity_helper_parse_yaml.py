# pylint: disable=line-too-long
"""
Parses a Unity asset file as YAML after some pre-processing. Returns a new dict.

Makes no assumptions about content; callers need to clean it as needed.
"""
import json
import re
from sys import stdout
from pathlib import Path
import yaml



ROOT_PATH = Path(__file__).parent

REPLACE_YAML_PATTERN = re.compile(r"^%YAML.*$", flags=re.MULTILINE)
REPLACE_TAG_PATTERN = re.compile(r"^%TAG.*$", flags=re.MULTILINE)
CLEAN_DOC_PATTERN = re.compile(r"^---\s*!u!\d+", flags=re.MULTILINE)



def parse_yaml(asset_path: Path, verbose: bool = False) -> dict:
    """Parse an asset file and return a dictionary of the asset's contents."""
    if verbose:
        stdout.write(f"Loading asset file {asset_path} for YAML parsing...\n")
    text = asset_path.read_text(encoding="utf-8")
    text_len = len(text)
    if verbose:
        stdout.write(f"...starting with {text_len} characters...\n")
    text = REPLACE_YAML_PATTERN.sub("", text)
    text = REPLACE_TAG_PATTERN.sub("", text)
    text = CLEAN_DOC_PATTERN.sub("---", text)
    if verbose:
        stdout.write(f"...pre-processing removed {text_len - len(text)} characters...\n")
    yaml_raw = yaml.safe_load(text)
    assert len(yaml_raw) == 1, f"Expected exactly one top-level key, got {list(yaml_raw)}"
    raw_data = next(iter(yaml_raw.values())) # promote out from under MonoBehaviour
    if verbose:
        stdout.write(f"...asset data parsed from {asset_path} into {len(raw_data)} top-level keys...\n")
    return raw_data



if __name__ == "__main__":
    # pylint: disable=invalid-name
    test_asset_filename = "Haunted Ruined Bad House.asset"
    test_asset_path = ROOT_PATH / "Assets" / "MonoBehaviour" / test_asset_filename
    asset_data = parse_yaml(test_asset_path, verbose=True)
    with open(ROOT_PATH / f"{test_asset_filename}.json", "w", encoding="utf-8") as asset_data_file:
        json.dump(asset_data, asset_data_file, indent=4)
