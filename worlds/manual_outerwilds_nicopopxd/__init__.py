from base64 import b64encode
import os
import logging
import json
from typing import Callable, Optional

from worlds.generic.Rules import forbid_items_for_player
from worlds.LauncherComponents import Component, SuffixIdentifier, components, Type, launch_subprocess

from .Data import item_table, progressive_item_table, location_table, region_table, category_table
from .Game import game_name, filler_item_name, starting_items
from .Locations import location_id_to_name, location_name_to_id, location_name_to_location, location_name_groups
from .Items import item_id_to_name, item_name_to_id, item_name_to_item, advancement_item_names, item_name_groups

from .Regions import create_regions
from .Items import ManualItem
from .Rules import set_rules
from .Options import manual_options
from .Helpers import is_option_enabled, is_item_enabled, get_option_value

from BaseClasses import ItemClassification, Tutorial, Item
from worlds.AutoWorld import World, WebWorld
from copy import copy

from .hooks.World import \
    before_pre_fill, after_pre_fill, \
    before_generate_basic, after_generate_basic, \
    before_create_item, after_create_item, \
    before_set_rules, after_set_rules, \
    before_create_regions, after_create_regions, \
    before_fill_slot_data, after_fill_slot_data

class ManualWeb(WebWorld):
    options_presets = {
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
    theme = "ocean"
    tutorials = [Tutorial(
        "Multiworld Setup Guide",
        "A guide to setting up manual game integration for Archipelago multiworld games.",
        "English",
        "setup_en.md",
        "setup/en",
        ["Nicopopxd"]
    )]
    bug_report_page = "https://discord.com/channels/1097532591650910289/1101289500602286161"


class ManualWorld(World):
    """
    Manual games allow you to set custom check locations and custom item names that will be rolled into a multiworld.
    In this case a game from 2019: OuterWilds
    the player must manually refrain from using these gathered items until the tracker shows that they have been acquired or sent.
    """
    game: str = game_name
    web = ManualWeb()

    option_definitions = manual_options
    data_version = 2
    required_client_version = (0, 3, 4)

    # These properties are set from the imports of the same name above.
    item_table = item_table
    category_table = category_table
    progressive_item_table = progressive_item_table
    item_id_to_name = item_id_to_name
    item_name_to_id = item_name_to_id
    item_name_to_item = item_name_to_item
    item_name_groups = item_name_groups
    item_counts = {}

    advancement_item_names = advancement_item_names
    location_table = location_table # this is likely imported from Data instead of Locations because the Game Complete location should not be in here, but is used for lookups
    location_id_to_name = location_id_to_name
    location_name_to_id = location_name_to_id
    location_name_to_location = location_name_to_location
    location_name_groups = location_name_groups

    def interpret_slot_data(self, slot_data: dict[str, any]):
        #this is called by UT before rules are called
        self.item_counts[self.player] = slot_data['item_counts']

    def pre_fill(self):
        before_pre_fill(self, self.multiworld, self.player)

        location_game_complete = self.multiworld.get_location("__Manual Game Complete__", self.player)
        location_game_complete.address = None

        location_game_complete.place_locked_item(
            ManualItem("__Victory__", ItemClassification.progression, None, player=self.player))

        after_pre_fill(self, self.multiworld, self.player)

    def generate_basic(self):
        logger = logging.getLogger()
        # Generate item pool
        pool = []
        traps = []
        configured_item_names = self.item_id_to_name.copy()

        for name in configured_item_names.values():
            if name == "__Victory__":
                continue

            # If it's the filler item, skip it until we know if we need any extra items
            if name == filler_item_name:
                continue

            # if (hasattr(self.multiworld, "progressive_items") and len(self.multiworld.progressive_items) > 0):
            #     shouldUseProgressive = (self.multiworld.progressive_items[self.player].value);

            #     if shouldUseProgressive and name in self.progressive_item_table:
            #         name = self.progressive_item_table[name]

            item = self.item_name_to_item[name]
            item_count = 1

            if item.get("trap"):
                traps.append(name)

            if "count" in item:
                item_count = int(item["count"])

            if "category" in item:
                if not is_item_enabled(self.multiworld, self.player, item):
                    item_count = 0

            if item_count == 0:
                continue

            for i in range(item_count):
                new_item = self.create_item(name)
                pool.append(new_item)

            if item.get("early") and item.get("local"):
              # both
                self.multiworld.local_early_items[self.player][name] = item_count

            elif item.get("early"):
                # only early
                self.multiworld.early_items[self.player][name] = item_count

            elif item.get("local"):
              # only local
                if name not in self.multiworld.local_items[self.player].value:
                    self.multiworld.local_items[self.player].value.add(name)

        items_started = []

        if starting_items:
            for starting_item_block in starting_items:
                # if there's a condition on having a previous item, check for any of them
                # if not found in items started, this starting item rule shouldn't execute, and check the next one
                if "if_previous_item" in starting_item_block:
                    matching_items = [item for item in items_started if item.name in starting_item_block["if_previous_item"]]

                    if len(matching_items) == 0:
                        continue

                # start with the full pool of items
                items = pool

                # if the setting lists specific item names, limit the items to just those
                if "items" in starting_item_block:
                    items = [item for item in pool if item.name in starting_item_block["items"]]

                # if the setting lists specific item categories, limit the items to ones that have any of those categories
                if "item_categories" in starting_item_block:
                    items_in_categories = [item["name"] for item in self.item_name_to_item.values() if "category" in item and len(set(starting_item_block["item_categories"]).intersection(item["category"])) > 0]
                    items = [item for item in pool if item.name in items_in_categories]

                self.random.shuffle(items)

                # if the setting lists a specific number of random items that should be pulled, only use a subset equal to that number
                if "random" in starting_item_block:
                    items = items[0:starting_item_block["random"]]

                for starting_item in items:
                    items_started.append(starting_item)
                    self.multiworld.push_precollected(starting_item)
                    pool.remove(starting_item)

        pool = self.add_filler_items(pool, traps)

        pool = before_generate_basic(pool, self, self.multiworld, self.player)

        # need to put all of the items in the pool so we can have a full state for placement
        # then will remove specific item placements below from the overall pool
        self.multiworld.itempool += pool

        # Handle item forbidding
        manual_locations_with_forbid = {location['name']: location for location in location_name_to_location.values() if "dont_place_item" in location or "dont_place_item_category" in location}
        locations_with_forbid = [l for l in self.multiworld.get_unfilled_locations(player=self.player) if l.name in manual_locations_with_forbid.keys()]
        for location in locations_with_forbid:
            manual_location = manual_locations_with_forbid[location.name]
            forbidden_item_names = []

            if "dont_place_item" in manual_location:
                if len(manual_location["dont_place_item"]) == 0:
                    continue

                forbidden_item_names.extend([i["name"] for i in item_name_to_item.values() if i["name"] in manual_location["dont_place_item"]])

            if "dont_place_item_category" in manual_location:
                if len(manual_location["dont_place_item_category"]) == 0:
                    continue

                forbidden_item_names.extend([i["name"] for i in item_name_to_item.values() if "category" in i and set(i["category"]).intersection(manual_location["dont_place_item_category"])])

            if len(forbidden_item_names) > 0:
                forbid_items_for_player(location, forbidden_item_names, self.player)
                forbidden_item_names.clear()

        # Handle specific item placements using fill_restrictive
        manual_locations_with_placements = {location['name']: location for location in location_name_to_location.values() if "place_item" in location or "place_item_category" in location}
        locations_with_placements = [l for l in self.multiworld.get_unfilled_locations(player=self.player) if l.name in manual_locations_with_placements.keys()]
        for location in locations_with_placements:
            manual_location = manual_locations_with_placements[location.name]
            eligible_items = []

            if "place_item" in manual_location:
                if len(manual_location["place_item"]) == 0:
                    continue

                eligible_items = [item for item in self.multiworld.itempool if item.name in manual_location["place_item"] and item.player == self.player]

                if len(eligible_items) == 0:
                    raise Exception("Could not find a suitable item to place at %s. No items that match %s." % (manual_location["name"], ", ".join(manual_location["place_item"])))

            if "place_item_category" in manual_location:
                if len(manual_location["place_item_category"]) == 0:
                    continue

                eligible_item_names = [i["name"] for i in item_name_to_item.values() if "category" in i and set(i["category"]).intersection(manual_location["place_item_category"])]
                eligible_items = [item for item in self.multiworld.itempool if item.name in eligible_item_names and item.player == self.player]

                if len(eligible_items) == 0:
                    raise Exception("Could not find a suitable item to place at %s. No items that match categories %s." % (manual_location["name"], ", ".join(manual_location["place_item_category"])))

            if "dont_place_item" in manual_location:
                if len(manual_location["dont_place_item"]) == 0:
                    continue

                eligible_items = [item for item in eligible_items if item.name not in manual_location["dont_place_item"]]

                if len(eligible_items) == 0:
                    raise Exception("Could not find a suitable item to place at %s. No items that match placed_items(_category) because of forbidden %s." % (manual_location["name"], ", ".join(manual_location["dont_place_item"])))

            if "dont_place_item_category" in manual_location:
                if len(manual_location["dont_place_item_category"]) == 0:
                    continue

                forbidden_item_names = [i["name"] for i in item_name_to_item.values() if "category" in i and set(i["category"]).intersection(manual_location["dont_place_item_category"])]

                eligible_items = [item for item in eligible_items if item.name not in forbidden_item_names]

                if len(eligible_items) == 0:
                    raise Exception("Could not find a suitable item to place at %s. No items that match placed_items(_category) because of forbidden categories %s." % (manual_location["name"], ", ".join(manual_location["dont_place_item_category"])))
                forbidden_item_names.clear()


            # if we made it here and items is empty, then we encountered an unknown issue... but also can't do anything to place, so error
            if len(eligible_items) == 0:
                raise Exception("Custom item placement at location %s failed." % (manual_location["name"]))

            item_to_place = self.random.choice(eligible_items)
            location.place_locked_item(item_to_place)

            # remove the item we're about to place from the pool so it isn't placed twice
            self.multiworld.itempool.remove(item_to_place)

        # Generate item_counts here so it could be acessed in after_generate_basic
        if self.player not in self.item_counts:
            real_pool = self.multiworld.get_items()
            self.item_counts[self.player] = {i.name:real_pool.count(i) for i in real_pool if i.player == self.player}

        after_generate_basic(self, self.multiworld, self.player)
        # Uncomment these to generate a diagram of your manual.  Only works on 0.4.4+

        #from Utils import visualize_regions
        #visualize_regions(self.multiworld.get_region("Menu", self.player), f"{self.game}_{self.player}.puml")

    def create_item(self, name: str) -> Item:
        name = before_create_item(name, self, self.multiworld, self.player)

        item = self.item_name_to_item[name]
        classification = ItemClassification.filler

        if "trap" in item and item["trap"]:
            classification = ItemClassification.trap

        if "useful" in item and item["useful"]:
            classification = ItemClassification.useful

        if "progression" in item and item["progression"]:
            classification = ItemClassification.progression

        if "progression_skip_balancing" in item and item["progression_skip_balancing"]:
            classification = ItemClassification.progression_skip_balancing

        item_object = ManualItem(name, classification,
                        self.item_name_to_id[name], player=self.player)

        item_object = after_create_item(item_object, self, self.multiworld, self.player)

        return item_object

    def set_rules(self):
        before_set_rules(self, self.multiworld, self.player)

        set_rules(self, self.multiworld, self.player)

        after_set_rules(self, self.multiworld, self.player)

    def create_regions(self):
        before_create_regions(self, self.multiworld, self.player)

        create_regions(self, self.multiworld, self.player)

        after_create_regions(self, self.multiworld, self.player)

    def fill_slot_data(self):
        slot_data = before_fill_slot_data({}, self, self.multiworld, self.player)

        # slot_data["DeathLink"] = bool(self.multiworld.death_link[self.player].value)
        slot_data["item_counts"] = self.item_counts.get(self.player)

        slot_data = after_fill_slot_data(slot_data, self, self.multiworld, self.player)

        return slot_data

    def add_filler_items(self, item_pool, traps):
        extras = len(self.multiworld.get_unfilled_locations(player=self.player)) - len(item_pool) - 1 # subtracting 1 because of Victory; seems right

        if extras > 0:
            trap_percent = get_option_value(self.multiworld, self.player, "filler_traps")
            if not traps:
                trap_percent = 0

            trap_count = extras * trap_percent // 100
            filler_count = extras - trap_count

            for i in range(0, trap_count):
                extra_item = self.create_item(self.random.choice(traps))
                item_pool.append(extra_item)

            for i in range(0, filler_count):
                extra_item = self.create_item(filler_item_name)
                item_pool.append(extra_item)
        return item_pool

    def client_data(self):
        return {
            "game": self.game,
            'player_name': self.multiworld.get_player_name(self.player),
            'player_id': self.player,
            'items': self.item_name_to_item,
            'locations': self.location_name_to_location,
            # todo: extract connections out of mutliworld.get_regions() instead, in case hooks have modified the regions.
            'regions': region_table,
            'categories': category_table,

        }

    def generate_output(self, output_directory: str):
        data = self.client_data()
        filename = f"{self.multiworld.get_out_file_name_base(self.player)}.apmanual"
        with open(os.path.join(output_directory, filename), 'wb') as f:
            f.write(b64encode(bytes(json.dumps(data), 'utf-8')))


def launch_client(*args):
    from .ManualClient import launch as Main
    launch_subprocess(Main, name="Manual client")

class VersionedComponent(Component):
    def __init__(self, display_name: str, script_name: Optional[str] = None, func: Optional[Callable] = None, version: int = 0, file_identifier: Optional[Callable[[str], bool]] = None):
        super().__init__(display_name=display_name, script_name=script_name, func=func, component_type=Type.CLIENT, file_identifier=file_identifier)
        self.version = version

def add_client_to_launcher() -> None:
    version = 20240112 # YYYYMMDD
    found = False
    for c in components:
        if c.display_name == "Manual Client":
            found = True
            if getattr(c, "version", 0) < version:  # We have a newer version of the Manual Client than the one the last apworld added
                c.version = version
                c.func = launch_client
                return
    if not found:
        components.append(VersionedComponent("Manual Client", "ManualClient", func=launch_client, version=version, file_identifier=SuffixIdentifier('.apmanual')))

add_client_to_launcher()
