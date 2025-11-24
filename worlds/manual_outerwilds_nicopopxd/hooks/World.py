# Object classes from AP core, to represent an entire MultiWorld and this individual World that's part of it
from worlds.AutoWorld import World
from worlds.generic.Rules import add_rule
from ..Data import load_data_file
from copy import copy

from BaseClasses import MultiWorld, CollectionState
import logging

# Object classes from Manual -- extending AP core -- representing items and locations that are used in generation
from ..Items import ManualItem
from ..Locations import ManualLocation
from .Helpers import InitCategories

# Raw JSON data from the Manual apworld, respectively:
#          data/game.json, data/items.json, data/locations.json, data/regions.json
#
from ..Data import game_table, item_table, location_table, region_table
from .Options import EarlyShipKey, RandomContent, Goal

# These helper methods allow you to determine if an option has been set, or what its value is, for any player in the multiworld
from ..Helpers import is_option_enabled, is_item_enabled, get_option_value

logger = logging.getLogger()
APMiscData = {}
"""Miscellaneous shared data"""
APMiscData["KnownPlayers"] = []
APWorkingData = {}
"""
Copy of any changed world item/locations
"""
########################################################################################
## Order of method calls when the world generates:
##    1. create_regions - Creates regions and locations
##    2. create_items - Creates the item pool
##    3. set_rules - Creates rules for accessing regions and locations
##    4. generate_basic - Runs any post item pool options, like place item/category
##    5. pre_fill - Creates the victory location
##
## The create_item method is used by plando and start_inventory settings to create an item from an item name.
## The fill_slot_data method will be used to send data to the Manual client for later use, like deathlink.
########################################################################################



# Called before regions and locations are created. Not clear why you'd want this, but it's here. Victory location is included, but Victory event is not placed yet.
def before_create_regions(world: World, multiworld: MultiWorld, player: int):
    if hasattr(world, 'options'):
        world.hasOptionsManager = True
    else:
        raise Exception("Sorry I no longer support AP before the Options Manager")
    # Set version in yaml and log
    if not APMiscData.get('version'):
        APMiscData['version'] = "Unknown"
        APMiscData['043Compatible'] = False

        if 'version' in game_table:
            APMiscData['version'] = game_table['version']

        if hasattr(multiworld, 'clear_location_cache') and callable(multiworld.clear_location_cache):
            APMiscData['043Compatible'] = True

        logger.info(f"player(s) uses {world.game} version: {APMiscData['version']}")

    world.options.game_version.value = APMiscData["version"]
#Init Options
#region
    APMiscData["KnownPlayers"].append(player)
    APMiscData[player] = {}
    goal = world.options.goal
    randomcontent = world.options.randomized_content.value
    #Options Check for impossibilities
    if randomcontent == RandomContent.option_both:
        if goal == Goal.option_standard: goal.value = Goal.option_eye #Dynamic Goal

    elif randomcontent == RandomContent.option_base_game:
        world.options.require_prisoner.value = 0
        if goal == Goal.option_standard: goal.value = Goal.option_eye #Dynamic Goal
        elif (goal == Goal.option_prisoner or goal == Goal.option_visit_all_archive or
            goal == Goal.option_stuck_in_stranger or goal == Goal.option_stuck_in_dream):
            goal.value = Goal.option_eye
            logger.warning(f"OW: Impossible goal for player '{multiworld.get_player_name(player)}'. Was changed to Default (Vanilla%)")
        world.options.enable_spooks.value = 1 #Set to True to skip some code later
        world.options.dlc_access_items.value = 0

    elif randomcontent == RandomContent.option_dlc:
        if goal == Goal.option_standard: goal.value = Goal.option_prisoner #Dynamic Goal

    InitCategories(multiworld, player)
#endregion

# Called after regions and locations are created, in case you want to see or modify that information.
def after_create_regions(world: World, multiworld: MultiWorld, player: int):
    solanum = world.options.require_solanum.value
    owlguy = world.options.require_prisoner.value
    randomContent = world.options.randomized_content.value
    goal = world.options.goal.value

# Removing items/locations
#region
    locations_to_be_removed = []

    # Selecting what content to remove
    #region
    if not APWorkingData.get('items_to_be_removed'):
        APWorkingData["items_to_be_removed"] = {}
    APWorkingData['items_to_be_removed'][player] = []
    if randomContent != RandomContent.option_both:
        if randomContent == RandomContent.option_base_game:
            message = "Base game"
        elif randomContent == RandomContent.option_dlc:
            message = "DLC"
            if goal == Goal.option_eye:
                message += " + Eye"
            elif goal == Goal.option_ash_twin_project_break_spacetime:
                message += " + Ash Twin project"
            elif goal == Goal.option_high_energy_lab_break_spacetime:
                message += " + High Energy Lab"
            elif goal == Goal.option_stuck_in_stranger or goal == Goal.option_stuck_in_dream:
                message += " + Adv. warp core"
            elif goal == Goal.option_stuck_with_solanum:
                message += " + Adv. warp core + Solanum"
            if solanum and goal != Goal.option_stuck_with_solanum:
                message += " + Solanum"

    else:
        message = "Both"
    #logger.info(message)
    APMiscData[player]['contentmsg'] = message

    if goal == Goal.option_ash_twin_project_break_spacetime:
        locations_to_be_removed.append('1 - Break Space-Time in the Ash Twin Project')

    elif goal == Goal.option_high_energy_lab_break_spacetime:
        locations_to_be_removed.append('1 - Break space time in the lab')

    elif goal == Goal.option_visit_all_archive:
        locations_to_be_removed.append('9 - In a loop visit all 3 archive without getting caught')

    elif goal == Goal.option_prisoner:

        locations_to_be_removed.append('94 - Enter the Sealed Vault in the Subterranean Lake Dream')

    #endregion

    #Removing Locations
    #region

    if len(locations_to_be_removed) > 0:
        for region in multiworld.regions:
            if region.player != player:
                continue
            for location in list(region.locations):
                if location.name in locations_to_be_removed:
                    region.locations.remove(location)
        if APMiscData['043Compatible']:
            multiworld.clear_location_cache()

    #endregion
#endregion
    pass

# The item pool before starting items are processed, in case you want to see the raw item pool at that stage
def before_create_items_starting(item_pool: list, world: World, multiworld: MultiWorld, player: int) -> list:
    return item_pool

# The item pool after starting items are processed but before filler is added, in case you want to see the raw item pool at that stage
def before_create_items_filler(item_pool: list, world: World, multiworld: MultiWorld, player: int) -> list:
    solanum = world.options.require_solanum
    owlguy = world.options.require_prisoner
    do_place_item_category = world.options.do_place_item_category
    randomContent = world.options.randomized_content
    goal = world.options.goal
    do_spooks = world.options.enable_spooks
    DlcMainItemsRequired = world.options.dlc_access_items
    StartItems = {}
# SuitShuffle
    if not world.options.shuffle_spacesuit.value:
        StartItems["SpaceSuit"] = 1

# Reverse Teleporters:
    if world.options.reverse_teleporters.value:
        multiworld.push_precollected(world.create_item("Reverse Teleporters"))

# Ship Key logic
# region
    # option_local_early = 0 default in items.json
    # option_local_anywhere = 1
    # option_global_early = 2
    # option_global_anywhere = 3
    # option_startswith = 4 default option value
    early_Ship = world.options.ship_key_logic.value
    shipitem = "Ship Key"
    if early_Ship == EarlyShipKey.option_startswith:
        world.options.local_items.value.discard(shipitem)
        multiworld.early_items[player].pop(shipitem, "")
        StartItems[shipitem] = 1
    elif early_Ship == EarlyShipKey.option_local_early:
        pass
    elif early_Ship == EarlyShipKey.option_local_anywhere:
        multiworld.early_items[player].pop(shipitem, "")
    elif early_Ship == EarlyShipKey.option_global_early:
        world.options.local_items.value.discard(shipitem)
    elif early_Ship == EarlyShipKey.option_global_anywhere:
        world.options.local_items.value.discard(shipitem)
        multiworld.early_items[player].pop(shipitem, "")


#endregion
# Early Launch Codes
#region
    if world.options.remove_launch_codes.value:
        StartItems["Launch Codes"] = 1
#endregion
# Loop item and apply as requested
    for item in item_pool:
        if item.player != player:
            continue
        if item.name in StartItems.keys() and world.start_inventory.get(item.name, 0) < StartItems[item.name]:
            multiworld.push_precollected(item)
            item_pool.remove(item),
            world.start_inventory[item.name] = world.start_inventory.get(item.name, 0) + 1


# Personal Item counts adjustment
#region
    location_count = len(multiworld.get_unfilled_locations(player)) - 1
    item_counts= {}
    if randomContent == RandomContent.option_base_game:
        item_counts["Forced Meditation"] = 2
        item_counts["Musical Instrument"] = 5
        item_counts["Ticket for (1) free death"] = 4

    elif randomContent == RandomContent.option_dlc:
        item_counts["Forced Meditation"] = 3
        item_counts["Ticket for (1) free death"] = 5

    else:
        pass
    #if randomContent == RandomContent.option_base_game or randomContent == RandomContent.option_dlc:
        #if either only base game or only dlc
        #world.item_name_to_item["Ticket for (1) free death"]["count"] = 10

    for item in APWorkingData['items_to_be_removed'][player]:
        item_counts[item] = 0

    for name, count in item_counts.items():
        items = []
        for item in item_pool:
            if item.player != player:
                continue
            if item.name == name:
                items.append(item)
        if len(items) > count:
            for x in range(len(items) - count):
                item_pool.remove(items[x])
#endregion
#Placing Victory item in location
#region
    VictoryInfoToAdd = ""
    if solanum: VictoryInfoToAdd += " + 'Seen Solanum'"
    if owlguy: VictoryInfoToAdd += " + 'Seen Prisoner'"

    if goal == Goal.option_eye or (goal == Goal.option_standard and ( randomContent == RandomContent.option_both or randomContent == RandomContent.option_base_game)):
        victory_base_message = "Eye"
    elif goal == Goal.option_prisoner or (goal == Goal.option_standard and randomContent == RandomContent.option_dlc):
        victory_base_message = "Prisoner"
    elif goal == Goal.option_visit_all_archive:
        victory_base_message = "Visit all archive"
    elif goal == Goal.option_ash_twin_project_break_spacetime:
        victory_base_message = "Ash Twin Project"
    elif goal == Goal.option_high_energy_lab_break_spacetime:
        victory_base_message = "High Energy Lab"
    elif goal == Goal.option_stuck_with_solanum:
        victory_base_message = "Stuck with Solanum"
    elif goal == Goal.option_stuck_in_stranger:
        victory_base_message = "Stuck in Stranger"
    elif goal == Goal.option_stuck_in_dream:
        victory_base_message = "Stuck in Dreamworld"
    victory_message = victory_base_message + VictoryInfoToAdd

    contentmsg = APMiscData[player]['contentmsg']
    logger.info(f"{world.game}:{multiworld.get_player_name(player)} ({player}):({contentmsg}) {len(item_pool)} items | {location_count} locations")
    logger.info(f'Set Victory rules to {victory_message}')
#endregion

    if len(APWorkingData.get('RM_place_item_cat', ["tomato"])) == 0:
        APWorkingData.pop("RM_place_item_cat", "")
    if len(APWorkingData.get('RM_place_item', ["tomato"])) == 0:
        APWorkingData.pop("RM_place_item", "")
    return item_pool

# The complete item pool prior to being set for generation is provided here, in case you want to make changes to it
def after_create_items(item_pool: list, world: World, multiworld: MultiWorld, player: int) -> list:
    return item_pool

# Called before rules for accessing regions and locations are created. Not clear why you'd want this, but it's here.
def before_set_rules(world: World, multiworld: MultiWorld, player: int):
    pass

# Called after rules for accessing regions and locations are created, in case you want to see or modify that information.
def after_set_rules(world: World, multiworld: MultiWorld, player: int):
    #extra_data = load_data_file("extra.json")
    solanum = world.options.require_solanum.value
    owlguy = world.options.require_prisoner.value
    randomContent = world.options.randomized_content.value
    goal = world.options.goal.value

#Victory Location access rules mod
#region

    if goal == Goal.option_eye or (goal == Goal.option_standard and ( randomContent == RandomContent.option_both or randomContent == RandomContent.option_base_game)):
        victory_name = "Any%"
    elif goal == Goal.option_prisoner or (goal == Goal.option_standard and randomContent == RandomContent.option_dlc):
        victory_name = "Prisoner%"
    elif goal == Goal.option_visit_all_archive:
        victory_name = "Ghosts_In_The_Machine%"
    elif goal == Goal.option_ash_twin_project_break_spacetime:
        victory_name = "Break_Space-Time_In_ATP%"
    elif goal == Goal.option_high_energy_lab_break_spacetime:
        victory_name = "Break_Space-Time_In_Lab%"
    elif goal == Goal.option_stuck_with_solanum:
        victory_name = "Quantum_Stuck%"
    elif goal == Goal.option_stuck_in_stranger:
        victory_name = "Stranger_Stuck%"
    elif goal == Goal.option_stuck_in_dream:
        victory_name = "Dream_Stuck%"

    for location in multiworld.get_locations(player):
        if location.name == victory_name:
            if solanum:
                add_rule(location,
                         lambda state: state.has("[Event] 6 - Explore the Sixth Location", player))
            if owlguy and goal != Goal.option_prisoner:
                add_rule(location,
                         lambda state: state.has("[Event] 94 - Enter the Sealed Vault in the Subterranean Lake Dream", player))
#endregion
# The complete item pool prior to being set for generation is provided here, in case you want to make changes to it
    pass

# This method is run at the very end of pre-generation, once the place_item options have been handled and before AP generation occurs
def after_generate_basic(world: World, multiworld: MultiWorld, player: int):
    pass

# This method is called before the victory location has the victory event placed and locked
def before_pre_fill(world: World, multiworld: MultiWorld, player: int):
    pass

# This method is called after the victory location has the victory event placed and locked
def after_pre_fill(world: World, multiworld: MultiWorld, player: int):
    pass

# The item name to create is provided before the item is created, in case you want to make changes to it
def before_create_item(item_name: str, world: World, multiworld: MultiWorld, player: int) -> str:
    return item_name

# The item that was created is provided after creation, in case you want to modify the item
def after_create_item(item: ManualItem, world: World, multiworld: MultiWorld, player: int) -> ManualItem:
    return item

# This method is run towards the end of pre-generation, before the place_item options have been handled and before AP generation occurs
def before_generate_basic(world: World, multiworld: MultiWorld, player: int) -> list:
    pass

# This method is run at the very end of pre-generation, once the place_item options have been handled and before AP generation occurs
def after_generate_basic(world: World, multiworld: MultiWorld, player: int):
    pass

# This is called before slot data is set and provides an empty dict ({}), in case you want to modify it before Manual does
def before_fill_slot_data(slot_data: dict, world: World, multiworld: MultiWorld, player: int) -> dict:
    return slot_data

# This is called after slot data is set and provides the slot data at the time, in case you want to check and modify it after Manual is done with it
def after_fill_slot_data(slot_data: dict, world: World, multiworld: MultiWorld, player: int) -> dict:
    # slot_data["item_counts"] = world.item_counts[player]
    return slot_data

# This is called right at the end, in case you want to write stuff to the spoiler log
def before_write_spoiler(world: World, multiworld: MultiWorld, spoiler_handle) -> None:
    #spoiler_handle.write(f"\nIncluded in this Async: {world.game} version {APMiscData['version']}")
    pass
