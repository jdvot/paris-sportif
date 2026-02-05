"""Shared constants for the application.

Centralized definitions to avoid duplication across modules.
"""

from typing import TypedDict


class CompetitionInfo(TypedDict):
    """Competition information structure."""

    code: str
    name: str
    country: str
    flag: str


# Main competitions supported by the application
# This is the single source of truth for competition data
COMPETITIONS: list[CompetitionInfo] = [
    {"code": "PL", "name": "Premier League", "country": "England", "flag": "gb-eng"},
    {"code": "PD", "name": "La Liga", "country": "Spain", "flag": "es"},
    {"code": "BL1", "name": "Bundesliga", "country": "Germany", "flag": "de"},
    {"code": "SA", "name": "Serie A", "country": "Italy", "flag": "it"},
    {"code": "FL1", "name": "Ligue 1", "country": "France", "flag": "fr"},
    {"code": "CL", "name": "Champions League", "country": "Europe", "flag": "eu"},
    {"code": "EL", "name": "Europa League", "country": "Europe", "flag": "eu"},
]

# Code to name mapping for quick lookup
COMPETITION_NAMES: dict[str, str] = {comp["code"]: comp["name"] for comp in COMPETITIONS}

# Code to full info mapping
COMPETITION_MAP: dict[str, CompetitionInfo] = {comp["code"]: comp for comp in COMPETITIONS}
