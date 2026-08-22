# pylint: disable=no-else-return
"""
Normalizes an asset data tree by collapsing null and guid references.
"""
import json
from pathlib import Path
from unity_helper_parse_yaml import parse_yaml



ROOT_PATH = Path(__file__).parent



def is_null_file_ref(node) -> bool:
    """Check if a node is a null asset reference."""
    return node == {"fileID": 0}

def collapse_any_null_ref(node) -> dict:
    """Collapses null references to None."""
    if is_null_file_ref(node):
        return None
    return node



def is_file_guid_type_triplet(node) -> bool:
    """Check if a node is a file-guid-type asset reference."""
    return (isinstance(node, dict) and node.keys() == {"fileID", "guid", "type"})

def collapse_any_triplet_guid_ref(node: dict) -> dict:
    """Collapses file-guid-type triplets to just the guid."""
    if is_file_guid_type_triplet(node):
        return node["guid"]
    return node



def is_desired_asset_dereference_key(key: str) -> bool:
    """Check if a key is a desired asset dereference key."""
    return key in ["fileID", "guid", "type"]



def normalize_dict(raw_node: dict, verbose: bool) -> dict:
    """Normalizes references in the asset data tree, dict mode."""
    new_dict = {}
    for key, value in raw_node.items():
        new_dict[key] = normalize_asset_tree(value, verbose)
    return new_dict

def normalize_list(raw_node: list, verbose: bool) -> list:
    """Normalizes references in the asset data tree, list mode."""
    new_list = []
    for item in raw_node:
        new_list.append(normalize_asset_tree(item, verbose))
    return new_list

def normalize_asset_tree(raw_node: dict|list|str, verbose: bool) -> dict|list|str:
    """Normalizes references in the asset data tree, dispatching to recursive functions."""
    new_node = collapse_any_triplet_guid_ref(collapse_any_null_ref(raw_node))
    if isinstance(new_node, dict):
        return normalize_dict(new_node, verbose)
    if isinstance(new_node, list):
        return normalize_list(new_node, verbose)
    else:
        return new_node



if __name__ == "__main__":
    # pylint: disable=invalid-name
    test_asset_filename = "Haunted Ruined Bat House.asset"
    test_asset_path = ROOT_PATH / "Assets" / "MonoBehaviour" / test_asset_filename
    asset_data = parse_yaml(test_asset_path, verbose=True)
    normalized_asset_data = normalize_asset_tree(asset_data, verbose=True)
    with open(ROOT_PATH / f"{test_asset_filename}.json", "w", encoding="utf-8") as asset_data_file:
        json.dump(normalized_asset_data, asset_data_file, indent=4)
