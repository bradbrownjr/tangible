"""ItemTemplate endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from tangible.auth.deps import (
    AuthContext,
    collection_role,
    require_user,
)
from tangible.db import get_session
from tangible.models import Collection, Item, ItemTemplate
from tangible.schemas import (
    ItemTemplateCreate,
    ItemTemplateRead,
    ItemTemplateUpdate,
    TemplateField,
)

router = APIRouter(tags=["item-templates"])

_EDITOR_ROLES = {"editor", "owner"}
_VIEWER_ROLES = {"viewer", "editor", "owner"}

# Seed templates offered per root category slug.
_SCAFFOLD: dict[str, list[dict]] = {
    "music": [
        {"name": "Vinyl", "category_slug": "music.vinyl", "fields": [
            {"key": "label", "label": "Label", "type": "text"},
            {"key": "catalog_no", "label": "Catalog #", "type": "text"},
            {"key": "pressing_year", "label": "Pressing year", "type": "number"},
            {"key": "matrix", "label": "Matrix / runout", "type": "text"},
        ]},
        {"name": "Compact Disc", "category_slug": "music.cd", "fields": [
            {"key": "label", "label": "Label", "type": "text"},
            {"key": "catalog_no", "label": "Catalog #", "type": "text"},
            {"key": "release_year", "label": "Release year", "type": "number"},
            {"key": "barcode", "label": "Barcode", "type": "text"},
        ]},
        {"name": "Cassette", "category_slug": "music.cassette", "fields": [
            {"key": "label", "label": "Label", "type": "text"},
            {"key": "year", "label": "Year", "type": "number"},
            {"key": "tape_type", "label": "Tape type", "type": "select",
             "options": ["Type I", "Type II", "Type IV"]},
        ]},
        {"name": "8-Track", "category_slug": "music.eight_track", "fields": [
            {"key": "label", "label": "Label", "type": "text"},
            {"key": "year", "label": "Year", "type": "number"},
        ]},
        {"name": "Reel-to-Reel", "category_slug": "music.reel", "fields": [
            {"key": "label", "label": "Label", "type": "text"},
            {"key": "year", "label": "Year", "type": "number"},
            {"key": "speed", "label": "Speed (IPS)", "type": "select",
             "options": ["1⅞", "3¾", "7½", "15"]},
        ]},
    ],
    "movies": [
        {"name": "Blu-ray / 4K UHD", "category_slug": "movies.bluray", "fields": [
            {"key": "studio", "label": "Studio", "type": "text"},
            {"key": "release_year", "label": "Release year", "type": "number"},
            {"key": "region", "label": "Region", "type": "select",
             "options": ["A", "B", "C", "Free"]},
            {"key": "aspect_ratio", "label": "Aspect ratio", "type": "text"},
        ]},
        {"name": "DVD", "category_slug": "movies.dvd", "fields": [
            {"key": "studio", "label": "Studio", "type": "text"},
            {"key": "release_year", "label": "Release year", "type": "number"},
            {"key": "region", "label": "Region", "type": "select",
             "options": ["0", "1", "2", "3", "4", "5", "6"]},
        ]},
        {"name": "VHS", "category_slug": "movies.vhs", "fields": [
            {"key": "studio", "label": "Studio", "type": "text"},
            {"key": "year", "label": "Year", "type": "number"},
            {"key": "format", "label": "Format", "type": "select",
             "options": ["NTSC", "PAL", "SECAM"]},
        ]},
    ],
    "books": [
        {"name": "Book", "category_slug": "books.print", "fields": [
            {"key": "publisher", "label": "Publisher", "type": "text"},
            {"key": "year", "label": "Year", "type": "number"},
            {"key": "edition", "label": "Edition", "type": "text"},
            {"key": "format", "label": "Format", "type": "select",
             "options": ["Hardcover", "Paperback", "Trade"]},
            {"key": "isbn", "label": "ISBN", "type": "text"},
        ]},
        {"name": "Comic / Graphic Novel", "category_slug": "books.comic", "fields": [
            {"key": "publisher", "label": "Publisher", "type": "text"},
            {"key": "issue_no", "label": "Issue #", "type": "text"},
            {"key": "year", "label": "Year", "type": "number"},
            {"key": "grade", "label": "Grade", "type": "text"},
        ]},
    ],
    "games": [
        {"name": "Game", "category_slug": "games.software", "fields": [
            {"key": "platform", "label": "Platform", "type": "text"},
            {"key": "year", "label": "Year", "type": "number"},
            {"key": "region", "label": "Region", "type": "select",
             "options": ["NTSC", "PAL", "NTSC-J"]},
            {"key": "rating", "label": "Rating", "type": "select",
             "options": ["E", "E10+", "T", "M", "AO", "RP"]},
            {"key": "upc", "label": "UPC", "type": "text"},
        ]},
        {"name": "Console / Hardware", "category_slug": "games.console", "fields": [
            {"key": "manufacturer", "label": "Manufacturer", "type": "text"},
            {"key": "model", "label": "Model #", "type": "text"},
            {"key": "region", "label": "Region", "type": "select",
             "options": ["NTSC", "PAL", "NTSC-J"]},
        ]},
    ],
    "tabletop": [
        {"name": "Board Game", "category_slug": "tabletop.board_game", "fields": [
            {"key": "publisher", "label": "Publisher", "type": "text"},
            {"key": "year", "label": "Year", "type": "number"},
            {"key": "players", "label": "Players", "type": "text"},
            {"key": "bgg_id", "label": "BGG ID", "type": "text"},
        ]},
        {"name": "RPG Book", "category_slug": "tabletop.rpg_book", "fields": [
            {"key": "publisher", "label": "Publisher", "type": "text"},
            {"key": "year", "label": "Year", "type": "number"},
            {"key": "edition", "label": "Edition", "type": "text"},
        ]},
    ],
    "collectibles": [
        {"name": "Trading Card", "category_slug": "collectibles.trading_card", "fields": [
            {"key": "set", "label": "Set", "type": "text"},
            {"key": "card_number", "label": "Card #", "type": "text"},
            {"key": "grade", "label": "Grade", "type": "text"},
            {"key": "graded_by", "label": "Graded by", "type": "select",
             "options": ["PSA", "BGS", "CGC", "SGC", "Raw"]},
        ]},
        {"name": "Action Figure / Funko", "category_slug": "collectibles.action_figure", "fields": [
            {"key": "manufacturer", "label": "Manufacturer", "type": "text"},
            {"key": "year", "label": "Year", "type": "number"},
            {"key": "box_condition", "label": "Box condition", "type": "text"},
        ]},
    ],
    "home_equipment": [
        {"name": "Appliance", "category_slug": "home_equipment.appliance", "fields": [
            {"key": "brand", "label": "Brand", "type": "text", "required": True},
            {"key": "model", "label": "Model", "type": "text", "required": True},
            {"key": "serial_number", "label": "Serial number", "type": "text"},
            {"key": "purchase_date", "label": "Purchase date", "type": "date"},
            {"key": "purchase_price", "label": "Purchase price", "type": "number"},
            {"key": "warranty_expiry", "label": "Warranty expiry", "type": "date"},
            {"key": "room", "label": "Room / location", "type": "text"},
            {"key": "last_service_date", "label": "Last service date", "type": "date"},
            {"key": "service_interval_days", "label": "Service interval (days)", "type": "number"},
        ]},
        {"name": "Generator", "category_slug": "home_equipment.generator", "fields": [
            {"key": "fuel_type", "label": "Fuel type", "type": "select", "options": ["gasoline", "propane", "dual-fuel", "diesel"]},
            {"key": "tank_capacity_gal", "label": "Tank capacity (gal)", "type": "number"},
            {"key": "last_run_date", "label": "Last run date", "type": "date"},
            {"key": "run_interval_days", "label": "Run interval (days)", "type": "number", "default": 30},
            {"key": "last_oil_change_date", "label": "Last oil change", "type": "date"},
            {"key": "oil_type", "label": "Oil type", "type": "text"},
        ]},
        {"name": "HVAC / Furnace / Air Handler", "category_slug": "home_equipment.hvac", "fields": [
            {"key": "system_type", "label": "System type", "type": "select", "options": ["central_air", "mini_split", "boiler", "heat_pump", "furnace"]},
            {"key": "filter_size", "label": "Filter size", "type": "text"},
            {"key": "filter_merv", "label": "Filter MERV", "type": "text"},
            {"key": "last_filter_change", "label": "Last filter change", "type": "date"},
            {"key": "filter_change_interval_days", "label": "Filter interval (days)", "type": "number", "default": 90},
            {"key": "last_professional_service", "label": "Last professional service", "type": "date"},
        ]},
    ],
    "fuel_chemicals": [
        {"name": "Stored Fuel", "category_slug": "fuel_chemicals.stored_fuel", "fields": [
            {"key": "fuel_type", "label": "Fuel type", "type": "select", "options": ["regular_gasoline", "ethanol_free", "premium", "diesel", "chainsaw_premix", "propane", "kerosene"]},
            {"key": "container_capacity_gal", "label": "Container capacity (gal)", "type": "number"},
            {"key": "quantity_on_hand_gal", "label": "Quantity on hand (gal)", "type": "number"},
            {"key": "purchase_date", "label": "Purchase date", "type": "date"},
            {"key": "stabilizer_added", "label": "Stabilizer added", "type": "boolean", "default": False},
            {"key": "stabilizer_added_date", "label": "Stabilizer added date", "type": "date"},
            {"key": "treat_by_date", "label": "Treat-by / expiry", "type": "date"},
            {"key": "intended_equipment", "label": "Intended equipment", "type": "text"},
        ]},
        {"name": "Lubricants & Fluids", "category_slug": "fuel_chemicals.lubricants_fluids", "fields": [
            {"key": "fluid_type", "label": "Fluid type", "type": "text", "required": True},
            {"key": "grade", "label": "Viscosity/grade", "type": "text"},
            {"key": "container_volume", "label": "Container volume", "type": "text"},
            {"key": "quantity_on_hand", "label": "Quantity on hand", "type": "number"},
            {"key": "purchase_date", "label": "Purchase date", "type": "date"},
            {"key": "expiry", "label": "Expiry", "type": "date"},
        ]},
        {"name": "Chemicals & Cleaning", "category_slug": "fuel_chemicals.chemicals_cleaning", "fields": [
            {"key": "purpose", "label": "Purpose", "type": "text"},
            {"key": "hazard_class", "label": "Hazard class", "type": "text"},
            {"key": "sds_url", "label": "SDS URL", "type": "url"},
            {"key": "purchase_date", "label": "Purchase date", "type": "date"},
            {"key": "expiry_date", "label": "Expiry date", "type": "date"},
        ]},
    ],
    "vehicles": [
        {"name": "Car / Truck / SUV", "category_slug": "vehicles.car_truck_suv", "fields": [
            {"key": "year", "label": "Year", "type": "number"},
            {"key": "make", "label": "Make", "type": "text", "required": True},
            {"key": "model", "label": "Model", "type": "text", "required": True},
            {"key": "vin", "label": "VIN", "type": "text"},
            {"key": "odometer", "label": "Odometer", "type": "number"},
            {"key": "fuel_type", "label": "Fuel type", "type": "text"},
            {"key": "last_oil_change_date", "label": "Last oil change date", "type": "date"},
            {"key": "last_oil_change_miles", "label": "Last oil change miles", "type": "number"},
            {"key": "oil_change_interval_miles", "label": "Oil interval miles", "type": "number", "default": 5000},
            {"key": "registration_expiry_date", "label": "Registration expiry", "type": "date"},
            {"key": "insurance_expiry_date", "label": "Insurance expiry", "type": "date"},
        ]},
        {"name": "Motorcycle / ATV / UTV", "category_slug": "vehicles.motorcycle_atv_utv", "fields": [
            {"key": "make", "label": "Make", "type": "text", "required": True},
            {"key": "model", "label": "Model", "type": "text", "required": True},
            {"key": "vin", "label": "VIN", "type": "text"},
            {"key": "last_chain_lubed", "label": "Last chain/belt lubed", "type": "date"},
            {"key": "last_air_filter_replaced", "label": "Last air filter replaced", "type": "date"},
        ]},
        {"name": "Lawn & Garden Equipment", "category_slug": "vehicles.lawn_garden_equipment", "fields": [
            {"key": "equipment_type", "label": "Equipment type", "type": "text"},
            {"key": "engine_spec", "label": "Engine cc/hp", "type": "text"},
            {"key": "fuel_type", "label": "Fuel type", "type": "text"},
            {"key": "last_oil_change_date", "label": "Last oil change date", "type": "date"},
            {"key": "last_oil_change_hours", "label": "Last oil change hours", "type": "number"},
            {"key": "oil_change_interval_hours", "label": "Oil interval hours", "type": "number", "default": 50},
            {"key": "last_blade_sharpen", "label": "Last blade sharpen", "type": "date"},
        ]},
        {"name": "Boat / PWC", "category_slug": "vehicles.boat_pwc", "fields": [
            {"key": "make", "label": "Make", "type": "text", "required": True},
            {"key": "model", "label": "Model", "type": "text", "required": True},
            {"key": "year", "label": "Year", "type": "number"},
            {"key": "hull_id", "label": "Hull ID", "type": "text"},
            {"key": "engine_type", "label": "Engine type", "type": "select", "options": ["inboard", "outboard", "jet_ski", "sailboat", "pontoon"]},
            {"key": "horsepower", "label": "Horsepower", "type": "number"},
            {"key": "last_service_date", "label": "Last service date", "type": "date"},
            {"key": "last_oil_change_hours", "label": "Last oil change hours", "type": "number"},
            {"key": "winterization_date", "label": "Winterization date", "type": "date"},
            {"key": "mooring_location", "label": "Mooring / storage location", "type": "text"},
            {"key": "registration_expiry", "label": "Registration expiry", "type": "date"},
            {"key": "insurance_expiry", "label": "Insurance expiry", "type": "date"},
        ]},
        {"name": "Trailer", "category_slug": "vehicles.trailer", "fields": [
            {"key": "make", "label": "Make", "type": "text"},
            {"key": "model", "label": "Model", "type": "text"},
            {"key": "year", "label": "Year", "type": "number"},
            {"key": "vin", "label": "VIN", "type": "text"},
            {"key": "trailer_type", "label": "Trailer type", "type": "select", "options": ["utility", "enclosed", "horse", "rv", "boat", "car", "flatbed", "gooseneck"]},
            {"key": "tare_weight_lbs", "label": "Tare weight (lbs)", "type": "number"},
            {"key": "capacity_lbs", "label": "Capacity (lbs)", "type": "number"},
            {"key": "last_inspection_date", "label": "Last inspection date", "type": "date"},
            {"key": "last_tire_replacement", "label": "Last tire replacement", "type": "date"},
            {"key": "registration_expiry", "label": "Registration expiry", "type": "date"},
            {"key": "insurance_expiry", "label": "Insurance expiry", "type": "date"},
        ]},
        {"name": "Bicycle / E-Bike", "category_slug": "vehicles.bicycle_ebike", "fields": [
            {"key": "make", "label": "Make", "type": "text"},
            {"key": "model", "label": "Model", "type": "text"},
            {"key": "bike_type", "label": "Bike type", "type": "select", "options": ["road", "mountain", "hybrid", "cruiser", "gravel", "ebike_pedal_assist", "ebike_throttle"]},
            {"key": "frame_size", "label": "Frame size", "type": "text"},
            {"key": "frame_material", "label": "Frame material", "type": "select", "options": ["steel", "aluminum", "carbon", "titanium"]},
            {"key": "wheel_size_inches", "label": "Wheel size (inches)", "type": "text"},
            {"key": "last_tune_up_date", "label": "Last tune-up date", "type": "date"},
            {"key": "last_chain_clean_lube", "label": "Last chain clean/lube", "type": "date"},
            {"key": "last_brake_service", "label": "Last brake service", "type": "date"},
            {"key": "ebike_battery_capacity_wh", "label": "Battery capacity (Wh)", "type": "number"},
            {"key": "ebike_last_battery_service", "label": "Last battery service", "type": "date"},
            {"key": "storage_location", "label": "Storage location", "type": "text"},
        ]},
    ],
    "batteries": [
        {"name": "Rechargeable Battery", "category_slug": "batteries.rechargeable", "fields": [
            {"key": "chemistry", "label": "Chemistry", "type": "select", "options": ["NiMH", "Li-ion", "LiFePO4", "LiPo", "Pb-acid"]},
            {"key": "form_factor", "label": "Form factor", "type": "select", "options": ["AA", "AAA", "C", "D", "9V", "18650", "21700", "custom"]},
            {"key": "capacity_mah", "label": "Capacity (mAh)", "type": "number"},
            {"key": "voltage", "label": "Nominal voltage (V)", "type": "number"},
            {"key": "quantity", "label": "Quantity", "type": "number", "default": 1},
            {"key": "purchase_date", "label": "Purchase date", "type": "date"},
            {"key": "charge_cycles", "label": "Charge cycles", "type": "number"},
            {"key": "last_charge_date", "label": "Last charge date", "type": "date"},
            {"key": "assigned_device", "label": "Assigned device", "type": "text"},
        ]},
        {"name": "Disposable Battery", "category_slug": "batteries.disposable", "fields": [
            {"key": "chemistry", "label": "Chemistry", "type": "select", "options": ["alkaline", "lithium", "zinc-carbon", "silver_oxide"]},
            {"key": "form_factor", "label": "Form factor", "type": "select", "options": ["AA", "AAA", "C", "D", "9V", "button_cell"]},
            {"key": "quantity_on_hand", "label": "Quantity on hand", "type": "number", "default": 1},
            {"key": "purchase_date", "label": "Purchase date", "type": "date"},
            {"key": "best_by_date", "label": "Best by / expiry", "type": "date"},
            {"key": "assigned_devices", "label": "Assigned devices", "type": "text"},
        ]},
        {"name": "Smoke Detector Battery Program", "category_slug": "batteries.smoke_detector", "fields": [
            {"key": "detector_type", "label": "Detector type", "type": "select", "options": ["replaceable_10yr", "sealed_10yr_lithium", "replaceable_standard"]},
            {"key": "battery_type", "label": "Battery type", "type": "text"},
            {"key": "install_date", "label": "Install date", "type": "date"},
            {"key": "replacement_due_date", "label": "Replacement due date", "type": "date"},
            {"key": "detector_location", "label": "Detector location", "type": "text"},
            {"key": "detector_manufacture_date", "label": "Detector manufacture date", "type": "date"},
            {"key": "last_test_date", "label": "Last test date", "type": "date"},
            {"key": "test_interval_months", "label": "Test interval (months)", "type": "number", "default": 1},
        ]},
    ],
    "clothing": [
        {"name": "Clothing Item", "category_slug": "clothing.clothing_item", "fields": [
            {"key": "type", "label": "Type", "type": "select", "options": ["shirt", "pants", "jacket", "dress", "suit", "sweater", "skirt", "shorts"]},
            {"key": "brand", "label": "Brand", "type": "text"},
            {"key": "size", "label": "Size", "type": "text"},
            {"key": "color", "label": "Color", "type": "text"},
            {"key": "material", "label": "Material", "type": "text"},
            {"key": "care_instructions", "label": "Care instructions", "type": "text"},
            {"key": "purchase_date", "label": "Purchase date", "type": "date"},
            {"key": "purchase_price", "label": "Purchase price", "type": "number"},
            {"key": "condition", "label": "Condition", "type": "select", "options": ["like_new", "excellent", "good", "fair", "needs_repair"]},
            {"key": "season", "label": "Season", "type": "select", "options": ["spring_summer", "fall_winter", "all_season"]},
            {"key": "occasion", "label": "Occasion", "type": "select", "options": ["casual", "work", "formal", "athletic", "other"]},
            {"key": "last_worn_date", "label": "Last worn date", "type": "date"},
        ]},
        {"name": "Footwear", "category_slug": "clothing.footwear", "fields": [
            {"key": "type", "label": "Type", "type": "select", "options": ["shoe", "boot", "sneaker", "sandal", "heel", "flats", "athletic"]},
            {"key": "brand", "label": "Brand", "type": "text"},
            {"key": "size", "label": "Size", "type": "text"},
            {"key": "size_system", "label": "Size system", "type": "select", "options": ["US", "EU", "UK", "JP"]},
            {"key": "color", "label": "Color", "type": "text"},
            {"key": "material", "label": "Material", "type": "text"},
            {"key": "width", "label": "Width", "type": "text"},
            {"key": "sole_type", "label": "Sole type", "type": "text"},
            {"key": "insole_last_replaced", "label": "Insole last replaced", "type": "date"},
            {"key": "purchase_date", "label": "Purchase date", "type": "date"},
            {"key": "condition", "label": "Condition", "type": "select", "options": ["like_new", "excellent", "good", "fair", "needs_repair"]},
        ]},
        {"name": "Accessories", "category_slug": "clothing.accessories", "fields": [
            {"key": "type", "label": "Type", "type": "select", "options": ["watch", "handbag", "belt", "jewelry", "hat", "scarf", "sunglasses"]},
            {"key": "brand", "label": "Brand", "type": "text"},
            {"key": "material", "label": "Material", "type": "text"},
            {"key": "color", "label": "Color", "type": "text"},
            {"key": "purchase_date", "label": "Purchase date", "type": "date"},
            {"key": "purchase_price", "label": "Purchase price", "type": "number"},
            {"key": "condition", "label": "Condition", "type": "select", "options": ["like_new", "excellent", "good", "fair", "needs_repair"]},
            {"key": "occasion", "label": "Occasion", "type": "select", "options": ["casual", "work", "formal", "evening", "other"]},
        ]},
    ],
    "art_decor": [
        {"name": "Artwork", "category_slug": "art_decor.artwork", "fields": [
            {"key": "type", "label": "Type", "type": "select", "options": ["painting", "print", "sculpture", "photograph", "mixed_media", "drawing", "collage"]},
            {"key": "artist", "label": "Artist", "type": "text"},
            {"key": "title", "label": "Title", "type": "text"},
            {"key": "medium", "label": "Medium", "type": "text"},
            {"key": "height_inches", "label": "Height (inches)", "type": "number"},
            {"key": "width_inches", "label": "Width (inches)", "type": "number"},
            {"key": "depth_inches", "label": "Depth (inches)", "type": "number"},
            {"key": "year_created", "label": "Year created", "type": "number"},
            {"key": "provenance", "label": "Provenance", "type": "text"},
            {"key": "has_coa", "label": "Certificate of authenticity", "type": "boolean"},
            {"key": "estimated_value", "label": "Estimated value", "type": "number"},
            {"key": "insured_value", "label": "Insured value", "type": "number"},
            {"key": "last_appraisal_date", "label": "Last appraisal date", "type": "date"},
        ]},
        {"name": "Framed Print / Poster", "category_slug": "art_decor.framed_print", "fields": [
            {"key": "artist", "label": "Artist", "type": "text"},
            {"key": "publisher", "label": "Publisher", "type": "text"},
            {"key": "title", "label": "Title", "type": "text"},
            {"key": "edition", "label": "Edition", "type": "text"},
            {"key": "print_run", "label": "Print run", "type": "number"},
            {"key": "frame_material", "label": "Frame material", "type": "text"},
            {"key": "glass_type", "label": "Glass type", "type": "select", "options": ["UV_protective", "standard", "acrylic"]},
            {"key": "height_inches", "label": "Height (inches)", "type": "number"},
            {"key": "width_inches", "label": "Width (inches)", "type": "number"},
        ]},
        {"name": "Decorative Object", "category_slug": "art_decor.decorative_object", "fields": [
            {"key": "type", "label": "Type", "type": "text"},
            {"key": "material", "label": "Material", "type": "text"},
            {"key": "origin", "label": "Origin / country", "type": "text"},
            {"key": "era", "label": "Era / period", "type": "text"},
            {"key": "estimated_value", "label": "Estimated value", "type": "number"},
            {"key": "condition", "label": "Condition", "type": "select", "options": ["excellent", "good", "fair", "needs_restoration"]},
            {"key": "notes", "label": "Notes", "type": "text"},
        ]},
    ],
    "tools": [
        {"name": "Hand Tool", "category_slug": "tools.hand", "fields": [
            {"key": "brand", "label": "Brand", "type": "text"},
            {"key": "model", "label": "Model", "type": "text"},
            {"key": "size_spec", "label": "Size / spec", "type": "text"},
            {"key": "purchase_date", "label": "Purchase date", "type": "date"},
            {"key": "purchase_price", "label": "Purchase price", "type": "number"},
            {"key": "warranty_expiry", "label": "Warranty expiry", "type": "date"},
            {"key": "storage_location", "label": "Storage location", "type": "text"},
        ]},
        {"name": "Power Tool", "category_slug": "tools.power", "fields": [
            {"key": "brand", "label": "Brand", "type": "text"},
            {"key": "model", "label": "Model", "type": "text"},
            {"key": "serial_number", "label": "Serial number", "type": "text"},
            {"key": "voltage_amperage", "label": "Voltage / amperage", "type": "text"},
            {"key": "purchase_date", "label": "Purchase date", "type": "date"},
            {"key": "warranty_expiry", "label": "Warranty expiry", "type": "date"},
            {"key": "battery_system", "label": "Battery system", "type": "text"},
            {"key": "last_blade_bit_change", "label": "Last blade/bit change", "type": "date"},
            {"key": "last_service_date", "label": "Last service date", "type": "date"},
        ]},
        {"name": "Shop Equipment", "category_slug": "tools.shop", "fields": [
            {"key": "brand", "label": "Brand", "type": "text"},
            {"key": "model", "label": "Model", "type": "text"},
            {"key": "serial_number", "label": "Serial number", "type": "text"},
            {"key": "purchase_date", "label": "Purchase date", "type": "date"},
            {"key": "warranty_expiry", "label": "Warranty expiry", "type": "date"},
            {"key": "last_service_date", "label": "Last service date", "type": "date"},
            {"key": "service_interval_months", "label": "Service interval (months)", "type": "number"},
        ]},
    ],
    "spices": [
        {"name": "Spice", "category_slug": "spices.spice", "fields": [
            {"key": "product_name", "label": "Product name", "type": "text", "required": True},
            {"key": "brand", "label": "Brand", "type": "text"},
            {"key": "category", "label": "Category", "type": "select", "options": ["spice", "herb", "seasoning_blend", "extract"]},
            {"key": "upc_barcode", "label": "UPC / barcode", "type": "text"},
            {"key": "quantity_on_hand", "label": "Quantity on hand", "type": "number"},
            {"key": "unit", "label": "Unit", "type": "select", "options": ["oz", "g", "lb", "kg", "tsp", "tbsp", "cup", "L", "ml"]},
            {"key": "purchase_date", "label": "Purchase date", "type": "date"},
            {"key": "best_by_date", "label": "Best by / expiry", "type": "date"},
            {"key": "bloom_date", "label": "Bloom date (last toasted)", "type": "date"},
            {"key": "storage_location", "label": "Storage location", "type": "text"},
        ]},
        {"name": "Pantry Item", "category_slug": "spices.pantry", "fields": [
            {"key": "product_name", "label": "Product name", "type": "text", "required": True},
            {"key": "brand", "label": "Brand", "type": "text"},
            {"key": "category", "label": "Category", "type": "select", "options": ["dry_goods", "canned", "frozen", "refrigerated", "beverage"]},
            {"key": "upc_barcode", "label": "UPC / barcode", "type": "text"},
            {"key": "minimum_stock_qty", "label": "Minimum stock quantity", "type": "number"},
            {"key": "quantity_on_hand", "label": "Quantity on hand", "type": "number"},
            {"key": "unit", "label": "Unit", "type": "select", "options": ["each", "oz", "g", "lb", "kg", "cup", "L", "ml", "can"]},
            {"key": "purchase_date", "label": "Purchase date", "type": "date"},
            {"key": "best_by_date", "label": "Best by / expiry", "type": "date"},
            {"key": "storage_location", "label": "Storage location", "type": "select", "options": ["pantry_shelf", "freezer", "fridge", "cabinet", "basement"]},
        ]},
    ],
    "sports": [
        {"name": "Fitness Equipment", "category_slug": "sports.fitness", "fields": [
            {"key": "type", "label": "Type", "type": "select", "options": ["barbell", "dumbbell", "kettlebell", "treadmill", "stationary_bike", "rower", "elliptical", "bench", "rack"]},
            {"key": "brand", "label": "Brand", "type": "text"},
            {"key": "weight_spec", "label": "Weight / spec", "type": "text"},
            {"key": "purchase_date", "label": "Purchase date", "type": "date"},
            {"key": "condition", "label": "Condition", "type": "select", "options": ["like_new", "excellent", "good", "fair", "needs_repair"]},
            {"key": "last_maintenance_date", "label": "Last maintenance date", "type": "date"},
        ]},
        {"name": "Outdoor Gear", "category_slug": "sports.outdoor", "fields": [
            {"key": "type", "label": "Type", "type": "select", "options": ["tent", "sleeping_bag", "backpack", "kayak", "canoe", "raft", "climbing_gear", "hiking_boots"]},
            {"key": "brand", "label": "Brand", "type": "text"},
            {"key": "packed_weight", "label": "Packed weight (lbs)", "type": "number"},
            {"key": "capacity", "label": "Capacity / rating", "type": "text"},
            {"key": "purchase_date", "label": "Purchase date", "type": "date"},
            {"key": "condition", "label": "Condition", "type": "select", "options": ["like_new", "excellent", "good", "fair", "needs_repair"]},
            {"key": "last_inspection_date", "label": "Last inspection date", "type": "date"},
        ]},
        {"name": "Sports Equipment", "category_slug": "sports.sports_equipment", "fields": [
            {"key": "sport", "label": "Sport", "type": "select", "options": ["baseball", "basketball", "football", "soccer", "tennis", "golf", "hockey", "lacrosse", "skateboarding", "surfing"]},
            {"key": "type", "label": "Type", "type": "text"},
            {"key": "brand", "label": "Brand", "type": "text"},
            {"key": "size_spec", "label": "Size / spec", "type": "text"},
            {"key": "dominant_hand", "label": "Dominant hand", "type": "select", "options": ["left", "right", "ambidextrous", "N/A"]},
            {"key": "purchase_date", "label": "Purchase date", "type": "date"},
            {"key": "condition", "label": "Condition", "type": "select", "options": ["like_new", "excellent", "good", "fair", "needs_repair"]},
            {"key": "last_restring_date", "label": "Last restring / reshaft / regrip", "type": "date"},
        ]},
    ],
}


def _require_role(
    db: DBSession, auth: AuthContext, collection_id: str, allowed: set[str]
) -> None:
    role = collection_role(db, auth.user, collection_id)
    if role is None or role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@router.get(
    "/collections/{collection_id}/templates",
    response_model=list[ItemTemplateRead],
)
def list_templates(
    collection_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ItemTemplateRead]:
    _require_role(db, auth, collection_id, _VIEWER_ROLES)
    rows = db.scalars(
        select(ItemTemplate)
        .where(ItemTemplate.collection_id == collection_id)
        .order_by(ItemTemplate.name)
    ).all()
    return [ItemTemplateRead.model_validate(r) for r in rows]


@router.post(
    "/collections/{collection_id}/templates",
    response_model=ItemTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
def create_template(
    collection_id: str,
    payload: ItemTemplateCreate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ItemTemplateRead:
    _require_role(db, auth, collection_id, _EDITOR_ROLES)
    tmpl = ItemTemplate(
        collection_id=collection_id,
        name=payload.name,
        category_slug=payload.category_slug,
        description=payload.description,
        fields=[f.model_dump() for f in payload.fields],
        created_by=auth.user.id,
    )
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return ItemTemplateRead.model_validate(tmpl)


@router.get("/templates/{template_id}", response_model=ItemTemplateRead)
def get_template(
    template_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ItemTemplateRead:
    tmpl = db.get(ItemTemplate, template_id)
    if tmpl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, tmpl.collection_id, _VIEWER_ROLES)
    return ItemTemplateRead.model_validate(tmpl)


@router.patch("/templates/{template_id}", response_model=ItemTemplateRead)
def update_template(
    template_id: str,
    payload: ItemTemplateUpdate,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ItemTemplateRead:
    tmpl = db.get(ItemTemplate, template_id)
    if tmpl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, tmpl.collection_id, _EDITOR_ROLES)
    data = payload.model_dump(exclude_unset=True)
    if "fields" in data and data["fields"] is not None:
        data["fields"] = [f if isinstance(f, dict) else f.model_dump() for f in data["fields"]]
    for k, v in data.items():
        setattr(tmpl, k, v)
    db.commit()
    db.refresh(tmpl)
    return ItemTemplateRead.model_validate(tmpl)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> None:
    tmpl = db.get(ItemTemplate, template_id)
    if tmpl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, tmpl.collection_id, _EDITOR_ROLES)
    db.delete(tmpl)
    db.commit()


@router.post(
    "/templates/{template_id}/clone",
    response_model=ItemTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
def clone_template(
    template_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> ItemTemplateRead:
    """Duplicate a template within the same collection."""
    tmpl = db.get(ItemTemplate, template_id)
    if tmpl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    _require_role(db, auth, tmpl.collection_id, _EDITOR_ROLES)
    clone = ItemTemplate(
        collection_id=tmpl.collection_id,
        name=f"{tmpl.name} (copy)",
        category_slug=tmpl.category_slug,
        description=tmpl.description,
        fields=list(tmpl.fields),
        created_by=auth.user.id,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return ItemTemplateRead.model_validate(clone)


# ---------------------------------------------------------------------------
# Scaffold helper (also called by create_collection)
# ---------------------------------------------------------------------------


def _do_scaffold(
    db: DBSession,
    collection_id: str,
    default_category_slug: str | None,
    created_by: str,
) -> None:
    """Seed default templates for *collection_id*.

    Idempotent: skips names that already exist. Does NOT commit — caller is
    responsible for committing the surrounding transaction.
    """
    root = (default_category_slug or "").split(".")[0]
    seeds = _SCAFFOLD.get(root, [])
    if not seeds:
        return

    existing_names = set(
        db.scalars(
            select(ItemTemplate.name).where(ItemTemplate.collection_id == collection_id)
        ).all()
    )

    for seed in seeds:
        if seed["name"] in existing_names:
            continue
        db.add(ItemTemplate(
            collection_id=collection_id,
            name=seed["name"],
            category_slug=seed["category_slug"],
            fields=seed["fields"],
            created_by=created_by,
        ))


@router.get(
    "/collections/{collection_id}/scaffold-templates",
    response_model=list[str],
)
def scaffold_template_names(
    collection_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[str]:
    """Return the names of default templates available for this collection's type."""
    _require_role(db, auth, collection_id, _VIEWER_ROLES)
    coll = db.get(Collection, collection_id)
    if coll is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    root = (coll.default_category_slug or "").split(".")[0]
    return [s["name"] for s in _SCAFFOLD.get(root, [])]


@router.get(
    "/collections/{collection_id}/scaffold-templates/preview",
    response_model=list[dict],
)
def scaffold_template_preview(
    collection_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[dict]:
    """Return the full scaffold template definitions (name + fields) for this collection's type."""
    _require_role(db, auth, collection_id, _VIEWER_ROLES)
    coll = db.get(Collection, collection_id)
    if coll is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    root = (coll.default_category_slug or "").split(".")[0]
    return [{"name": s["name"], "category_slug": s["category_slug"], "fields": s["fields"]}
            for s in _SCAFFOLD.get(root, [])]


@router.post(
    "/collections/{collection_id}/scaffold-templates",
    response_model=list[ItemTemplateRead],
    status_code=status.HTTP_201_CREATED,
)
def scaffold_templates(
    collection_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[ItemTemplateRead]:
    """Create sensible default templates for the collection's root category.

    Skips any template whose name already exists in the collection, so the
    endpoint is safe to call multiple times.
    """
    _require_role(db, auth, collection_id, _EDITOR_ROLES)
    coll = db.get(Collection, collection_id)
    if coll is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    _do_scaffold(db, collection_id, coll.default_category_slug, auth.user.id)
    db.commit()

    rows = db.scalars(
        select(ItemTemplate)
        .where(ItemTemplate.collection_id == collection_id)
        .order_by(ItemTemplate.name)
    ).all()
    return [ItemTemplateRead.model_validate(t) for t in rows]


@router.get(
    "/collections/{collection_id}/template-field-options/{field_key}",
    response_model=list[str],
)
def template_field_options(
    collection_id: str,
    field_key: str,
    template_id: str,
    db: DBSession = Depends(get_session),
    auth: AuthContext = Depends(require_user),
) -> list[str]:
    """Return dropdown options for a template select field.

    - Static fields return their declared options.
    - Dynamic fields return distinct values already used in item attrs.
    """
    _require_role(db, auth, collection_id, _VIEWER_ROLES)
    tmpl = db.get(ItemTemplate, template_id)
    if tmpl is None or tmpl.collection_id != collection_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    fields = [TemplateField.model_validate(f) for f in tmpl.fields]
    spec = next((f for f in fields if f.key == field_key), None)
    if spec is None or spec.type != "select":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Field is not a select field in this template",
        )

    if spec.select_source == "static":
        return list(spec.options or [])

    attr_rows = db.scalars(select(Item.attrs).where(Item.collection_id == collection_id)).all()
    seen: set[str] = set()
    for attrs in attr_rows:
        if not isinstance(attrs, dict):
            continue
        raw = attrs.get(field_key)
        if raw is None:
            continue
        sval = str(raw).strip()
        if sval:
            seen.add(sval)
    return sorted(seen, key=str.casefold)


# ---------------------------------------------------------------------------
# Validation helpers (used by items API)
# ---------------------------------------------------------------------------


def validate_attrs(
    db: DBSession,
    template: ItemTemplate,
    attrs: dict[str, Any],
    *,
    collection_id: str,
) -> dict[str, Any]:
    """Validate ``attrs`` against ``template.fields``.

    Returns the (possibly coerced) attrs dict; raises HTTPException on error.
    Unknown keys are preserved as-is so callers can carry forward legacy data.
    """
    out: dict[str, Any] = dict(attrs)
    field_specs: list[TemplateField] = [TemplateField.model_validate(f) for f in template.fields]
    for spec in field_specs:
        value = out.get(spec.key)
        if value is None or value == "":
            if spec.required:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Field '{spec.key}' is required",
                )
            if spec.default is not None and spec.key not in out:
                out[spec.key] = spec.default
            continue
        out[spec.key] = _coerce(db, spec, value, collection_id=collection_id)
    return out


def _coerce(db: DBSession, spec: TemplateField, value: Any, *, collection_id: str) -> Any:
    t = spec.type
    try:
        if t == "text" or t == "url":
            return str(value)
        if t == "number":
            return float(value)
        if t == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in {"1", "true", "yes", "on"}
            return bool(value)
        if t == "date":
            if isinstance(value, datetime):
                return value.isoformat()
            return str(value)
        if t == "multi_value":
            if isinstance(value, (list, tuple)):
                return [str(v).strip() for v in value if str(v).strip()]
            if isinstance(value, str):
                # Accept comma-delimited text for compatibility with simple clients.
                return [v.strip() for v in value.split(",") if v.strip()]
            raise ValueError("must be an array of values or a comma-separated string")
        if t == "select":
            sval = str(value)
            if spec.select_source == "static" and spec.options and sval not in spec.options:
                raise ValueError(
                    f"value '{sval}' not in allowed options for '{spec.key}'"
                )
            return sval
        if t == "relation":
            target_id = str(value).strip()
            if not target_id:
                raise ValueError("must reference an item id")
            target = db.get(Item, target_id)
            if target is None:
                raise ValueError("target item not found")
            if spec.relation_scope == "same_collection" and target.collection_id != collection_id:
                raise ValueError("target item must be in the same collection")
            return target_id
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Field '{spec.key}': {exc}",
        ) from exc
    return value
