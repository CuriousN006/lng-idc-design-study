from __future__ import annotations

import pandas as pd


def annualize_power_kw(power_kw: float, operating_hours_per_year: float) -> float:
    return power_kw * operating_hours_per_year / 1000.0


def annual_cost_krw(power_kw: float, operating_hours_per_year: float, electricity_unit_cost_krw_per_kwh: float) -> float:
    return power_kw * operating_hours_per_year * electricity_unit_cost_krw_per_kwh


def annual_emissions_tco2(power_kw: float, operating_hours_per_year: float, grid_emission_factor_tco2_per_mwh: float) -> float:
    return annualize_power_kw(power_kw, operating_hours_per_year) * grid_emission_factor_tco2_per_mwh


def compute_annual_metrics(config: dict, baseline_power_kw: float, lng_power_kw: float) -> dict[str, object]:
    economic_inputs = config["economic_inputs"]
    operating_hours = economic_inputs["operating_hours_per_year"]
    electricity_rate = economic_inputs["electricity_unit_cost_krw_per_kwh"]
    emission_factor = economic_inputs["grid_emission_factor_tco2_per_mwh"]

    baseline_energy_mwh = annualize_power_kw(baseline_power_kw, operating_hours)
    lng_energy_mwh = annualize_power_kw(lng_power_kw, operating_hours)
    energy_saving_mwh = baseline_energy_mwh - lng_energy_mwh

    baseline_cost_krw = annual_cost_krw(baseline_power_kw, operating_hours, electricity_rate)
    lng_cost_krw = annual_cost_krw(lng_power_kw, operating_hours, electricity_rate)
    cost_saving_krw = baseline_cost_krw - lng_cost_krw

    baseline_emissions_tco2 = annual_emissions_tco2(baseline_power_kw, operating_hours, emission_factor)
    lng_emissions_tco2 = annual_emissions_tco2(lng_power_kw, operating_hours, emission_factor)
    avoided_emissions_tco2 = baseline_emissions_tco2 - lng_emissions_tco2

    payback_rows = []
    for payback_year in economic_inputs["simple_payback_years"]:
        payback_rows.append(
            {
                "payback_years": int(payback_year),
                "allowable_incremental_capex_krw": cost_saving_krw * float(payback_year),
            }
        )

    return {
        "operating_hours_per_year": operating_hours,
        "electricity_unit_cost_krw_per_kwh": electricity_rate,
        "grid_emission_factor_tco2_per_mwh": emission_factor,
        "baseline_energy_mwh_per_year": baseline_energy_mwh,
        "lng_energy_mwh_per_year": lng_energy_mwh,
        "energy_saving_mwh_per_year": energy_saving_mwh,
        "baseline_cost_krw_per_year": baseline_cost_krw,
        "lng_cost_krw_per_year": lng_cost_krw,
        "cost_saving_krw_per_year": cost_saving_krw,
        "baseline_emissions_tco2_per_year": baseline_emissions_tco2,
        "lng_emissions_tco2_per_year": lng_emissions_tco2,
        "avoided_emissions_tco2_per_year": avoided_emissions_tco2,
        "payback_table": pd.DataFrame(payback_rows),
    }


def add_annualized_columns(frame: pd.DataFrame, power_column: str, baseline_power_kw: float, config: dict) -> pd.DataFrame:
    economic_inputs = config["economic_inputs"]
    operating_hours = economic_inputs["operating_hours_per_year"]
    electricity_rate = economic_inputs["electricity_unit_cost_krw_per_kwh"]
    emission_factor = economic_inputs["grid_emission_factor_tco2_per_mwh"]

    output = frame.copy()
    output["annual_energy_mwh"] = output[power_column] * operating_hours / 1000.0
    output["annual_cost_krw"] = output[power_column] * operating_hours * electricity_rate
    output["annual_emissions_tco2"] = output[power_column] * operating_hours / 1000.0 * emission_factor
    output["annual_cost_saving_krw"] = annual_cost_krw(baseline_power_kw, operating_hours, electricity_rate) - output["annual_cost_krw"]
    output["annual_avoided_emissions_tco2"] = annual_emissions_tco2(baseline_power_kw, operating_hours, emission_factor) - output["annual_emissions_tco2"]
    return output
