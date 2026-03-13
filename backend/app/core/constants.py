from __future__ import annotations

from dataclasses import dataclass


POSITIONS = [
    "Loosehead Prop",
    "Hooker",
    "Tighthead Prop",
    "Lock",
    "Blindside Flanker",
    "Openside Flanker",
    "Number 8",
    "Scrumhalf",
    "Flyhalf",
    "Inside Centre",
    "Outside Centre",
    "Wing",
    "Fullback",
]

LINEUP_SLOTS = [
    "Loosehead Prop",
    "Hooker",
    "Tighthead Prop",
    "Lock",
    "Lock",
    "Blindside Flanker",
    "Openside Flanker",
    "Number 8",
    "Scrumhalf",
    "Flyhalf",
    "Wing",
    "Inside Centre",
    "Outside Centre",
    "Wing",
    "Fullback",
]

TACTIC_VALUES = {
    "attacking_style": ["forward-oriented", "balanced", "expansive"],
    "kicking_approach": ["low", "balanced", "high"],
    "defensive_system": ["drift", "balanced", "rush"],
    "ruck_commitment": ["low", "balanced", "high"],
    "set_piece_intent": ["safe", "balanced", "aggressive"],
    "goal_choice": ["go for posts", "balanced", "kick to corner"],
}

TRAINING_FOCUSES = ["fitness", "attack", "defense", "set_piece", "recovery"]
PERFORMANCE_INTENSITIES = ["light", "balanced", "heavy"]
CONTACT_LEVELS = ["low", "balanced", "high"]
REHAB_MODES = ["standard", "physio", "accelerated"]
CLEARANCE_STATUSES = ["out", "managed", "full"]
MEDICAL_ALERT_FATIGUE = 68

SECONDARY_POSITION_MAP = {
    "Loosehead Prop": ["Hooker"],
    "Hooker": ["Loosehead Prop", "Tighthead Prop"],
    "Tighthead Prop": ["Hooker"],
    "Lock": ["Blindside Flanker"],
    "Blindside Flanker": ["Lock", "Number 8"],
    "Openside Flanker": ["Blindside Flanker", "Number 8"],
    "Number 8": ["Blindside Flanker", "Openside Flanker"],
    "Scrumhalf": ["Flyhalf"],
    "Flyhalf": ["Inside Centre", "Fullback"],
    "Inside Centre": ["Outside Centre", "Flyhalf"],
    "Outside Centre": ["Inside Centre", "Wing"],
    "Wing": ["Fullback", "Outside Centre"],
    "Fullback": ["Wing", "Flyhalf"],
}

ROSTER_TEMPLATE = {
    "Loosehead Prop": 2,
    "Hooker": 3,
    "Tighthead Prop": 3,
    "Lock": 4,
    "Blindside Flanker": 2,
    "Openside Flanker": 2,
    "Number 8": 2,
    "Scrumhalf": 2,
    "Flyhalf": 2,
    "Inside Centre": 2,
    "Outside Centre": 2,
    "Wing": 2,
    "Fullback": 2,
}

ATTRIBUTE_NAMES = [
    "speed",
    "strength",
    "endurance",
    "handling",
    "passing",
    "tackling",
    "kicking_hand",
    "goal_kicking",
    "breakdown",
    "scrum",
    "lineout",
    "decision_making",
    "composure",
    "discipline",
    "leadership",
]


@dataclass(frozen=True)
class PositionProfile:
    speed: int
    strength: int
    endurance: int
    handling: int
    passing: int
    tackling: int
    kicking_hand: int
    goal_kicking: int
    breakdown: int
    scrum: int
    lineout: int
    decision_making: int
    composure: int
    discipline: int
    leadership: int


POSITION_PROFILES: dict[str, PositionProfile] = {
    "Loosehead Prop": PositionProfile(48, 82, 70, 56, 48, 74, 34, 18, 66, 86, 24, 58, 62, 64, 52),
    "Hooker": PositionProfile(55, 78, 72, 62, 54, 72, 38, 22, 65, 76, 68, 60, 62, 62, 58),
    "Tighthead Prop": PositionProfile(45, 84, 68, 54, 46, 76, 32, 18, 64, 88, 26, 58, 60, 62, 54),
    "Lock": PositionProfile(54, 80, 74, 60, 52, 76, 30, 18, 60, 72, 82, 60, 64, 64, 58),
    "Blindside Flanker": PositionProfile(66, 76, 78, 62, 56, 80, 34, 18, 76, 56, 52, 64, 64, 60, 60),
    "Openside Flanker": PositionProfile(70, 72, 80, 64, 60, 82, 36, 20, 82, 48, 50, 68, 64, 58, 58),
    "Number 8": PositionProfile(68, 78, 78, 66, 58, 78, 36, 22, 74, 58, 54, 66, 66, 60, 62),
    "Scrumhalf": PositionProfile(76, 52, 76, 72, 80, 62, 62, 36, 58, 24, 28, 78, 68, 62, 60),
    "Flyhalf": PositionProfile(72, 54, 74, 74, 82, 58, 80, 76, 50, 22, 28, 82, 76, 64, 64),
    "Inside Centre": PositionProfile(74, 66, 76, 76, 74, 68, 54, 32, 52, 28, 30, 74, 72, 62, 58),
    "Outside Centre": PositionProfile(78, 64, 76, 78, 72, 66, 50, 28, 48, 24, 28, 72, 72, 60, 56),
    "Wing": PositionProfile(84, 58, 74, 74, 64, 58, 56, 26, 42, 18, 22, 68, 70, 58, 50),
    "Fullback": PositionProfile(80, 60, 76, 76, 74, 62, 78, 58, 46, 20, 24, 78, 76, 62, 56),
}

CLUB_IDENTITIES = [
    ("Kingsport Admirals", "KSA", 83, 8_600_000, 3_000_000, "Finish in the top three"),
    ("Redhaven Forge", "RHF", 80, 7_900_000, 2_900_000, "Push for continental qualification"),
    ("Westmarch Stags", "WMS", 78, 7_600_000, 2_800_000, "Challenge for the playoffs"),
    ("Southport Harriers", "SPH", 76, 7_100_000, 2_700_000, "Stay in the top half"),
    ("Blackwater Tritons", "BWT", 75, 6_900_000, 2_600_000, "Compete for top-half consistency"),
    ("Ironvale Miners", "IVM", 73, 6_500_000, 2_500_000, "Build momentum and finish top six"),
    ("Highmoor Ravens", "HMR", 71, 6_000_000, 2_350_000, "Avoid a bottom-three finish"),
    ("Suncoast Breakers", "SCB", 69, 5_800_000, 2_250_000, "Stabilise in mid-table"),
    ("Rivergate Falcons", "RGF", 67, 5_300_000, 2_100_000, "Avoid the relegation conversation"),
    ("Northcliff Armada", "NCA", 65, 5_000_000, 2_000_000, "Battle to survive the season"),
]
