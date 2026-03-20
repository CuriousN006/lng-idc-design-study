from __future__ import annotations


def compute_theoretical_minimum_power(config: dict, total_cooling_kw: float) -> dict[str, float]:
    assignment = config["assignment"]
    chilled_mean_k = 0.5 * (assignment["chilled_water_supply_temp_k"] + assignment["chilled_water_return_temp_k"])
    ambient_k = assignment["ambient_air_temp_k"]
    minimum_power_kw = total_cooling_kw * (ambient_k - chilled_mean_k) / chilled_mean_k
    return {
        "cold_reservoir_temp_k": chilled_mean_k,
        "hot_reservoir_temp_k": ambient_k,
        "minimum_power_kw": minimum_power_kw,
    }
