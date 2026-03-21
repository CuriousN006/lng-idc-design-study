from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LngMixtureDefinition:
    label: str
    coolprop_string: str
    normalized_components: dict[str, float]


def build_lng_mixture_definition(config: dict) -> LngMixtureDefinition:
    mixture_cfg = config.get("lng_mixture", {})
    backend = str(mixture_cfg.get("backend", "HEOS"))
    label = str(mixture_cfg.get("label", "Configured LNG surrogate"))
    components = {
        str(name): float(value)
        for name, value in mixture_cfg.get("component_mole_percent", {}).items()
        if float(value) > 0.0
    }
    if not components:
        raise RuntimeError("No LNG mixture components were configured.")

    total_percent = sum(components.values())
    if total_percent <= 0.0:
        raise RuntimeError("Configured LNG mixture composition must have a positive total mole fraction.")

    normalized = {
        name: value / total_percent
        for name, value in components.items()
    }
    mixture_string = backend + "::" + "&".join(
        f"{name}[{fraction:.12f}]"
        for name, fraction in normalized.items()
    )
    return LngMixtureDefinition(
        label=label,
        coolprop_string=mixture_string,
        normalized_components=normalized,
    )
