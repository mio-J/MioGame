"""Analytic scenarios, not a playable map or proof of player enjoyment."""
import json
from pathlib import Path


def commercial(n, weights, tax_bonus=0, statue=False, triumph=False):
    ceiling = (50 if statue else 40) * (2 if triumph else 1)
    headroom = 180 * max(0, 1 - tax_bonus)
    weights = [w * (2 if triumph else 1) for w in weights]
    total = n * min(sum(weights), ceiling, headroom)
    return round(total, 4)


out = {
    "method": "analytic fixed scenarios; no live playtest or generated-map validation",
    "equipment": {
        "armor_1_old_raw_damage_to_save_100": 3100,
        "armor_3_raw_damage_to_save_100": 1100,
        "armor_3_repeated_1100_damage_saved": round(1100 * (1 - 30 / 33), 4),
        "potion_320hp_armor10_heal_hp": 128,
        "potion_320hp_armor10_raw_damage_equivalent": round(128 / (30 / 40), 4),
        "shield_150hp_vs_180_burst_hp_left": 70,
        "potion_150hp_vs_180_burst": "dead before post-hit potion trigger",
        "assumptions": "repeated physical engagements include healing between them; armor reduces healing load, not an automatic win; shield/potion consumable once",
    },
    "commercial": {
        "saturated_40_people_three_stores": commercial(40, [12, 12, 24]),
        "saturated_add_electrical_net": commercial(40, [12, 12, 24, 20]) - commercial(40, [12, 12, 24]),
        "85pct_tax_bonus_per_resident_headroom": round(180 * .15, 4),
        "statue_at_85pct_bonus_net": commercial(40, [12, 12, 24], .85, True) - commercial(40, [12, 12, 24], .85),
        "triumph_40_people_three_stores": commercial(40, [12, 12, 24], triumph=True),
        "department_80_existing_60_new_net": round(commercial(80, [15, 15, 24]) + commercial(60, [24]) - commercial(80, [12, 12]), 4),
        "industrial_smith_40_people_income_less_noise": commercial(40, [6], -.1) - 40 * 180 * .1,
    },
    "exploit_boundaries": {
        "discount_recovery": {"paid": 1000, "refund": 500, "cycle_profit": -500},
        "energy": "cannot voluntarily remove supply if result worsens or causes a deficit; enemy destruction does not disable existing effects",
        "prosperity": "current buildings contribute, irreversible tier first award once; one-time costly milestone investment remains allowed",
        "drone_8_losses_single_queue_seconds": 160,
        "decoy_wall": "1000 gold/30s labor per segment, 20% construction HP; target-nearest rule retained, path lure requires live geometry test",
        "loan": "at least three future major-wave stages required; three 12000 repayments at subsequent cycle starts; no terminal free draw",
    },
}
assert out["commercial"]["saturated_add_electrical_net"] == 0
assert out["commercial"]["statue_at_85pct_bonus_net"] == 0
assert out["equipment"]["shield_150hp_vs_180_burst_hp_left"] > 0
assert out["exploit_boundaries"]["discount_recovery"]["cycle_profit"] < 0
path = Path(__file__).with_name("gameplay_results.json")
path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": "checks_passed", "output": path.name}))
