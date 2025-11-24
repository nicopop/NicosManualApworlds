from BaseClasses import Tutorial
from worlds.AutoWorld import World, WebWorld
_game_table = {}

# called after the game.json file has been loaded
def after_load_game_file(game_table: dict) -> dict:
    global _game_table
    _game_table = game_table
    return game_table

# called after the items.json file has been loaded, before any item loading or processing has occurred
# if you need access to the items after processing to add ids, etc., you should use the hooks in World.py
def after_load_item_file(item_table: list) -> list:
    return item_table

# NOTE: Progressive items are not currently supported in Manual. Once they are,
#       this hook will provide the ability to meaningfully change those.
def after_load_progressive_item_file(progressive_item_table: list) -> list:
    return progressive_item_table

# called after the locations.json file has been loaded, before any location loading or processing has occurred
# if you need access to the locations after processing to add ids, etc., you should use the hooks in World.py
def after_load_location_file(location_table: list) -> list:
    return location_table

# called after the locations.json file has been loaded, before any location loading or processing has occurred
# if you need access to the locations after processing to add ids, etc., you should use the hooks in World.py
def after_load_region_file(region_table: dict) -> dict:
    return region_table

# called after the categories.json file has been loaded
def after_load_category_file(category_table: dict) -> dict:
    return category_table

# called after the meta.json file has been loaded and just before the properties of the apworld are defined. You can use this hook to change what is displayed on the webhost
# for more info check https://github.com/ArchipelagoMW/Archipelago/blob/main/docs/world%20api.md#webworld-class
def after_load_meta_file(meta_table: dict) -> dict:
    if not meta_table.get("docs"):
        meta_table['docs'] = {}
    if not meta_table['docs'].get("web"):
        meta_table['docs']['web'] = {}

    meta_table["docs"]["apworld_description"] = f"""
    Manual games allow you to set custom check locations and custom item names that will be rolled into a multiworld.
    In this case a game from 2019: OuterWilds
    the player must manually refrain from using these gathered items until the tracker shows that they have been acquired or sent.
    [Apworld Version: {_game_table.get('version', 'Unknown')}]
    """
    web = meta_table['docs']['web']
    web['options_presets'] = {
        "Short":{
            "require_solanum": False,
            "require_prisoner": False,
            "do_place_item_category": True,
            "randomized_content": "both",
            "goal": "standard"
            },
        "Long":{
            "require_solanum": True,
            "require_prisoner": True,
            "do_place_item_category": True,
            "randomized_content": "both",
            "goal": "standard"
            },
        "Short (BaseGame)":{
            "require_solanum": False,
            "require_prisoner": False,
            "do_place_item_category": True,
            "randomized_content": "base_game",
            "goal": "standard"
            },
        "Long (BaseGame)":{
            "require_solanum": True,
            "require_prisoner": False,
            "do_place_item_category": True,
            "randomized_content": "base_game",
            "goal": "standard"
            }
        }
    web['theme'] = "ocean"
    web['bug_report_page'] = "https://discord.com/channels/1097532591650910289/1101289500602286161"

    return meta_table

# called when an external tool (eg Universal Tracker) ask for slot data to be read
# use this if you want to restore more data
# return True if you want to trigger a regeneration if you changed anything
def hook_interpret_slot_data(world, player: int, slot_data: dict[str, any]) -> bool:
    return False
