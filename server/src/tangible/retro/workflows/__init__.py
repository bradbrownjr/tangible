"""Telnet workflow handlers for each operational area."""

from tangible.retro.workflows.circulation import circulation_menu
from tangible.retro.workflows.inventory import inventory_menu
from tangible.retro.workflows.locations import locations_menu
from tangible.retro.workflows.receiving import receiving_menu
from tangible.retro.workflows.reports import reports_menu
from tangible.retro.workflows.service import service_desk_menu
from tangible.retro.workflows.shopping import shopping_menu

__all__ = [
    "circulation_menu",
    "inventory_menu",
    "locations_menu",
    "receiving_menu",
    "reports_menu",
    "service_desk_menu",
    "shopping_menu",
]
