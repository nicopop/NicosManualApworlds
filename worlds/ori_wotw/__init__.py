"""AP world for Ori and the Will of the Wisps."""

# TODO Relics ? Black market ? Also make location groups for each area
# TODO fix player name with _
# TODO fix the in-game location counter


from typing import List, Dict
from collections import Counter

from .Rules import (set_moki_rules, set_gorlek_rules, set_gorlek_glitched_rules, set_kii_rules,
                    set_kii_glitched_rules, set_unsafe_rules, set_unsafe_glitched_rules)
from .Additional_Rules import combat_rules, glitch_rules, unreachable_rules
from .Items import item_table, group_table
from .Items_Icons import get_item_iconpath
from .Locations import loc_table
from .Quests import quest_table
from .LocationGroups import loc_sets
from .Events import event_table
from .Regions import region_table
from .Entrances import entrance_table
from .Refills import refill_events
from .Options import WotWOptions, option_groups, LogicDifficulty, Quests
from .Spawn_items import spawn_items, spawn_names
from .Presets import options_presets

from worlds.AutoWorld import World, WebWorld
from worlds.generic.Rules import add_rule, set_rule
from BaseClasses import Region, Location, Item, Tutorial, ItemClassification


class WotWWeb(WebWorld):
    theme = "ocean"  # TODO documentation
    tutorials = [Tutorial(
        "Multiworld Setup Guide",
        "A guide to setting up the Ori and the Will of the Wisps randomizer connected to an Archipelago Multiworld",
        "English",
        "setup_en.md",
        "setup/en",
        ["Satisha"]
    )]
    options_presets = options_presets
    option_groups = option_groups
    bug_report_page = "https://discord.com/channels/731205301247803413/1272952565843103765"


class WotWWorld(World):
    """Ori and the Will of the Wisps is a 2D Metroidvania;
    The sequel to Ori and the blind forest, a platform game emphasizing exploration, collecting items and upgrades, and backtracking to previously inaccessible areas.
    The player controls the titular Ori, a white guardian spirit.
    """
    game = "Ori and the Will of the Wisps"
    web = WotWWeb()

    item_name_to_id = {name: data[2] for name, data in item_table.items()}
    location_name_to_id = loc_table

    item_name_groups = group_table

    options_dataclass = WotWOptions
    options: WotWOptions
    explicit_indirect_conditions = False  # TODO remove

    required_client_version = (0, 5, 0)

    def __init__(self, multiworld, player):
        super(WotWWorld, self).__init__(multiworld, player)

    def generate_early(self):
        """Options checking"""
        if self.options.open_mode:
            self.options.no_rain.value = True

    def create_regions(self):
        world = self.multiworld
        player = self.player
        options = self.options

        for region_name in region_table:
            region = Region(region_name, player, world)
            world.regions.append(region)

        menu_region = Region("Menu", player, world)
        world.regions.append(menu_region)

        spawn_name = spawn_names[options.spawn]
        spawn_region = world.get_region(spawn_name, player)  # Links menu with spawn point
        menu_region.connect(spawn_region)

        menu_region.connect(world.get_region("HeaderStates", player))

        for loc_name in loc_table.keys():  # Create regions on locations
            region = Region(loc_name, player, world)
            world.regions.append(region)
            region.locations.append(WotWLocation(player, loc_name, self.location_name_to_id[loc_name], region))
        for quest_name in quest_table:  # Quests are locations that have to be tracked like events
            event_name = quest_name + ".quest"
            region = Region(event_name, player, world)
            world.regions.append(region)
            event = WotWLocation(player, event_name, None, region)
            event.show_in_spoiler = False
            event.place_locked_item(self.create_event(quest_name))
            region.locations.append(event)
            base_region = world.get_region(quest_name, player)
            base_region.connect(region)

        for event in event_table:  # Create events, their item, and a region to attach them
            region = Region(event, player, world)
            ev = WotWLocation(player, event, None, region)
            ev.show_in_spoiler = False
            ev.place_locked_item(self.create_event(event))
            world.regions.append(region)
            region.locations.append(ev)
        for event in refill_events:  # Create refill events, their item, and attach to their region
            region = Region(event, player, world)
            ev = WotWLocation(player, event, None, region)
            ev.show_in_spoiler = False
            ev.place_locked_item(self.create_event(event))
            world.regions.append(region)
            region.locations.append(ev)

        for entrance_name in entrance_table:  # Creates and connects the entrances
            (parent, connected) = entrance_name.split("_to_")
            parent_region = world.get_region(parent, player)
            connected_region = world.get_region(connected, player)
            entrance = parent_region.create_exit(entrance_name)
            entrance.access_rule = lambda state: False
            entrance.connect(connected_region)

        region = Region("Victory", player, world)  # Victory event
        ev = WotWLocation(player, "Victory", None, region)
        ev.place_locked_item(WotWItem("Victory", ItemClassification.progression, None, player))
        world.regions.append(region)
        region.locations.append(ev)

        world.completion_condition[player] = lambda state: state.has("Victory", player)

    def create_item(self, name: str) -> "WotWItem":
        return WotWItem(name, item_table[name][1], item_table[name][2], player=self.player)

    def create_items(self):
        world = self.multiworld
        player = self.player
        options = self.options

        skipped_items: List[str] = []  # Remove one instance of the item
        removed_items: List[str] = []  # Remove all instances of the item

        for item in spawn_items(world, options.spawn, options.difficulty):  # Staring items
            world.push_precollected(self.create_item(item))
            skipped_items.append(item)

        for item, count in options.start_inventory.value.items():
            for _ in range(count):
                skipped_items.append(item)

        if options.sword:
            world.push_precollected(self.create_item("Sword"))
            removed_items.append("Sword")

        if not options.tp:
            for item in group_table["teleporters"]:
                removed_items.append(item)

        if not options.extratp:
            for item in group_table["extra_tp"]:
                removed_items.append(item)

        if not options.bonus:
            for item in group_table["bonus"]:
                removed_items.append(item)

        if not options.extra_bonus:
            for item in group_table["bonus+"]:
                removed_items.append(item)

        if not options.skill_upgrade:
            for item in group_table["skill_upgrades"]:
                removed_items.append(item)

        if options.glades_done:
            removed_items.append("Gorlek Ore")

        if options.no_ks:
            removed_items.append("Keystone")

        if options.vanilla_shop_upgrades:
            shop_items = {"OpherShop.ExplodingSpike": "Exploding Spear",
                          "OpherShop.ShockSmash": "Hammer Shockwave",
                          "OpherShop.StaticStar": "Static Shuriken",
                          "OpherShop.ChargeBlaze": "Charge Blaze",
                          "OpherShop.RapidSentry": "Rapid Sentry",
                          "OpherShop.WaterBreath": "Water Breath",
                          "TwillenShop.Overcharge": "Overcharge",
                          "TwillenShop.TripleJump": "Triple Jump",
                          "TwillenShop.Wingclip": "Wingclip",
                          "TwillenShop.Swap": "Swap",
                          "TwillenShop.LightHarvest": "Light Harvest",
                          "TwillenShop.Vitality": "Vitality",
                          "TwillenShop.Energy": "Energy (Shard)",
                          "TwillenShop.Finesse": "Finesse"}
            for location, item in shop_items.items():
                loc = world.get_location(location, player)
                loc.place_locked_item(self.create_item(item))
                removed_items.append(item)

        if options.launch_on_seir:
            world.get_location("WindtornRuins.Seir", player).place_locked_item(self.create_item("Launch"))
            removed_items.append("Launch")

        # Contain all the locations that are used
        empty_locations: List[str] = []
        if options.glades_done:
            empty_locations += loc_sets["Rebuild"].copy()
        if options.no_trials:
            empty_locations += loc_sets["Trials"].copy()
        if options.qol or options.quests == Quests.option_none:
            empty_locations += loc_sets["QOL"].copy()
        if options.quests != Quests.option_all:
            empty_locations += loc_sets["HandToHand"].copy()
        if options.quests == Quests.option_none:
            empty_locations += loc_sets["Quests"].copy()

        for location in empty_locations:
            loc = world.get_location(location, player)
            loc.place_locked_item(self.create_item("Nothing"))

        counter = Counter(skipped_items)
        pool: List[WotWItem] = []

        for item, data in item_table.items():
            if item in removed_items:
                count = -counter[item]
            else:
                count = data[0] - counter[item]
            if count <= 0:  # This can happen with starting inventory
                count = 0

            for _ in range(count):
                pool.append(self.create_item(item))

        extras = len(world.get_unfilled_locations(player=self.player)) - len(pool)
        for _ in range(extras):
            pool.append(self.create_item(self.get_filler_item_name()))

        world.itempool += pool

        if options.difficulty == LogicDifficulty.option_moki:
            # Exclude a location that is inaccessible in the lowest difficulty.
            skipped_loc = world.get_location("WestPools.BurrowOre", player)
            skipped_loc.progress_type = 3

    def create_event(self, event: str) -> "WotWItem":
        return WotWItem(event, ItemClassification.progression, None, self.player)

    def get_filler_item_name(self) -> str:
        return self.random.choice(["50 Spirit Light", "100 Spirit Light"])

    def set_rules(self):
        world = self.multiworld
        player = self.player
        options = self.options
        menu = world.get_region("Menu", player)
        difficulty = options.difficulty

        # Add the basic rules.
        set_moki_rules(world, player, options)
        combat_rules(world, player, options)
        glitch_rules(world, player, options)
        unreachable_rules(world, player, options)

        # Add rules depending on the logic difficulty.
        if difficulty == LogicDifficulty.option_moki:
            # Extra rule for a location that is inaccessible in the lowest difficulty.
            add_rule(world.get_entrance("WestPools.Teleporter_to_WestPools.BurrowOre", player),
                     lambda state: state.has_all(("Burrow", "Clean Water", "Water Dash"), player), "or")
        if difficulty >= LogicDifficulty.option_gorlek:
            set_gorlek_rules(world, player, options)
            if options.glitches:
                set_gorlek_glitched_rules(world, player, options)
        if difficulty >= LogicDifficulty.option_kii:
            set_kii_rules(world, player, options)
            if options.glitches:
                set_kii_glitched_rules(world, player, options)
        if difficulty == LogicDifficulty.option_unsafe:
            set_unsafe_rules(world, player, options)
            if options.glitches:
                set_unsafe_glitched_rules(world, player, options)

        # Add victory condition
        victory_conn = world.get_region("WillowsEnd.Upper", player).connect(world.get_region("Victory", player))
        set_rule(victory_conn, lambda s: s.has_any(("Sword", "Hammer"), player)
                         and s.has_all(("Double Jump", "Dash", "Bash", "Grapple", "Glide", "Burrow", "Launch"), player))

        if "trees" in options.goal:
            add_rule(victory_conn, lambda s: all([s.can_reach_region(tree, player)
                          for tree in ["MarshSpawn.RegenTree",
                                       "MarshSpawn.DamageTree",
                                       "HowlsDen.SwordTree",
                                       "HowlsDen.DoubleJumpTree",
                                       "MarshPastOpher.BowTree",
                                       "WestHollow.DashTree",
                                       "EastHollow.BashTree",
                                       "GladesTown.DamageTree",
                                       "InnerWellspring.GrappleTree",
                                       "UpperPools.SwimDashTree",
                                       "UpperReach.LightBurstTree",
                                       "LowerDepths.FlashTree",
                                       "LowerWastes.BurrowTree",
                                       "WeepingRidge.LaunchTree",
                                       ]
                          ])
                     )

        if "wisps" in options.goal:
            add_rule(victory_conn, lambda s: s.has_all(("EastHollow.ForestsVoice", "LowerReach.ForestsMemory",
                                                        "UpperDepths.ForestsEyes", "WestPools.ForestsStrength",
                                                        "WindtornRuins.Seir"), player)
                     )
        if "quests" in options.goal:
            quest_list: List[str] = loc_sets["ExtraQuests"].copy()
            if options.quests == Quests.option_no_hand:
                quest_list += loc_sets["Quests"].copy()
            elif options.quests == Quests.option_all:
                quest_list += loc_sets["Quests"].copy() + loc_sets["HandToHand"].copy()
            if not options.glades_done:
                quest_list += loc_sets["Rebuild"].copy()
            if not options.qol and options.quests != Quests.option_none:
                quest_list += loc_sets["QOL"].copy()
            add_rule(victory_conn, lambda s: s.has_all((quests for quests in quest_list), player))

        def try_connect(region_in: Region, region_out: Region, connection: str | None = None, rule=None):
            """Create the region connection if it doesn't already exist."""
            if connection is None:
                connection = f"{region_in.name} -> {region_out.name}"
            if not world.regions.entrance_cache[player].get(connection):
                region_in.connect(region_out, connection, rule)

        # Rules for specific options
        if options.qol:
            try_connect(menu, world.get_region("GladesTown.TuleySpawned", player))
            world.get_region("WoodsEntry.LastTreeBranch", player).connect(
                world.get_region("WoodsEntry.TreeSeed", player))
        if options.better_spawn:
            try_connect(menu, world.get_region("MarshSpawn.HowlBurnt", player))
            try_connect(menu, world.get_region("HowlsDen.BoneBarrier", player))
            try_connect(menu, world.get_region("EastPools.EntryLever", player))
            try_connect(menu, world.get_region("UpperWastes.LeverDoor", player))

        if "Everything" in options.no_combat or "Bosses" in options.no_combat:
            for entrance in ("HeaderStates_to_SkipKwolok",
                             "HeaderStates_to_SkipMora1",
                             "HeaderStates_to_SkipMora2"):
                set_rule(world.get_entrance(entrance, player), lambda s: True)
        else:  # Connect these events when the seed is completed, to make them reachable.
            set_rule(world.get_entrance("HeaderStates_to_SkipKwolok", player),
                     lambda s: s.has("Victory", player))
            set_rule(world.get_entrance("HeaderStates_to_SkipMora1", player),
                     lambda s: s.has("Victory", player))
            set_rule(world.get_entrance("HeaderStates_to_SkipMora2", player),
                     lambda s: s.has("Victory", player))
        if "Everything" in options.no_combat or "Shrines" in options.no_combat:
            for entrance in (
                        "DenShrine_to_HowlsDen.CombatShrineCompleted",
                        "MarshShrine_to_MarshPastOpher.CombatShrineCompleted",
                        "GladesShrine_to_WestGlades.CombatShrineCompleted",
                        "WoodsShrine_to_WoodsMain.CombatShrineCompleted",
                        "DepthsShrine_to_LowerDepths.CombatShrineCompleted"):
                set_rule(world.get_entrance(entrance, player), lambda s: True)

        if options.better_wellspring:
            try_connect(menu, world.get_region("InnerWellspring.TopDoorOpen", player))
        if options.no_ks:
            for event in ("MarshSpawn.KeystoneDoor",
                          "HowlsDen.KeystoneDoor",
                          "MidnightBurrows.KeystoneDoor",
                          "WoodsEntry.KeystoneDoor",
                          "WoodsMain.KeystoneDoor",
                          "LowerReach.KeystoneDoor",
                          "UpperReach.KeystoneDoor",
                          "UpperDepths.EntryKeystoneDoor",
                          "UpperDepths.CentralKeystoneDoor",
                          "UpperPools.KeystoneRoomBubbleFree",
                          "UpperPools.KeystoneDoor",
                          "UpperWastes.KeystoneDoor"):
                try_connect(menu, world.get_region(event, player))
        if options.open_mode:
            for event in ("HowlsDen.BoneBarrier",
                          "MarshSpawn.ToOpherBarrier",
                          "MarshSpawn.TokkBarrier",
                          "MarshSpawn.LogBroken",
                          "MarshSpawn.BurrowsOpen",
                          "MidnightBurrows.HowlsDenShortcut",
                          "MarshPastOpher.EyestoneDoor",
                          "WestHollow.PurpleDoorOpen",
                          "EastHollow.DepthsLever",
                          "GladesTown.GromsWall",
                          "OuterWellspring.EntranceDoorOpen",
                          "InnerWellspring.MiddleDoorsOpen",
                          "InnerWellspring.TopDoorOpen",
                          "EastHollow.DepthsOpen",
                          "LowerReach.Lever",
                          "LowerReach.TPLantern",
                          "LowerReach.RolledSnowball",
                          "LowerReach.EastDoorLantern",
                          "LowerReach.ArenaBeaten",
                          "UpperWastes.LeverDoor",
                          "WindtornRuins.RuinsLever",
                          "WeepingRidge.ElevatorFightCompleted",
                          "EastPools.EntryLever",
                          "EastPools.CentralRoomPurpleWall",
                          "UpperPools.UpperWaterDrained",
                          "UpperPools.ButtonDoorAboveTree",):
                try_connect(menu, world.get_region(event, player))
        if options.no_rain:
            for event in ("HowlsDen.UpperLoopExitBarrier",
                          "HowlsDen.UpperLoopEntranceBarrier",
                          "HowlsDen.RainLifted",):
                try_connect(menu, world.get_region(event, player))
            if not options.better_spawn:
                try_connect(menu, world.get_region("MarshSpawn.HowlBurnt", player))
        if options.glades_done:
            for quest in ("InnerWellspring.BlueMoonSeed",
                          "EastPools.GrassSeed",
                          "UpperDepths.LightcatcherSeed",
                          "UpperReach.SpringSeed",
                          "UpperWastes.FlowersSeed",
                          "WoodsEntry.TreeSeed",
                          "GladesTown.RebuildTheGlades",
                          "GladesTown.RegrowTheGlades",):
                try_connect(menu, world.get_region(quest + ".quest", player))
            for event in ("GladesTown.BuildHuts",
                          "GladesTown.RoofsOverHeads",
                          "GladesTown.OnwardsAndUpwards",
                          "GladesTown.ClearThorns",
                          "GladesTown.CaveEntrance"):
                try_connect(menu, world.get_region(event, player))

        if options.quests != Quests.option_none:  # Open locations locked behind NPCs
            for quest in ("WoodsEntry.LastTreeBranch",
                          "WoodsEntry.DollQI",
                          "GladesTown.FamilyReunionKey"):
                try_connect(menu, world.get_region(quest + ".quest", player))

    def fill_slot_data(self) -> Dict[str, any]:
        world = self.multiworld
        player = self.player
        options = self.options
        logic_difficulty: List[str] = ["Moki", "Gorlek", "Kii", "Unsafe"]
        coord: List[List[float]] = [
            [-799, -4310, "MarshSpawn.Main"],
            [-945, -4582, "MidnightBurrows.Teleporter"],
            [-328, -4536, "HowlsDen.Teleporter"],
            [-150, -4238, "EastHollow.Teleporter"],
            [-307, -4153, "GladesTown.Teleporter"],
            [-1308, -3675, "InnerWellspring.Teleporter"],
            [611, -4162, "WoodsEntry.Teleporter"],
            [1083, -4052, "WoodsMain.Teleporter"],
            [-259, -3962, "LowerReach.Teleporter"],
            [513, -4361, "UpperDepths.Teleporter"],
            [-1316, -4153, "EastPools.Teleporter"],
            [-1656, -4171, "WestPools.Teleporter"],
            [1456, -3997, "LowerWastes.WestTP"],
            [1992, -3902, "LowerWastes.EastTP"],
            [2044, -3679, "UpperWastes.NorthTP"],
            [2130, -3984, "WindtornRuins.RuinsTP"],
            [422, -3864, "WillowsEnd.InnerTP"]
        ]
        icons_paths: Dict[str, str] = {}
        shops: List[str] = ["TwillenShop.Overcharge",
                            "TwillenShop.TripleJump",
                            "TwillenShop.Wingclip",
                            "TwillenShop.Swap",
                            "TwillenShop.LightHarvest",
                            "TwillenShop.Vitality",
                            "TwillenShop.Energy",
                            "TwillenShop.Finesse",
                            "OpherShop.WaterBreath",
                            "OpherShop.Spike",
                            "OpherShop.SpiritSmash",
                            "OpherShop.Teleport",
                            "OpherShop.SpiritStar",
                            "OpherShop.Blaze",
                            "OpherShop.Sentry",
                            "OpherShop.ExplodingSpike",
                            "OpherShop.ShockSmash",
                            "OpherShop.StaticStar",
                            "OpherShop.ChargeBlaze",
                            "OpherShop.RapidSentry",
                            "LupoShop.HCMapIcon",
                            "LupoShop.ECMapIcon",
                            "LupoShop.ShardMapIcon"
                            ]
        for loc in shops:
            item = world.get_location(loc, player).item
            icon_path = get_item_iconpath(self, item, bool(options.shop_keywords))
            icons_paths.update({loc: icon_path})

        slot_data: Dict[str, any] = {
            "difficulty": logic_difficulty[options.difficulty.value],
            "glitches": bool(options.glitches.value),
            "spawn_x": coord[options.spawn.value][0],
            "spawn_y": coord[options.spawn.value][1],
            "spawn_anchor": coord[options.spawn.value][2],
            "goal_trees": bool("trees" in options.goal),
            "goal_quests": bool("quests" in options.goal),
            "goal_wisps": bool("wisps" in options.goal),
            "hard": bool(options.hard_mode.value),
            "qol": bool(options.qol.value),
            "hints": bool(options.hints.value),
            "knowledge_hints": bool(options.knowledge_hints.value),
            "better_spawn": bool(options.better_spawn.value),
            "better_wellspring": bool(options.better_wellspring.value),
            "no_rain": bool(options.no_rain.value),
            "skip_boss": bool("Everything" in options.no_combat or "Bosses" in options.no_combat),
            "skip_demi_boss": bool("Everything" in options.no_combat or "Demi Bosses" in options.no_combat),
            "skip_shrine": bool("Everything" in options.no_combat or "Shrines" in options.no_combat),
            "skip_arena": bool("Everything" in options.no_combat or "Arenas" in options.no_combat),
            "no_trials": bool(options.no_trials.value),
            "no_hearts": bool(options.no_hearts.value),
            "no_hand_quest": bool(options.quests == Quests.option_no_hand or options.quests == Quests.option_none),
            "no_quests": bool(options.quests == Quests.option_none),
            "no_ks": bool(options.no_ks.value),
            "open_mode": bool(options.open_mode),
            "glades_done": bool(options.glades_done),
            "shop_icons": icons_paths,
        }

        return slot_data


class WotWItem(Item):
    game: str = "Ori and the Will of the Wisps"


class WotWLocation(Location):
    game: str = "Ori and the Will of the Wisps"
