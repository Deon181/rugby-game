from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationConfig:
    blocks: int = 8
    block_minutes: int = 10
    home_advantage: float = 2.5
    base_injury_chance: float = 0.02
    base_card_chance: float = 0.018
    base_entry_scale: float = 2.0
    penalty_goal_success_base: float = 0.62
    conversion_success_base: float = 0.67
    drop_goal_chance: float = 0.025


CONFIG = SimulationConfig()
