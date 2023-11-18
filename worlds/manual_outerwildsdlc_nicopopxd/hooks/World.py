# Object classes from AP core, to represent an entire MultiWorld and this individual World that's part of it
import random
from worlds.AutoWorld import World
from BaseClasses import MultiWorld
import json
import os
import pkgutil

# Object classes from Manual -- extending AP core -- representing items and locations that are used in generation
from ..Items import ManualItem
from ..Locations import ManualLocation

# Raw JSON data from the Manual apworld, respectively:
#          data/game.json, data/items.json, data/locations.json, data/regions.json
#
from ..Data import game_table, item_table, location_table, region_table
from ..Game import game_name
from .Options import RandomContent
# These helper methods allow you to determine if an option has been set, or what its value is, for any player in the multiworld
from ..Helpers import is_option_enabled, get_option_value



########################################################################################
## Order of method calls when the world generates:
##    1. create_regions - Creates regions and locations
##    2. set_rules - Creates rules for accessing regions and locations
##    3. generate_basic - Creates the item pool and runs any place_item options
##    4. pre_fill - Creates the victory location
##
## The create_item method is used by plando and start_inventory settings to create an item from an item name.
## The fill_slot_data method will be used to send data to the Manual client for later use, like deathlink.
########################################################################################



# Called before regions and locations are created. Not clear why you'd want this, but it's here.
def before_create_regions(world: World, multiworld: MultiWorld, player: int):
    if 'version' in game_table:
        apworldversion = game_table['version']
    if apworldversion != "":
            print(f"Includes {game_name} version: {apworldversion}")
    pass

# Called after regions and locations are created, in case you want to see or modify that information.
def after_create_regions(world: World, multiworld: MultiWorld, player: int):
    pass

# Called before rules for accessing regions and locations are created. Not clear why you'd want this, but it's here.
def before_set_rules(world: World, multiworld: MultiWorld, player: int):
    randomContent = get_option_value(multiworld, player, "randomized_content") or 0
    solanum = get_option_value(multiworld, player, "require_solanum") or False
    owlguy = get_option_value(multiworld, player, "require_prisoner") or False
    if randomContent == RandomContent.option_base_game:
        owlguy = False
    elif randomContent == RandomContent.option_dlc:
        solanum = False

    if not (solanum or owlguy or randomContent != RandomContent.option_both):
        return
    TotalToAdd = 7
    if solanum: TotalToAdd += 1
    if owlguy: TotalToAdd += 1
    victory_location = next(loc for loc in world.location_table if loc["name"] == "FINAL > Get the warp drive to the vessel and Warp to the Eye")
    victory_location["requires"] = f"|@1 Need For End:{TotalToAdd}| and |@4a Knowledge:4|"
    print(f'Changed the player {game_name}:{player} Victory rules to "|@1 Need For End:{TotalToAdd}| and |@4a Knowledge:4|"')
    # THX Axxroy

# Called after rules for accessing regions and locations are created, in case you want to see or modify that information.
def after_set_rules(world: World, multiworld: MultiWorld, player: int):
    pass

# The complete item pool prior to being set for generation is provided here, in case you want to make changes to it
def before_generate_basic(item_pool: list, world: World, multiworld: MultiWorld, player: int):
    solanum = get_option_value(multiworld, player, "require_solanum") or False
    owlguy = get_option_value(multiworld, player, "require_prisoner") or False
    randomContent = get_option_value(multiworld, player, "randomized_content") or 0

    if randomContent != RandomContent.option_both:
        fname = os.path.join("..", "data", "dlc.json")
        dlc_data = json.loads(pkgutil.get_data(__name__, fname).decode())
        if randomContent == RandomContent.option_base_game:
            owlguy = False
            print("Only base game")
            for item in list(item_pool):
                if item.name in dlc_data["echoes"]["items"]:
                    item_pool.remove(item)
                
            for region in multiworld.regions:
                if region.player != player:
                    continue
                for location in list(region.locations):
                    if location.name in dlc_data["echoes"]["locations"]:
                        world.location_name_to_location[location.name].pop("place_item", "")
                        world.location_name_to_location[location.name].pop("place_item_category", "")
                        region.locations.remove(location)
            multiworld.clear_location_cache()
            #Do stuff
        if randomContent == RandomContent.option_dlc:
            solanum = False
            world.location_name_to_location["94 - Communicate with the prisoner in the Subterranean Lake Dream"]['place_item'] = ["Victory"]
            print("Only DLC")
            valid_items = dlc_data["echoes"]["items"] + dlc_data["both"]["items"]
            valid_locations = dlc_data["echoes"]["locations"] + dlc_data["both"]["locations"]
            for item in list(item_pool):
                if item.name not in valid_items:
                    item_pool.remove(item)
            
            for region in multiworld.regions:
                if region.player != player:
                    continue
                for location in list(region.locations):
                    if location.name not in valid_locations:
                        world.location_name_to_location[location.name].pop("place_item", "")
                        world.location_name_to_location[location.name].pop("place_item_category", "")
                        region.locations.remove(location)
            multiworld.clear_location_cache()
            

    if not (solanum or owlguy):
        return item_pool
    if solanum: world.item_name_to_item["Seen Solanum"]["category"].append("1 Need For End")
    if owlguy: world.item_name_to_item["Seen Prisoner"]["category"].append("1 Need For End")
    
#
    ## if total_characters < 10 or total_characters > 50:
    ##     total_characters = 50
#
    ## # shuffle the character item names and pull a subset with a maximum for the option we provided
    ## character_names = [name for name in world.item_names]
    ## random.shuffle(character_names)
    ## character_names = character_names[0:total_characters]
#
    ## # remove any items that have been added that don't have those item names
    ## item_pool = [item for item in item_pool if item.name in character_names]
    #
    ## # remove any locations that have been added that aren't for those items
    ## world.location_id_to_name = {id: name for (id, name) in world.location_id_to_name.items() if name.replace("Beat the Game - ", "") in character_names}
    ## world.location_name_to_id = {name: id for (id, name) in world.location_id_to_name.items()}
    ## world.location_names = world.location_name_to_id.keys()
#
    ## # remove the locations above from the multiworld as well
    ## multiworld.clear_location_cache()
    #
    ## for region in multiworld.regions:
    ##     locations_to_remove_from_region = []
#
    ##     for location in region.locations:
    ##         if location.name.replace("Beat the Game - ", "") not in character_names and location.player == player:
    ##             locations_to_remove_from_region.append(location)
#
    ##     for location in locations_to_remove_from_region:
    ## #         region.locations.remove(location)
    #
    ## # modify the victory requirements to only include items that are in the item names list
    ## victory_location = multiworld.get_location("__Manual Game Complete__", player)
    ## victory_location.access_rule = lambda state, items=character_names, p=player: state.has_all(items, p)

    return item_pool

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

# This is called before slot data is set and provides an empty dict ({}), in case you want to modify it before Manual does
def before_fill_slot_data(slot_data: dict, world: World, multiworld: MultiWorld, player: int) -> dict:
    return slot_data

# This is called after slot data is set and provides the slot data at the time, in case you want to check and modify it after Manual is done with it
def after_fill_slot_data(slot_data: dict, world: World, multiworld: MultiWorld, player: int) -> dict:
    if 'version' in game_table:
        version = game_table["version"]
        if version != "":
            multiworld.game_version[player].value = version
        else:
            multiworld.game_version[player].value = "Unknown"
    else:
        multiworld.game_version[player].value = "Unknown"
    print(f"Game version set to: {multiworld.game_version[player].value}")
    return slot_data