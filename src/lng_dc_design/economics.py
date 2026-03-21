from __future__ import annotations

import math

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


def _npv(discount_rate: float, cashflows: list[float]) -> float:
    return sum(cashflow / (1.0 + discount_rate) ** period for period, cashflow in enumerate(cashflows))


def _irr(cashflows: list[float]) -> float:
    if len(cashflows) < 2 or max(cashflows[1:], default=0.0) <= 0.0:
        return math.nan

    low = -0.99
    high = 0.10
    low_value = _npv(low, cashflows)
    high_value = _npv(high, cashflows)
    while high_value > 0.0 and high < 10.0:
        high *= 2.0
        high_value = _npv(high, cashflows)
    if low_value * high_value > 0.0:
        return math.nan

    for _ in range(80):
        mid = 0.5 * (low + high)
        mid_value = _npv(mid, cashflows)
        if abs(mid_value) < 1e-6:
            return mid
        if low_value * mid_value <= 0.0:
            high = mid
            high_value = mid_value
        else:
            low = mid
            low_value = mid_value
    return 0.5 * (low + high)


def compute_financial_metrics(config: dict, total_capex_krw: float, annual_cost_saving_krw: float) -> dict[str, float]:
    financial = config["economic_inputs"]["financial"]
    project_life_years = int(financial["project_life_years"])
    discount_rate_fraction = float(financial["discount_rate_fraction"])
    annual_om_fraction_of_capex = float(financial["annual_om_fraction_of_capex"])
    salvage_fraction_of_capex = float(financial["salvage_fraction_of_capex"])

    annual_om_cost_krw = total_capex_krw * annual_om_fraction_of_capex
    net_annual_cashflow_krw = annual_cost_saving_krw - annual_om_cost_krw
    cashflows = [-total_capex_krw] + [net_annual_cashflow_krw] * project_life_years
    cashflows[-1] += total_capex_krw * salvage_fraction_of_capex
    npv_krw = _npv(discount_rate_fraction, cashflows)
    irr_fraction = _irr(cashflows)

    simple_payback_years = math.nan
    if net_annual_cashflow_krw > 1e-9:
        simple_payback_years = total_capex_krw / net_annual_cashflow_krw

    discounted_payback_years = math.nan
    cumulative = -total_capex_krw
    for year in range(1, project_life_years + 1):
        discounted_cashflow = net_annual_cashflow_krw / (1.0 + discount_rate_fraction) ** year
        if year == project_life_years and salvage_fraction_of_capex > 0.0:
            discounted_cashflow += total_capex_krw * salvage_fraction_of_capex / (1.0 + discount_rate_fraction) ** year
        previous_cumulative = cumulative
        cumulative += discounted_cashflow
        if cumulative >= 0.0:
            recovery = -previous_cumulative / max(discounted_cashflow, 1e-9)
            discounted_payback_years = (year - 1) + recovery
            break

    return {
        "project_life_years": float(project_life_years),
        "discount_rate_fraction": discount_rate_fraction,
        "annual_om_cost_krw_per_year": annual_om_cost_krw,
        "net_annual_cashflow_krw_per_year": net_annual_cashflow_krw,
        "simple_payback_years": simple_payback_years,
        "discounted_payback_years": discounted_payback_years,
        "npv_krw": npv_krw,
        "irr_fraction": irr_fraction,
    }
