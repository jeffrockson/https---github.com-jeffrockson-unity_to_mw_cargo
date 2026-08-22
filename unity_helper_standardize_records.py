# pylint: disable=line-too-long
"""Standardizes records by adding missing fields and coercing lists."""
import json
from pathlib import Path

from unity_compile_domain_data import META_FIELDS, META_ITEMS, META_TYPES, META_TYPE_GUID_LIST, META_TYPE_GUID, META_TYPE_INT, META_TYPE_FLOAT, META_TYPE_BOOL, META_TYPE_STRING



ROOT_PATH = Path(__file__).parent.parent
WRITE_STANDARDIZED_DATA_PATH = ROOT_PATH / "standardized_domain_data.json"

META_KEY_FIELDS = "META_DOMAIN_FIELDS"
DOMAIN_DATA_KEY = "domains_data"



def has_subtree_match(schema_node: dict) -> bool:
    """Checks if the schema node contains a fields and items subtree that match."""
    fields_subtree = schema_node.get(META_FIELDS, None)
    items_subtree = schema_node.get(META_ITEMS, None)
    if fields_subtree is None or items_subtree is None:
        return False
    items_subtree = items_subtree.get(META_FIELDS, None)
    if items_subtree is None:
        return False
    return fields_subtree == items_subtree

def is_guid_list(schema_node: dict) -> bool:
    """Checks if the schema node is a GUID list."""
    upper_node_type = schema_node.get(META_TYPES, None)
    inner_item_type = schema_node.get(META_ITEMS, None)
    if upper_node_type is None or inner_item_type is None:
        return False
    inner_item_type = inner_item_type.get(META_TYPES, None)
    if inner_item_type is None:
        return False
    return upper_node_type == [META_TYPE_GUID_LIST] and inner_item_type == [META_TYPE_GUID]

def is_list_of_scalars(schema_node: dict) -> bool:
    """Checks if the schema node is a list."""
    list_type = schema_node.get(META_ITEMS, None)
    if list_type is None:
        return False
    return list_type.get(META_TYPES) is not None

def is_list_of_dicts(schema_node: dict) -> bool:
    """Checks if the schema node is a list of dicts."""
    list_type = schema_node.get(META_ITEMS, None)
    if list_type is None:
        return False
    return list_type.get(META_FIELDS) is not None

def is_dict(schema_node: dict) -> bool:
    """Checks if the schema node is a dict."""
    return schema_node.get(META_FIELDS) is not None

def is_scalar(schema_node: dict) -> bool:
    """Checks if the schema node is a scalar."""
    return schema_node.get(META_TYPES) is not None

def build_template_node_from_schema_node(domain_schema_node: dict) -> dict:
    """Builds a dict template from a schema node."""
    template_node = {}
    for field_name, child in domain_schema_node.items():
        if has_subtree_match(child):
            inner_template = build_template_node_from_schema_node(child[META_FIELDS])
            template_node[field_name] = [inner_template]
        elif is_guid_list(child):
            template_node[field_name] = []
        elif is_list_of_dicts(child):
            inner_template = build_template_node_from_schema_node(child[META_ITEMS][META_FIELDS])
            template_node[field_name] = [inner_template]
        elif is_list_of_scalars(child):
            template_node[field_name] = []
        elif is_dict(child):
            inner_template = build_template_node_from_schema_node(child[META_FIELDS])
            template_node[field_name] = inner_template
        elif is_scalar(child):
            template_node[field_name] = None
        else:
            raise ValueError(f"Invalid schema node: {child}")
    return template_node


def build_template_from_schema(domain_schema: dict) -> dict:
    """Builds a dict template from a schema."""
    template = {}
    for domain, domain_schema in domain_schema.items():
        template[domain] = build_template_node_from_schema_node(domain_schema)
    return template



def standardize_domain_data(domain: str, domain_data: dict, schema: dict) -> dict:
    """Standardizes the data for a domain."""
    standardized = {}
    for key in schema.keys():




def standardize_records(all_domains_data: dict) -> dict:
    """Standardizes records by adding missing fields and coercing lists."""
    standardized_data = {
        DOMAIN_DATA_KEY = {}
    }
    schema = domain_data[META_KEY_FIELDS]
    for domain, domain_data in all_domains_data[DOMAIN_DATA_KEY].items():
        standardized_domain = standardize_domain_data(domain, domain_data, schema[domain])
        standardized_data[DOMAIN_DATA_KEY][domain] = standardized_domain
    return standardized_data



if __name__ == "__main__":
    with open(ROOT_PATH / "domain_data.json", "r", encoding="utf-8") as file:
        loaded_domain_data = json.load(file)
    standardized_data = standardize_records(loaded_domain_data)
    with open(WRITE_STANDARDIZED_DATA_PATH, "w", encoding="utf-8") as file:
        json.dump(standardized_data, file, indent=4)