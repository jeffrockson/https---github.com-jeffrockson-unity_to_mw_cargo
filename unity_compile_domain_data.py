# pylint: disable=line-too-long, no-else-return, too-many-arguments, too-many-positional-arguments, too-many-return-statements
"""
Gathers domain data for all domains from asset files in the model registry and the guid index.
"""
import json
import re
from sys import stdout
from pathlib import Path

from unity_helper_parse_yaml import parse_yaml
from unity_helper_normalize_asset_tree import normalize_asset_tree
from unity_helper_merge_config import merge_config

from unity_orchestrator import GAME_CONFIG



ROOT_PATH = Path(__file__).parent
READ_ENGLISH_STRINGS_PATH = ROOT_PATH / "Assets" / "Resources" / "texts" / "en.json"
WRITE_DOMAIN_DATA_PATH = ROOT_PATH / "domain_data.json"

MODEL_KEY = "model_registry"

META_KEY_PREFIX = "META_DOMAIN_"
META_KEY_FIELDS = META_KEY_PREFIX + "FIELDS"
META_KEY_GUID_REF_INDEX = META_KEY_PREFIX + "REF_INDEX"

META_FIELDS = "META_FIELDS"
META_ITEMS = "META_ITEMS"
META_TYPES = "META_TYPES"

META_TYPE_NULL = "null"
META_TYPE_BOOL = "Boolean"
META_TYPE_INT = "Integer"
META_TYPE_FLOAT = "Float"
META_TYPE_STRING = "Text"
META_TYPE_GUID = "String"
META_TYPE_GUID_LIST = "List of String"
META_TYPE_LIST = "inspect list"
META_TYPE_DICT = "inspect dict"
META_TYPE_UNKNOWN = "must inspect"

DATA_KEY = "domains_data"

CONFIG_EXCLUDE_KEY = "exclude"
CONFIG_EXPAND_KEY = "expand"
CONFIG_SEPARATE_KEY = "separate"
SEPARATE_GUID_PREFIX = "guid_prefix"
SEPARATE_DOMAIN = "domain"
CONFIG_DEDUPE_KEY= "deduplication"
DEDUPE_KEEP = "keep"
DEDUPE_REMOVE = "remove"
DEDUPE_DOMAIN = "domain"
DEDUPE_KEY = "key"

GUID_PATTERN = re.compile(r"([0-9a-f]{32})")
UNIQUE_NAME_PATTERN = re.compile(r"m_Name")

L10N_KEY = "key"
L10N_ENGLISH_KEY_SUFFIX = "_en"

TESTING_ITERATION_LIMIT = 15



def register_references_in_list(node_key: str, node: list, references: dict) -> dict:
    """Registers all guid references in the list."""
    for item in node:
        if isinstance(item, str) and GUID_PATTERN.fullmatch(item):
            if item not in references:
                references[item] = []
            if node_key not in references[item]:
                references[item].append(node_key)
        elif isinstance(item, dict):
            register_references_in_dict(item, references)
    return references

def register_references_in_dict(node: dict, references: dict) -> dict:
    """Registers all guid references in the node."""
    for key, value in node.items():
        if isinstance(value, str) and GUID_PATTERN.fullmatch(value):
            if value not in references:
                references[value] = []
            if key not in references[value]:
                references[value].append(key)
        elif isinstance(value, dict):
            register_references_in_dict(value, references)
        elif isinstance(value, list):
            register_references_in_list(key, value, references)
    return references

def register_references(model_data: dict) -> dict:
    """Registers all guid references in the model data."""
    references = {}
    for _, domain_data in model_data.items():
        if not isinstance(domain_data, dict):
            continue
        for _, guid_data in domain_data.items():
            if not isinstance(guid_data, dict):
                continue
            register_references_in_dict(guid_data, references)
    return references



def classify_field_type(key: str, value: object) -> str:
    """Classifies the field type based on the python type of the value."""
    if value is None:
        return META_TYPE_NULL
    if isinstance(value, bool):
        return META_TYPE_BOOL
    if isinstance(value, float):
        return META_TYPE_FLOAT
    if isinstance(value, int):
        return META_TYPE_INT
    if isinstance(value, str):
        if GUID_PATTERN.fullmatch(value) or UNIQUE_NAME_PATTERN.fullmatch(key):
            return META_TYPE_GUID
        else:
            return META_TYPE_STRING
    if isinstance(value, list):
        if value and all(isinstance(item, str) and GUID_PATTERN.fullmatch(item) for item in value):
            return META_TYPE_GUID_LIST
        return META_TYPE_LIST
    if isinstance(value, dict):
        return META_TYPE_DICT
    return META_TYPE_UNKNOWN

def finalize_fields_schema_for_node(schema_node: dict) -> None:
    """Finishes the schema by reducing types and converting sets to lists."""
    if META_TYPES in schema_node:
        types = schema_node[META_TYPES]
        if META_TYPE_INT in types and META_TYPE_FLOAT in types:
            types.discard(META_TYPE_INT)
        if META_TYPE_NULL in types and len(types) > 1:
            types.discard(META_TYPE_NULL)
        if META_TYPE_INT in types and META_TYPE_STRING in types:
            types.discard(META_TYPE_INT)
        if META_TYPE_GUID in types and META_TYPE_STRING in types:
            types.discard(META_TYPE_GUID)
        if types:
            schema_node[META_TYPES] = sorted(types)
        else:
            del schema_node[META_TYPES]
    if META_FIELDS in schema_node:
        for child in schema_node[META_FIELDS].values():
            finalize_fields_schema_for_node(child)
    if META_ITEMS in schema_node:
        finalize_fields_schema_for_node(schema_node[META_ITEMS])

def finalize_fields_schema(schema: dict) -> None:
    """Finishes the schema."""
    for node in schema.values():
        finalize_fields_schema_for_node(node)

def register_domain_fields_in_value(key: str, value: object, schema_node: dict) -> None:
    """Classify value, merge type on this node, recurse into dict/list children."""
    field_type = classify_field_type(key, value)
    if field_type not in (META_TYPE_DICT, META_TYPE_LIST):
        schema_node.setdefault(META_TYPES, set()).add(field_type)
    if isinstance(value, dict):
        register_domain_fields_in_dict(value, schema_node.setdefault(META_FIELDS, {}))
    elif isinstance(value, list):
        register_domain_fields_in_list(key, value, schema_node)

def register_domain_fields_in_dict(node: dict, schema_node: dict) -> None:
    """Merges each key into schema in one dict node."""
    for key, value in node.items():
        child = schema_node.setdefault(key, {})
        register_domain_fields_in_value(key, value, child)

def register_domain_fields_in_list(key: str, node: list, schema_node: dict) -> None:
    """Merges each item into schema in one list node."""
    items_schema = schema_node.setdefault(META_ITEMS, {})
    for item in node:
        register_domain_fields_in_value(key, item, items_schema)

def register_domain_fields(model_data: dict) -> dict:
    """Registers every seen field and its seen types once per domain."""
    fields = {}
    for _, row in model_data.items():
        if not isinstance(row, dict):
            continue # should all be dicts tho
        register_domain_fields_in_dict(row, fields)
    finalize_fields_schema(fields)
    return fields



def filter_asset_data(asset_data: dict, exclude_list: list) -> dict:
    """Filters the asset data by the exclude keys."""
    for key in exclude_list:
        if key in asset_data:
            del asset_data[key]
    return asset_data



def select_asset_data_from_dict(final_node: dict, current_node: dict, include_list: list) -> dict:
    """Recursively selects the fields from include_list but flattens them to final_node."""
    if isinstance(current_node, dict):
        for key, value in current_node.items():
            if key in include_list:
                if value is not None:
                    final_node[key] = value
            elif isinstance(value, dict):
                select_asset_data_from_dict(final_node, value, include_list)
            elif isinstance(value, list):
                for item in value:
                    select_asset_data_from_dict(final_node, item, include_list)

def select_asset_data(asset_data: dict, include_list: list) -> dict:
    """Selects only the included keys."""
    new_asset_data = {}
    select_asset_data_from_dict(new_asset_data, asset_data, include_list)
    return new_asset_data



def is_string_key_node(node: dict) -> bool:
    """Checks if the node has a string key."""
    if isinstance(node, dict):
        if isinstance(node.get(L10N_KEY), str):
            return True
    return False

def add_string_key_to_node(parent_key: str, node: dict, en_strings: dict, verbose: bool) -> dict:
    """Expands a string key node with its english string."""
    string_key = node.get(L10N_KEY)
    if string_key in en_strings:
        node[L10N_KEY + L10N_ENGLISH_KEY_SUFFIX] = en_strings[string_key]
        if verbose:
            stdout.write(f"...expanded string key {string_key} under selected key {parent_key}...\n")
    return node

def expand_string_keys_in_list(node: list, en_strings: dict, verbose: bool) -> dict:
    """Recursively expands all string keys in the list."""
    for item in node:
        if isinstance(item, dict):
            expand_string_keys_in_dict(item, en_strings, verbose)
    return node

def expand_string_keys_in_dict(node: dict, en_strings: dict, verbose: bool) -> dict:
    """Expands all string keys in the node with their english strings."""
    for key in list(node.keys()):
        if is_string_key_node(node[key]):
            node[key] = add_string_key_to_node(key, node[key], en_strings, verbose)
        elif isinstance(node[key], dict):
            expand_string_keys_in_dict(node[key], en_strings, verbose)
        elif isinstance(node[key], list):
            expand_string_keys_in_list(node[key], en_strings, verbose)
    return node



def replace_selected_reference(selected_key: str, guid: str, expand_list: dict, guid_index: dict, en_strings: dict, verbose: bool) -> dict:
    """Replaces a guid inside a selected field with its asset data."""
    if verbose:
        stdout.write(f"...expanding guid {guid} under selected key {selected_key}...\n")
    if guid not in guid_index:
        stdout.write(f"...WARNING: guid {guid} not found in guid index...\n")
        return guid
    inner_asset_path = Path(guid_index[guid])
    inner_asset_data = normalize_asset_tree(parse_yaml(inner_asset_path, verbose=False), verbose=False)
    include_list = expand_list[selected_key]
    selected_asset_data = select_asset_data(inner_asset_data, include_list)
    expand_string_keys_in_dict(selected_asset_data, en_strings, verbose)
    expand_asset_data(selected_asset_data, expand_list, guid_index, en_strings, verbose)
    if verbose:
        stdout.write(f"...expanded guid {guid} with {len(selected_asset_data.keys())} keys...\n")
    return {
        "guid": guid,
        **selected_asset_data
    }

def expand_selected_field(selected_key: str, selected_value: object, expand_list: dict, guid_index: dict, en_strings: dict, verbose: bool) -> dict:
    """Expands the selected field's guids or leave as-is."""
    if selected_value is None:
        return None
    if isinstance(selected_value, str):
        if GUID_PATTERN.fullmatch(selected_value):
            return replace_selected_reference(selected_key, selected_value, expand_list, guid_index, en_strings, verbose)
        return selected_value
    elif isinstance(selected_value, list):
        new_list = []
        for item in selected_value:
            if isinstance(item, str) and GUID_PATTERN.fullmatch(item):
                new_list.append(replace_selected_reference(selected_key, item, expand_list, guid_index, en_strings, verbose))
            else:
                new_list.append(item)
        return new_list
    return selected_value

def expand_asset_data_in_list(parent_key: str, node: list, expand_list: dict, guid_index: dict, en_strings: dict, verbose: bool) -> dict:
    """Recursively looks for selected references in the list."""
    for i, item in enumerate(node):
        if isinstance(item, dict):
            expand_asset_data(item, expand_list, guid_index, en_strings, verbose)
        elif parent_key in expand_list and isinstance(item, str) and GUID_PATTERN.fullmatch(item):
            inner_asset_data = replace_selected_reference(parent_key, item, expand_list, guid_index, en_strings, verbose)
            node[i] = inner_asset_data
    return node

def expand_asset_data(node: dict, expand_list: dict, guid_index: dict, en_strings: dict, verbose: bool) -> dict:
    """Recursively looks for selected references in the dict."""
    for key in list(node.keys()):
        value = node[key]
        if key in expand_list:
            node[key] = expand_selected_field(key, value, expand_list, guid_index, en_strings, verbose)
        elif isinstance(value, dict):
            expand_asset_data(value, expand_list, guid_index, en_strings, verbose)
        elif isinstance(value, list):
            expand_asset_data_in_list(key, value, expand_list, guid_index, en_strings, verbose)
    return node



def expand_guid(guid: str, domain_config: dict, guid_index: dict, en_strings: dict, verbose: bool) -> dict:
    """Expands the registered guid into its model data."""
    if guid not in guid_index:
        stdout.write(f"...WARNING: guid {guid} not found in guid index...\n")
        return guid
    asset_path = Path(guid_index[guid])
    asset_data = normalize_asset_tree(parse_yaml(asset_path, verbose=False), verbose=False)
    filter_asset_data(asset_data, domain_config[CONFIG_EXCLUDE_KEY])
    if verbose:
        stdout.write(f"...guid expanded to {len(asset_data)} keys...\n")
    expand_string_keys_in_dict(asset_data, en_strings, verbose)
    expand_asset_data(asset_data, domain_config[CONFIG_EXPAND_KEY], guid_index, en_strings, verbose)
    return asset_data

def expand_domain(domain_config: dict, domain_model_registry: dict, guid_index: dict, en_strings: dict, verbose: bool, testing: bool) -> dict:
    """Goes through all entries in the domain model registry and expands their references."""
    model_data = {}
    item_number = 0
    iterable_domain_model_registry = domain_model_registry if isinstance(domain_model_registry, list) else [domain_model_registry]
    for guid in iterable_domain_model_registry:
        if testing and item_number > TESTING_ITERATION_LIMIT:
            return model_data
        item_number += 1
        if verbose:
            stdout.write(f"...processing guid #{item_number} of {len(iterable_domain_model_registry)}: {guid}...\n")
        asset_data = expand_guid(guid, domain_config, guid_index, en_strings, verbose)
        model_data[guid] = asset_data
        if verbose:
            stdout.write(f"...finished processing guid {guid}...\n")
    return model_data



def run_deduplication(all_config: dict, domain_data: dict, verbose: bool) -> None:
    """Runs the deduplication process."""
    deduplication_config = all_config[CONFIG_DEDUPE_KEY]
    removed_records = 0
    for dedupe_pair in deduplication_config:
        keep_domain = dedupe_pair[DEDUPE_KEEP][DEDUPE_DOMAIN]
        keep_key = dedupe_pair[DEDUPE_KEEP][DEDUPE_KEY]
        remove_domain = dedupe_pair[DEDUPE_REMOVE][DEDUPE_DOMAIN]
        remove_key = dedupe_pair[DEDUPE_REMOVE][DEDUPE_KEY]
        keep_keys = set()
        if keep_domain not in domain_data or remove_domain not in domain_data:
            continue
        for keep_record in domain_data[keep_domain].values():
            if keep_key in keep_record:
                keep_keys.add(keep_record[keep_key])
        for guid in list(domain_data[remove_domain].keys()):
            if remove_key in domain_data[remove_domain][guid]:
                remove_value = domain_data[remove_domain][guid][remove_key]
                if remove_value in keep_keys:
                    del domain_data[remove_domain][guid]
                    removed_records += 1
    if verbose:
        stdout.write(f"...removed {removed_records} duplicate records...\n")



def synthesize_new_guid(guid_prefix: str, parent_guid: str) -> str:
    """Synthesizes a new guid based on the guid prefix and parent guid."""
    borrow_length = len(parent_guid) - len(guid_prefix)
    new_guid = guid_prefix + parent_guid[:borrow_length]
    return new_guid

def run_domain_separation(all_config: dict, all_domain_data: dict, verbose: bool) -> None:
    """Runs the domain separation process on records."""
    moved_records = 0
    for domain in list(all_domain_data.keys()):
        if domain not in all_config:
            continue
        domain_data = all_domain_data[domain]
        domain_config = all_config[domain]
        if CONFIG_SEPARATE_KEY not in domain_config:
            continue
        for guid, record in domain_data.items():
            for separate_key, separation_rule in domain_config[CONFIG_SEPARATE_KEY].items():
                if separate_key not in record:
                    continue
                if record[separate_key] is None or record[separate_key] == {} or record[separate_key] == [] or record[separate_key] == "":
                    continue
                subrecord_to_move = record.pop(separate_key)
                synthetic_guid = synthesize_new_guid(separation_rule[SEPARATE_GUID_PREFIX], guid)
                record[separate_key] = synthetic_guid
                target_domain = separation_rule[SEPARATE_DOMAIN]
                if target_domain not in all_domain_data:
                    all_domain_data[target_domain] = {}
                subrecord_to_move = { separate_key: subrecord_to_move }
                all_domain_data[target_domain][synthetic_guid] = subrecord_to_move
                moved_records += 1
    if verbose:
        stdout.write(f"...separated {moved_records} records...\n")



def compile_domain_data(model_registry: dict, guid_index: dict, en_strings: dict|None = None, verbose: bool = False, testing: bool = False) -> dict:
    """Compile domain data from the model registry and guid index."""
    domain_data = {
        META_KEY_FIELDS: {},
        META_KEY_GUID_REF_INDEX: {},
        DATA_KEY: {},
    }
    with open(GAME_CONFIG, "r", encoding="utf-8") as config_file:
        all_config = json.load(config_file)
    if en_strings is None:
        with open(READ_ENGLISH_STRINGS_PATH, "r", encoding="utf-8") as strings_file:
            en_strings = json.load(strings_file)
    domain_number = 0
    for domain in model_registry[MODEL_KEY].keys():
        if verbose:
            stdout.write(f"Processing domain {domain}...\n")
        domain_number += 1
        if verbose:
            stdout.write(f"...gathering data for domain {domain} ({domain_number}/{len(model_registry[MODEL_KEY])})...\n")
        domain_config = merge_config(all_config, domain)
        domain_data[DATA_KEY][domain] = expand_domain(domain_config, model_registry[MODEL_KEY][domain], guid_index, en_strings, verbose=False, testing=False)
        if verbose:
            stdout.write(f"...finished processing domain {domain}...\n")
        if testing and domain_number > TESTING_ITERATION_LIMIT:
            break
    run_deduplication(all_config, domain_data[DATA_KEY], verbose)
    run_domain_separation(all_config, domain_data[DATA_KEY], verbose)
    for domain in list(domain_data[DATA_KEY].keys()):
        domain_data[META_KEY_FIELDS][domain] = register_domain_fields(domain_data[DATA_KEY][domain])
    domain_data[META_KEY_GUID_REF_INDEX] = register_references(domain_data[DATA_KEY])
    stdout.write(f"...finished compiling domain data for {len(domain_data[DATA_KEY])} domains...\n")
    return domain_data



if __name__ == "__main__":
    with open(ROOT_PATH / "guid_index.json", "r", encoding="utf-8") as file:
        loaded_guid_index = json.load(file)
    with open(ROOT_PATH / "model_registry.json", "r", encoding="utf-8") as file:
        loaded_model_registry = json.load(file)
    stdout.write("Compiling domain data...")
    result = compile_domain_data(loaded_model_registry, loaded_guid_index, verbose=True, testing=False)
    stdout.write("...done.\n")
    with open(WRITE_DOMAIN_DATA_PATH, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=4)
