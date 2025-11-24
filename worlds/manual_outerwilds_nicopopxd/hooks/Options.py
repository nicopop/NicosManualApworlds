# Object classes from AP that represent different types of options that you can create
from Options import FreeText, NumericOption, Toggle, DefaultOnToggle, Choice, TextChoice, Range, NamedRange

# These helper methods allow you to determine if an option has been set, or what its value is, for any player in the multiworld
from ..Helpers import is_option_enabled, get_option_value



####################################################################
# NOTE: At the time that options are created, Manual has no concept of the multiworld or its own world.
#       Options are defined before the world is even created.
#
# Example of creating your own option:
#
#   class MakeThePlayerOP(Toggle):
#       """Should the player be overpowered? Probably not, but you can choose for this to do... something!"""
#       display_name = "Make me OP"
#
#   options["make_op"] = MakeThePlayerOP
#
#
# Then, to see if the option is set, you can call is_option_enabled or get_option_value.
#####################################################################


# To add an option, use the before_options_defined hook below and something like this:
#   options["total_characters_to_win_with"] = TotalCharactersToWinWith
#
#class TotalCharactersToWinWith(Range):
#    """Instead of having to beat the game with all characters, you can limit locations to a subset of character victory locations."""
#    display_name = "Number of characters to beat the game with before victory"
#    range_start = 10
#    range_end = 50
#    default = 50

class RequireSolanum(Toggle):
    """Do you want to require Talking to Solanum before you can win?"""
    display_name = "Require Talking to Solanum"

class RequirePrisoner(Toggle):
    """Do you want to require Talking to the Prisoner before you can win?"""
    display_name = "Require Talking to the Prisoner"
class do_spooks(DefaultOnToggle):
    """Do you want to enable some of the Spookier DLC locations?"""
    display_name = "ReduceSpooks"
class MainDlcKnowledge(Toggle):
    """Should The main 2 dlc Progression items (stranger access and dreamworld access) be enabled?"""
    display_name = "Enable Main 2 Dlc Access Items"

class LocalPlacedItems(DefaultOnToggle):
    """Do you want some items to be predetermined to help with the flow of the game"""#todo find a better way to phrase this
    display_name = "Predetermined Local Items"

class ShuffleSpacesuit(Toggle):
    """Puts the spacesuit into the Archipelago item pool, forcing you to play suitless until it's found.
    This is a HIGHLY EXPERIMENTAL setting. Expect logic bugs. Feedback encouraged."""
    display_name = "Shuffle SpaceSuit"

# class ShipKey(DefaultOnToggle):
#     """Lock being able to move the ship behind this item, you still can grab the SpaceSuit and use it's jetpack but you can't take off with the ship"""
#     display_name = "Ship Key Logic"

class EarlyShipKey(Choice):
    """Do you want the Ship Key to be located in the early game
    Leave it as startswith to disable the Ship Key logic"""
    display_name = "Ship Key Logic"
    option_local_early = 0
    option_local_anywhere = 1
    option_global_early = 2
    alias_global = option_global_early
    option_global_anywhere = 3
    option_startswith = 4
    default = 4

class RandomContent(Choice):
    """What part of the game do you want to play + minimum content for your goal,
    Base Game: disable the dlc
    DLC: disable every base game locations except for those needed by the goal
    both(default): everything's allowed
    """
    display_name = "Randomized content"
    option_both = 0
    alias_everything = 0
    option_base_game = 1
    alias_no_dlc = 1
    alias_base = 1
    option_dlc = 2
    alias_only_dlc = 2
    default = 0

class BiggerSphere1(Toggle):
    """when true remove the launch codes logic so Sphere 1 is bigger
    You will still need to talk to Hornfels to start the loop"""
    display_name = "Remove Launch codes"

class ReverseTeleporter(Toggle):
    """Turn this on if you want and use a mod to enable reverse teleporters,
    Warning No such mod exist as of writing this, and thus the logic is untested"""
    display_name = "Enable Reverse Teleporters Logic"

class Goal(Choice):
    """Where do you want to end,
    standard(default): for dlc only will end on prisoner, for base and base+dlc will end at the eye.
    Vanilla% aka eye: Will require going to the eye.
    Prisoner% aka prisoner: Will end after talking to the prisoner
    GhostsInTheMachine% aka visit_all_archive: Will End by visiting all the archive in a single loop without being caught
    BreakSpaceTimeInATP% aka ash_twin_project_break_spacetime: Require going to the ash twin project and break spacetime there.
    BreakSpaceTimeInLab% aka high_energy_lab_break_spacetime: Require going to the high energy lab and break spacetime there.
    QuantumStuck% aka stuck_with_solanum: Get the Adv. warp core to Solanum and wait for Credits.
    StrangerStuck% aka stuck_in_stranger: Get the Adv. warp core to the Stranger and wait for Credits.
    DreamStuck% aka stuck_in_dream: Get the Adv. warp core to the Stranger and die to get to the Dreamworld.
    """
    display_name = "Goal"
    option_standard = 0
    alias_default = 0
    option_eye = 1
    option_prisoner = 2
    option_visit_all_archive = 3
    option_ash_twin_project_break_spacetime = 4
    option_high_energy_lab_break_spacetime = 5
    option_stuck_with_solanum = 6
    option_stuck_in_stranger = 7
    option_stuck_in_dream = 8
    default = 0

class ApWorldVersion(FreeText):
    """Do not change this, it will get set to the apworld version"""
    display_name = "Game Version (Detected)"
    default = "Should Be Detected"

# This is called before any manual options are defined, in case you want to define your own with a clean slate or let Manual define over them
def before_options_defined(options: dict) -> dict:
#    options["total_characters_to_win_with"] = TotalCharactersToWinWith
    options["game_version"] = ApWorldVersion
    options["require_solanum"] = RequireSolanum
    options["require_prisoner"] = RequirePrisoner
    options["enable_spooks"] = do_spooks #we'll need to talk on what need to be disabled/modified when this is enabled
    options["remove_launch_codes"] = BiggerSphere1
    options["ship_key_logic"] = EarlyShipKey
    options["shuffle_spacesuit"] = ShuffleSpacesuit
    options["do_place_item_category"] = LocalPlacedItems
    options["randomized_content"] = RandomContent
    options["dlc_access_items"] = MainDlcKnowledge
    options["reverse_teleporters"] = ReverseTeleporter
    return options

# This is called after any manual options are defined, in case you want to see what options are defined or want to modify the defined options
def after_options_defined(options: dict) -> dict:
    # the generated goal option will not keep your defined values or documentation string you'll need to add them here:
    # To automatically convert your own goal to alias of the generated goal uncomment this below and replace 'Goal' with your own option of type Choice
    your_goal_class = Goal #Your Goal class here
    generated_goal = options.get('goal', {})
    if generated_goal and issubclass(your_goal_class, Choice) and not issubclass(generated_goal, your_goal_class):
        goals = {'option_' + i: v for i, v in generated_goal.options.items() if i != 'default'}
        for option, value in your_goal_class.options.items():
            if option == 'default':
                continue
            goals[f"alias_{option}"] = value
        options['goal'] = type('goal', (Choice,), goals)
        options['goal'].default = your_goal_class.options.get('default', generated_goal.default)
        options['goal'].__doc__ = your_goal_class.__doc__ or options['goal'].__doc__
    return options