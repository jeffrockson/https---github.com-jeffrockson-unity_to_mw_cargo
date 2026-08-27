# pylint: disable=line-too-long, no-else-return
"""
Loads specified Unity asset files that centralize registrations of other asset references under 
their respective model domains or game-mechanics categories. Requires the guid index to be built
first.

The registry is one dictionary consisting of the following:
- META REGISTRY
-- _DOMAIN_LIST : a list of all model domains (or game mechanics categories)
-- _INDEX : a dictionary of all GUIDs and which domains they appear in
- model_registry : the dictionary of all assets, per domain, loaded in from their asset files.

Writes the registry to a file for inspection but also returns it to the caller, so that the caller
does not need to read the file. The file will be in the same folder as this script.
"""
import json
import re
from sys import stdout
from pathlib import Path

from unity_helper_parse_yaml import parse_yaml
from unity_helper_normalize_asset_tree import normalize_asset_tree



ROOT_PATH = Path(__file__).parent
READ_GUID_INDEX_PATH = ROOT_PATH / "guid_index.json"
WRITE_MODEL_REGISTRY_PATH = ROOT_PATH / "model_registry.json"

MODEL_KEY = "model_registry"

META_KEY = "META_REGISTRY"
META_KEY_DOMAIN_LIST = META_KEY + "_DOMAIN_LIST"
META_KEY_INDEX = META_KEY + "_INDEX"

REGISTRY_FIELDS_TO_EXCLUDE = [
    "m_ObjectHideFlags",
    "m_CorrespondingSourceObject",
    "m_PrefabInstance",
    "m_PrefabAsset",
    "m_GameObject",
    "m_Enabled",
    "m_EditorHideFlags",
    "m_Script",
    "m_Name",
    "m_EditorClassIdentifier",
    "gameplayRaces",
    "NeedsConsumptionTime",
    "RewardColorRawGood",
    "RewardColorGoodPerMin",
    "RewardColorRawProduction",
    "RewardColorBuildingProduction",
    "RewardColorProfessionCapacity",
    "RewardColorVillagers",
    "RewardColorNewcomersRaceBonus",
    "RewardColorBuildings",
    "RewardColorPositiveResolveEffect",
    "RewardColorWorkplacePerk",
    "RewardColorNeedPerk",
    "RewardColorNegativeResolveEffect",
    "RewardColorPositiveReputation",
    "RewardColorReputationPenalty",
    "RewardColorPauseBlock",
    "RewardColorProductionSpeed",
    "RewardColorFuelRate",
    "RewardColorVillagerSpeed",
    "RewardColorNewYearEffectMultiplayer",
    "RewardColorBuildingsStorageCapacity",
    "RewardsColorGrassAmount",
    "RewardColorSeasonLength",
    "RewardColorComposite",
    "RewardColorGladeInfo",
    "RewardColorRecipe",
    "RewardColorCloning",
    "RewardColorExplosion",
    "RewardColorMerchantsReproach",
    "RewardColorVillagersDeath",
    "RewardColorReplaceBuilding",
    "RewardColorDepositsCharges",
    "RewardColorResolveToReputationRate",
    "RewardColorCommonPositive",
    "RewardColorCommonNegative",
    "DepositGladeColor",
    "SpringGladeColor",
    "OreGladeColor",
    "RewardGladeColor",
    "ThreatGladeColor",
    "DangerousThreatGladeColor",
    "GladesIndicatorHidingSpeed",
    "RefundRemovedConstruction",
    "RefundRemovedBuilding",
    "tradesRoutesPaymentInterval",
    "maxProductionLimit",
    "timeUntilGoodAutoDelivery",
    "DefaultProfession",
    "landPatches",
    "defaultBiome",
    "capitalBiome",
    "wikiCategories",
    "wikiTopics",
    "marketingNews",
    "twitchFactions",
    "topics",
    "cornerstonesViewConfigurations",
    "backButtonCooldown",
    "autoSaveInterval",
    "simpleSeasonEffectsLabel",
    "conditionalSeasonEffectsLabel",
    "seasonEffectsTopic",
    "menuSkins",
    "perksConfig",
    "uiConfig",
    "tooltipsConfig",
    "tutorialsConfig",
    "ordersConfig",
    "goalsConfig",
    "monitorsConfig",
    "metaConfig",
    "ironmanMetaConfig",
    "embarkConfig",
    "worldConfig",
    "resolveConfig",
    "challengeConfig",
    "analyticsConfig",
    "needsConfig",
    "votingConfig",
    "tipsConfig",
    "newsConfig",
    "locaConfig",
    "savesSupportConfig",
    "conditionsConfig",
    "platformsConfig",
    "pluginsConfig",
    "altarConfig",
    "tradeRoutesConfig",
    "fuelRodsConfig",
    "hubsConfig",
    "blightConfig",
    "seasonalEffectsGlobalConfig",
    "customGameConfig",
    "rainpunkConfig",
    "logisticConfig",
    "twitchConfig",
    "gamesHistoryConfig",
    "sealsGameplayConfig",
    "ironmanConfig",
    "demoConfig",
    "storageOperationsConfig",
    "creditsConfig",
    "actorsBehavioursConfig",
    "dlcsConfig",
    "clientPrefsConfig",
]

GUID_PATTERN = re.compile(r"([0-9a-f]{32})")

TESTING_ITERATION_LIMIT = 1



def register_guid(guid: str, domain: str, registry: dict, verbose: bool):
    """Registers a guid under the specified domain."""
    if guid not in registry[META_KEY_INDEX]:
        registry[META_KEY_INDEX][guid] = [ domain ]
    else:
        if domain not in registry[META_KEY_INDEX][guid]:
            registry[META_KEY_INDEX][guid].append(domain)
    if verbose:
        stdout.write(f"...indexed {guid} under domain {domain}\n")

def register_domain(domain_tree: dict|list|str, domain: str, registry: dict, verbose: bool):
    """Registers a new domain. This stays at the top or second levels of the asset data."""
    if domain not in registry[META_KEY_DOMAIN_LIST]:
        registry[META_KEY_DOMAIN_LIST].append(domain)
        if verbose:
            stdout.write(f"...added new {domain} to registry domain list\n")
    if isinstance(domain_tree, dict):
        for _, value in domain_tree.items():
            if isinstance(value, str) and GUID_PATTERN.fullmatch(value):
                register_guid(value, domain, registry, verbose)
    elif isinstance(domain_tree, list):
        for item in domain_tree:
            if isinstance(item, str) and GUID_PATTERN.fullmatch(item):
                register_guid(item, domain, registry, verbose)
    elif isinstance(domain_tree, str) and GUID_PATTERN.fullmatch(domain_tree):
        register_guid(domain_tree, domain, registry, verbose)



def build_registry_from_asset(registry_asset_path: Path, registry: dict, verbose: bool) -> dict:
    """Builds a new model registry from one asset file."""
    asset_data = parse_yaml(registry_asset_path, verbose)
    for domain_key, raw_value in asset_data.items():
        if domain_key in REGISTRY_FIELDS_TO_EXCLUDE:
            if verbose:
                stdout.write(f"...dropped field {domain_key}\n")
            continue
        normalized_domain_tree = normalize_asset_tree(raw_value, verbose)
        register_domain(normalized_domain_tree, domain_key, registry, verbose)
        registry[MODEL_KEY][domain_key] = normalized_domain_tree
    return registry



def build_model_registry(registry_assets_paths: list, verbose: bool = False, testing: bool = False) -> dict:
    """Builds a new model registry from the provided files."""
    registry = {}
    registry[META_KEY_DOMAIN_LIST] = []
    registry[META_KEY_INDEX] = {}
    registry[MODEL_KEY] = {}
    asset_number = 0
    if verbose:
        stdout.write(f"Building model registry from {len(registry_assets_paths)} assets...\n")
    for registry_asset_path in registry_assets_paths:
        asset_number += 1
        if testing and asset_number > TESTING_ITERATION_LIMIT:
            break
        build_registry_from_asset(registry_asset_path, registry, verbose)
    stdout.write(f"...finished building model registry from {asset_number} assets.\n")
    return registry



if __name__ == "__main__":
    registry_asset_paths = [
        ROOT_PATH / "Assets" / "MonoBehaviour" / "Settings.asset",
    ]
    stdout.write("Building model registry...\n")
    model_registry = build_model_registry(registry_asset_paths, verbose=True, testing=True)
    with open(WRITE_MODEL_REGISTRY_PATH, "w", encoding="utf-8") as model_registry_file:
        json.dump(model_registry, model_registry_file, indent=4)
    stdout.write("...done.\n")
