from __future__ import annotations

import math

import pandas as pd


SQUARE_FEET_PER_SQUARE_METER = 10.763910416709722
GPM_PER_M3_S = 15_850.323141489
INCHES_PER_METER = 39.37007874015748
METERS_PER_MILE = 1609.344

SHELL_AND_TUBE_AREA_FT2 = [
    100.0,
    200.0,
    300.0,
    400.0,
    500.0,
    600.0,
    700.0,
    800.0,
    900.0,
    1000.0,
    2000.0,
    3000.0,
    4000.0,
    5000.0,
    6000.0,
    7000.0,
    8000.0,
    9000.0,
    10000.0,
    15000.0,
    20000.0,
    30000.0,
    40000.0,
    50000.0,
    60000.0,
    70000.0,
]

SHELL_AND_TUBE_INSTALLED_COST_1998_USD = [
    48300.0,
    55800.0,
    57300.0,
    59100.0,
    68000.0,
    68400.0,
    70000.0,
    70400.0,
    72600.0,
    73100.0,
    95800.0,
    109600.0,
    132900.0,
    141800.0,
    151100.0,
    203500.0,
    212400.0,
    222100.0,
    229800.0,
    321500.0,
    427000.0,
    573900.0,
    767500.0,
    953000.0,
    1106600.0,
    1425600.0,
]

CENTRIFUGAL_PUMP_FLOW_GPM = [
    100.0,
    200.0,
    300.0,
    400.0,
    500.0,
    1000.0,
    2000.0,
    3000.0,
    4000.0,
    5000.0,
    6000.0,
    7000.0,
    8000.0,
    9000.0,
    10000.0,
]

CENTRIFUGAL_PUMP_INSTALLED_COST_1998_USD = [
    22800.0,
    23800.0,
    27700.0,
    28500.0,
    29000.0,
    37500.0,
    44800.0,
    58100.0,
    72300.0,
    77100.0,
    93400.0,
    103000.0,
    119700.0,
    126200.0,
    144800.0,
]


def _interpolate_with_linear_extrapolation(x: float, x_points: list[float], y_points: list[float]) -> float:
    if x <= x_points[0]:
        x0, x1 = x_points[0], x_points[1]
        y0, y1 = y_points[0], y_points[1]
    elif x >= x_points[-1]:
        x0, x1 = x_points[-2], x_points[-1]
        y0, y1 = y_points[-2], y_points[-1]
    else:
        for idx in range(len(x_points) - 1):
            x0 = x_points[idx]
            x1 = x_points[idx + 1]
            if x0 <= x <= x1:
                y0 = y_points[idx]
                y1 = y_points[idx + 1]
                break
    if abs(x1 - x0) < 1e-12:
        return y0
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def shell_and_tube_installed_cost_1998_usd(area_m2: float) -> float:
    area_ft2 = area_m2 * SQUARE_FEET_PER_SQUARE_METER
    return _interpolate_with_linear_extrapolation(area_ft2, SHELL_AND_TUBE_AREA_FT2, SHELL_AND_TUBE_INSTALLED_COST_1998_USD)


def centrifugal_pump_installed_cost_1998_usd(flow_m3_s: float) -> float:
    flow_gpm = flow_m3_s * GPM_PER_M3_S
    return _interpolate_with_linear_extrapolation(flow_gpm, CENTRIFUGAL_PUMP_FLOW_GPM, CENTRIFUGAL_PUMP_INSTALLED_COST_1998_USD)


def _current_krw_per_1998_usd(config: dict) -> float:
    cost_indexing = config["economic_inputs"]["cost_indexing"]
    inflation_factor = float(cost_indexing["current_cpi_u"]) / float(cost_indexing["base_year_cpi_u"])
    return inflation_factor * float(cost_indexing["krw_per_usd"])


def _urban_natural_gas_pipeline_cost_1998_usd_per_mile(diameter_m: float) -> float:
    diameter_in = diameter_m * INCHES_PER_METER
    return 836.0 * diameter_in ** 2 + 50_441.0 * diameter_in + 291_948.0


def estimate_capex(config: dict, idc_hx_result: dict, hx_result: dict, pipeline_result: dict, idc_secondary_loop_result: dict) -> dict[str, object]:
    capex_cfg = config["economic_inputs"]["capex_models"]
    krw_per_1998_usd = _current_krw_per_1998_usd(config)

    lng_hx_area_m2 = float(hx_result["selected_geometry"]["provided_area_m2"])
    idc_hx_area_m2 = float(idc_hx_result["required_area_m2"])
    selected_pipeline = pipeline_result["selected_design"]
    base_distance_m = float(config["assignment"]["pipeline_distance_m"])

    lng_hx_cost_krw = (
        shell_and_tube_installed_cost_1998_usd(lng_hx_area_m2)
        * float(capex_cfg["cryogenic_hx_installation_multiplier"])
        * krw_per_1998_usd
    )
    idc_hx_cost_krw = (
        shell_and_tube_installed_cost_1998_usd(idc_hx_area_m2)
        * float(capex_cfg["idc_hx_installation_multiplier"])
        * krw_per_1998_usd
    )

    supply_pipeline_cost_krw = (
        _urban_natural_gas_pipeline_cost_1998_usd_per_mile(float(selected_pipeline["supply_id_m"]))
        * (base_distance_m / METERS_PER_MILE)
        * float(capex_cfg["cryogenic_pipeline_installation_multiplier"])
        * krw_per_1998_usd
    )
    return_pipeline_cost_krw = (
        _urban_natural_gas_pipeline_cost_1998_usd_per_mile(float(selected_pipeline["return_id_m"]))
        * (base_distance_m / METERS_PER_MILE)
        * float(capex_cfg["cryogenic_pipeline_installation_multiplier"])
        * krw_per_1998_usd
    )

    supply_flow_m3_s = (
        float(selected_pipeline["velocity_supply_m_per_s"])
        * math.pi
        * float(selected_pipeline["supply_id_m"]) ** 2
        / 4.0
    )
    lng_pump_cost_krw = (
        centrifugal_pump_installed_cost_1998_usd(supply_flow_m3_s)
        * float(capex_cfg["pump_installation_multiplier"])
        * krw_per_1998_usd
    )
    idc_pump_cost_krw = (
        centrifugal_pump_installed_cost_1998_usd(float(idc_secondary_loop_result["volumetric_flow_m3_s"]))
        * float(capex_cfg["pump_installation_multiplier"])
        * krw_per_1998_usd
    )

    direct_rows = [
        {
            "component": "LNG vaporizer",
            "basis": f"{lng_hx_area_m2:,.1f} m2 provided area",
            "installed_cost_krw": lng_hx_cost_krw,
            "source_ids": "SRC-021,ASM-057",
        },
        {
            "component": "IDC-side liquid-liquid heat exchanger",
            "basis": f"{idc_hx_area_m2:,.1f} m2 required area",
            "installed_cost_krw": idc_hx_cost_krw,
            "source_ids": "SRC-021,ASM-058",
        },
        {
            "component": "LNG supply pipeline",
            "basis": f"{base_distance_m / 1000.0:.1f} km, {float(selected_pipeline['supply_id_m']) * INCHES_PER_METER:.1f} in",
            "installed_cost_krw": supply_pipeline_cost_krw,
            "source_ids": "SRC-022,SRC-023,SRC-024,SRC-025,ASM-059",
        },
        {
            "component": "LNG return pipeline",
            "basis": f"{base_distance_m / 1000.0:.1f} km, {float(selected_pipeline['return_id_m']) * INCHES_PER_METER:.1f} in",
            "installed_cost_krw": return_pipeline_cost_krw,
            "source_ids": "SRC-022,SRC-023,SRC-024,SRC-025,ASM-059",
        },
        {
            "component": "LNG circulation pump",
            "basis": f"{supply_flow_m3_s * GPM_PER_M3_S:,.0f} gpm",
            "installed_cost_krw": lng_pump_cost_krw,
            "source_ids": "SRC-021,SRC-022,SRC-023,SRC-024",
        },
        {
            "component": "IDC secondary-loop pump",
            "basis": f"{float(idc_secondary_loop_result['volumetric_flow_m3_s']) * GPM_PER_M3_S:,.0f} gpm",
            "installed_cost_krw": idc_pump_cost_krw,
            "source_ids": "SRC-021,SRC-022,SRC-023,SRC-024",
        },
    ]
    direct_capex_krw = sum(row["installed_cost_krw"] for row in direct_rows)
    indirect_capex_krw = direct_capex_krw * float(capex_cfg["balance_of_plant_fraction"])
    table = pd.DataFrame(direct_rows)
    table.loc[len(table)] = {
        "component": "Balance of plant and integration",
        "basis": f"{float(capex_cfg['balance_of_plant_fraction']):.0%} of direct CAPEX",
        "installed_cost_krw": indirect_capex_krw,
        "source_ids": "ASM-060",
    }
    total_capex_krw = direct_capex_krw + indirect_capex_krw
    return {
        "table": table,
        "direct_capex_krw": direct_capex_krw,
        "indirect_capex_krw": indirect_capex_krw,
        "total_capex_krw": total_capex_krw,
        "krw_per_1998_usd": krw_per_1998_usd,
    }
