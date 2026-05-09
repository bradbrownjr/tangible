# Scaffold Template Field Reference

This document lists every default template that Tangible seeds when you click
**Create ___ defaults** in the Templates panel. Templates are keyed to a
collection's root category (the first segment of `default_category_slug`).

Each template is pre-populated with the fields shown below. You can add,
remove, or rename fields at any time after creation — these are just starting
points. Fields marked **\*** are required when using the template.

---

## Music

Seeded for collections with root category `music`.

### Vinyl
`music.vinyl`

| Key | Label | Type |
|-----|-------|------|
| label | Label | text |
| catalog_no | Catalog # | text |
| pressing_year | Pressing year | number |
| matrix | Matrix / runout | text |

### Compact Disc
`music.cd`

| Key | Label | Type |
|-----|-------|------|
| label | Label | text |
| catalog_no | Catalog # | text |
| release_year | Release year | number |
| barcode | Barcode | text |

### Cassette
`music.cassette`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| label | Label | text | |
| year | Year | number | |
| tape_type | Tape type | select | Type I, Type II, Type IV |

### 8-Track
`music.eight_track`

| Key | Label | Type |
|-----|-------|------|
| label | Label | text |
| year | Year | number |

### Reel-to-Reel
`music.reel`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| label | Label | text | |
| year | Year | number | |
| speed | Speed (IPS) | select | 1⅞, 3¾, 7½, 15 |

---

## Movies

Seeded for collections with root category `movies`.

### Blu-ray / 4K UHD
`movies.bluray`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| studio | Studio | text | |
| release_year | Release year | number | |
| region | Region | select | A, B, C, Free |
| aspect_ratio | Aspect ratio | text | |

### DVD
`movies.dvd`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| studio | Studio | text | |
| release_year | Release year | number | |
| region | Region | select | 0, 1, 2, 3, 4, 5, 6 |

### VHS
`movies.vhs`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| studio | Studio | text | |
| year | Year | number | |
| format | Format | select | NTSC, PAL, SECAM |

---

## Books

Seeded for collections with root category `books`.

### Book
`books.print`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| publisher | Publisher | text | |
| year | Year | number | |
| edition | Edition | text | |
| format | Format | select | Hardcover, Paperback, Trade |
| isbn | ISBN | text | |

### Comic / Graphic Novel
`books.comic`

| Key | Label | Type |
|-----|-------|------|
| publisher | Publisher | text |
| issue_no | Issue # | text |
| year | Year | number |
| grade | Grade | text |

---

## Games

Seeded for collections with root category `games`.

### Game
`games.software`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| platform | Platform | text | |
| year | Year | number | |
| region | Region | select | NTSC, PAL, NTSC-J |
| rating | Rating | select | E, E10+, T, M, AO, RP |
| upc | UPC | text | |

### Console / Hardware
`games.console`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| manufacturer | Manufacturer | text | |
| model | Model # | text | |
| region | Region | select | NTSC, PAL, NTSC-J |

---

## Tabletop

Seeded for collections with root category `tabletop`.

### Board Game
`tabletop.board_game`

| Key | Label | Type |
|-----|-------|------|
| publisher | Publisher | text |
| year | Year | number |
| players | Players | text |
| bgg_id | BGG ID | text |

### RPG Book
`tabletop.rpg_book`

| Key | Label | Type |
|-----|-------|------|
| publisher | Publisher | text |
| year | Year | number |
| edition | Edition | text |

---

## Collectibles

Seeded for collections with root category `collectibles`.

### Trading Card
`collectibles.trading_card`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| set | Set | text | |
| card_number | Card # | text | |
| grade | Grade | text | |
| graded_by | Graded by | select | PSA, BGS, CGC, SGC, Raw |

### Action Figure / Funko
`collectibles.action_figure`

| Key | Label | Type |
|-----|-------|------|
| manufacturer | Manufacturer | text |
| year | Year | number |
| box_condition | Box condition | text |

---

## Home Equipment

Seeded for collections with root category `home_equipment`.

### Appliance
`home_equipment.appliance`

| Key | Label | Type | Notes |
|-----|-------|------|-------|
| brand **\*** | Brand | text | required |
| model **\*** | Model | text | required |
| serial_number | Serial number | text | |
| purchase_date | Purchase date | date | |
| purchase_price | Purchase price | number | |
| warranty_expiry | Warranty expiry | date | |
| room | Room / location | text | |
| last_service_date | Last service date | date | |
| service_interval_days | Service interval (days) | number | |

### Generator
`home_equipment.generator`

| Key | Label | Type | Options / Notes |
|-----|-------|------|-----------------|
| fuel_type | Fuel type | select | gasoline, propane, dual-fuel, diesel |
| tank_capacity_gal | Tank capacity (gal) | number | |
| last_run_date | Last run date | date | |
| run_interval_days | Run interval (days) | number | default: 30 |
| last_oil_change_date | Last oil change | date | |
| oil_type | Oil type | text | |

### HVAC / Furnace / Air Handler
`home_equipment.hvac`

| Key | Label | Type | Options / Notes |
|-----|-------|------|-----------------|
| system_type | System type | select | central_air, mini_split, boiler, heat_pump, furnace |
| filter_size | Filter size | text | |
| filter_merv | Filter MERV | text | |
| last_filter_change | Last filter change | date | |
| filter_change_interval_days | Filter interval (days) | number | default: 90 |
| last_professional_service | Last professional service | date | |

---

## Fuel & Chemicals

Seeded for collections with root category `fuel_chemicals`.

### Stored Fuel
`fuel_chemicals.stored_fuel`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| fuel_type | Fuel type | select | regular_gasoline, ethanol_free, premium, diesel, chainsaw_premix, propane, kerosene |
| container_capacity_gal | Container capacity (gal) | number | |
| quantity_on_hand_gal | Quantity on hand (gal) | number | |
| purchase_date | Purchase date | date | |
| stabilizer_added | Stabilizer added | boolean | |
| stabilizer_added_date | Stabilizer added date | date | |
| treat_by_date | Treat-by / expiry | date | |
| intended_equipment | Intended equipment | text | |

### Lubricants & Fluids
`fuel_chemicals.lubricants_fluids`

| Key | Label | Type | Notes |
|-----|-------|------|-------|
| fluid_type **\*** | Fluid type | text | required |
| grade | Viscosity/grade | text | |
| container_volume | Container volume | text | |
| quantity_on_hand | Quantity on hand | number | |
| purchase_date | Purchase date | date | |
| expiry | Expiry | date | |

### Chemicals & Cleaning
`fuel_chemicals.chemicals_cleaning`

| Key | Label | Type |
|-----|-------|------|
| purpose | Purpose | text |
| hazard_class | Hazard class | text |
| sds_url | SDS URL | url |
| purchase_date | Purchase date | date |
| expiry_date | Expiry date | date |

---

## Vehicles

Seeded for collections with root category `vehicles`.

### Car / Truck / SUV
`vehicles.car_truck_suv`

| Key | Label | Type | Notes |
|-----|-------|------|-------|
| year | Year | number | |
| make **\*** | Make | text | required |
| model **\*** | Model | text | required |
| vin | VIN | text | |
| odometer | Odometer | number | |
| fuel_type | Fuel type | text | |
| last_oil_change_date | Last oil change date | date | |
| last_oil_change_miles | Last oil change miles | number | |
| oil_change_interval_miles | Oil interval miles | number | default: 5000 |
| registration_expiry_date | Registration expiry | date | |
| insurance_expiry_date | Insurance expiry | date | |

### Motorcycle / ATV / UTV
`vehicles.motorcycle_atv_utv`

| Key | Label | Type | Notes |
|-----|-------|------|-------|
| make **\*** | Make | text | required |
| model **\*** | Model | text | required |
| vin | VIN | text | |
| last_chain_lubed | Last chain/belt lubed | date | |
| last_air_filter_replaced | Last air filter replaced | date | |

### Lawn & Garden Equipment
`vehicles.lawn_garden_equipment`

| Key | Label | Type | Notes |
|-----|-------|------|-------|
| equipment_type | Equipment type | text | |
| engine_spec | Engine cc/hp | text | |
| fuel_type | Fuel type | text | |
| last_oil_change_date | Last oil change date | date | |
| last_oil_change_hours | Last oil change hours | number | |
| oil_change_interval_hours | Oil interval hours | number | default: 50 |
| last_blade_sharpen | Last blade sharpen | date | |

### Boat / PWC
`vehicles.boat_pwc`

| Key | Label | Type | Options / Notes |
|-----|-------|------|-----------------|
| make **\*** | Make | text | required |
| model **\*** | Model | text | required |
| year | Year | number | |
| hull_id | Hull ID | text | |
| engine_type | Engine type | select | inboard, outboard, jet_ski, sailboat, pontoon |
| horsepower | Horsepower | number | |
| last_service_date | Last service date | date | |
| last_oil_change_hours | Last oil change hours | number | |
| winterization_date | Winterization date | date | |
| mooring_location | Mooring / storage location | text | |
| registration_expiry | Registration expiry | date | |
| insurance_expiry | Insurance expiry | date | |

### Trailer
`vehicles.trailer`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| make | Make | text | |
| model | Model | text | |
| year | Year | number | |
| vin | VIN | text | |
| trailer_type | Trailer type | select | utility, enclosed, horse, rv, boat, car, flatbed, gooseneck |
| tare_weight_lbs | Tare weight (lbs) | number | |
| capacity_lbs | Capacity (lbs) | number | |
| last_inspection_date | Last inspection date | date | |
| last_tire_replacement | Last tire replacement | date | |
| registration_expiry | Registration expiry | date | |
| insurance_expiry | Insurance expiry | date | |

### Bicycle / E-Bike
`vehicles.bicycle_ebike`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| make | Make | text | |
| model | Model | text | |
| bike_type | Bike type | select | road, mountain, hybrid, cruiser, gravel, ebike_pedal_assist, ebike_throttle |
| frame_size | Frame size | text | |
| frame_material | Frame material | select | steel, aluminum, carbon, titanium |
| wheel_size_inches | Wheel size (inches) | text | |
| last_tune_up_date | Last tune-up date | date | |
| last_chain_clean_lube | Last chain clean/lube | date | |
| last_brake_service | Last brake service | date | |
| ebike_battery_capacity_wh | Battery capacity (Wh) | number | |
| ebike_last_battery_service | Last battery service | date | |
| storage_location | Storage location | text | |

---

## Batteries

Seeded for collections with root category `batteries`.

### Rechargeable Battery
`batteries.rechargeable`

| Key | Label | Type | Options / Notes |
|-----|-------|------|-----------------|
| chemistry | Chemistry | select | NiMH, Li-ion, LiFePO4, LiPo, Pb-acid |
| form_factor | Form factor | select | AA, AAA, C, D, 9V, 18650, 21700, custom |
| capacity_mah | Capacity (mAh) | number | |
| voltage | Nominal voltage (V) | number | |
| quantity | Quantity | number | default: 1 |
| purchase_date | Purchase date | date | |
| charge_cycles | Charge cycles | number | |
| last_charge_date | Last charge date | date | |
| assigned_device | Assigned device | text | |

### Disposable Battery
`batteries.disposable`

| Key | Label | Type | Options / Notes |
|-----|-------|------|-----------------|
| chemistry | Chemistry | select | alkaline, lithium, zinc-carbon, silver_oxide |
| form_factor | Form factor | select | AA, AAA, C, D, 9V, button_cell |
| quantity_on_hand | Quantity on hand | number | default: 1 |
| purchase_date | Purchase date | date | |
| best_by_date | Best by / expiry | date | |
| assigned_devices | Assigned devices | text | |

### Smoke Detector Battery Program
`batteries.smoke_detector`

| Key | Label | Type | Options / Notes |
|-----|-------|------|-----------------|
| detector_type | Detector type | select | replaceable_10yr, sealed_10yr_lithium, replaceable_standard |
| battery_type | Battery type | text | |
| install_date | Install date | date | |
| replacement_due_date | Replacement due date | date | |
| detector_location | Detector location | text | |
| detector_manufacture_date | Detector manufacture date | date | |
| last_test_date | Last test date | date | |
| test_interval_months | Test interval (months) | number | default: 1 |

---

## Clothing

Seeded for collections with root category `clothing`.

### Clothing Item
`clothing.clothing_item`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| type | Type | select | shirt, pants, jacket, dress, suit, sweater, skirt, shorts |
| brand | Brand | text | |
| size | Size | text | |
| color | Color | text | |
| material | Material | text | |
| care_instructions | Care instructions | text | |
| purchase_date | Purchase date | date | |
| purchase_price | Purchase price | number | |
| condition | Condition | select | like_new, excellent, good, fair, needs_repair |
| season | Season | select | spring_summer, fall_winter, all_season |
| occasion | Occasion | select | casual, work, formal, athletic, other |
| last_worn_date | Last worn date | date | |

### Footwear
`clothing.footwear`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| type | Type | select | shoe, boot, sneaker, sandal, heel, flats, athletic |
| brand | Brand | text | |
| size | Size | text | |
| size_system | Size system | select | US, EU, UK, JP |
| color | Color | text | |
| material | Material | text | |
| width | Width | text | |
| sole_type | Sole type | text | |
| insole_last_replaced | Insole last replaced | date | |
| purchase_date | Purchase date | date | |
| condition | Condition | select | like_new, excellent, good, fair, needs_repair |

### Accessories
`clothing.accessories`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| type | Type | select | watch, handbag, belt, jewelry, hat, scarf, sunglasses |
| brand | Brand | text | |
| material | Material | text | |
| color | Color | text | |
| purchase_date | Purchase date | date | |
| purchase_price | Purchase price | number | |
| condition | Condition | select | like_new, excellent, good, fair, needs_repair |
| occasion | Occasion | select | casual, work, formal, evening, other |

---

## Art & Décor

Seeded for collections with root category `art_decor`.

### Artwork
`art_decor.artwork`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| type | Type | select | painting, print, sculpture, photograph, mixed_media, drawing, collage |
| artist | Artist | text | |
| title | Title | text | |
| medium | Medium | text | |
| height_inches | Height (inches) | number | |
| width_inches | Width (inches) | number | |
| depth_inches | Depth (inches) | number | |
| year_created | Year created | number | |
| provenance | Provenance | text | |
| has_coa | Certificate of authenticity | boolean | |
| estimated_value | Estimated value | number | |
| insured_value | Insured value | number | |
| last_appraisal_date | Last appraisal date | date | |

### Framed Print / Poster
`art_decor.framed_print`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| artist | Artist | text | |
| publisher | Publisher | text | |
| title | Title | text | |
| edition | Edition | text | |
| print_run | Print run | number | |
| frame_material | Frame material | text | |
| glass_type | Glass type | select | UV_protective, standard, acrylic |
| height_inches | Height (inches) | number | |
| width_inches | Width (inches) | number | |

### Decorative Object
`art_decor.decorative_object`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| type | Type | text | |
| material | Material | text | |
| origin | Origin / country | text | |
| era | Era / period | text | |
| estimated_value | Estimated value | number | |
| condition | Condition | select | excellent, good, fair, needs_restoration |
| notes | Notes | text | |

---

## Tools

Seeded for collections with root category `tools`.

### Hand Tool
`tools.hand`

| Key | Label | Type |
|-----|-------|------|
| brand | Brand | text |
| model | Model | text |
| size_spec | Size / spec | text |
| purchase_date | Purchase date | date |
| purchase_price | Purchase price | number |
| warranty_expiry | Warranty expiry | date |
| storage_location | Storage location | text |

### Power Tool
`tools.power`

| Key | Label | Type |
|-----|-------|------|
| brand | Brand | text |
| model | Model | text |
| serial_number | Serial number | text |
| voltage_amperage | Voltage / amperage | text |
| purchase_date | Purchase date | date |
| warranty_expiry | Warranty expiry | date |
| battery_system | Battery system | text |
| last_blade_bit_change | Last blade/bit change | date |
| last_service_date | Last service date | date |

### Shop Equipment
`tools.shop`

| Key | Label | Type |
|-----|-------|------|
| brand | Brand | text |
| model | Model | text |
| serial_number | Serial number | text |
| purchase_date | Purchase date | date |
| warranty_expiry | Warranty expiry | date |
| last_service_date | Last service date | date |
| service_interval_months | Service interval (months) | number |

---

## Pantry / Spices

Seeded for collections with root category `spices`.

### Spice
`spices.spice`

| Key | Label | Type | Options / Notes |
|-----|-------|------|-----------------|
| product_name **\*** | Product name | text | required |
| brand | Brand | text | |
| category | Category | select | spice, herb, seasoning_blend, extract |
| upc_barcode | UPC / barcode | text | |
| quantity_on_hand | Quantity on hand | number | |
| unit | Unit | select | oz, g, lb, kg, tsp, tbsp, cup, L, ml |
| purchase_date | Purchase date | date | |
| best_by_date | Best by / expiry | date | |
| bloom_date | Bloom date (last toasted) | date | |
| storage_location | Storage location | text | |

### Pantry Item
`spices.pantry`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| product_name **\*** | Product name | text | required |
| brand | Brand | text | |
| category | Category | select | dry_goods, canned, frozen, refrigerated, beverage |
| upc_barcode | UPC / barcode | text | |
| minimum_stock_qty | Minimum stock quantity | number | |
| quantity_on_hand | Quantity on hand | number | |
| unit | Unit | select | each, oz, g, lb, kg, cup, L, ml, can |
| purchase_date | Purchase date | date | |
| best_by_date | Best by / expiry | date | |
| storage_location | Storage location | select | pantry_shelf, freezer, fridge, cabinet, basement |

---

## Sports

Seeded for collections with root category `sports`.

### Fitness Equipment
`sports.fitness`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| type | Type | select | barbell, dumbbell, kettlebell, treadmill, stationary_bike, rower, elliptical, bench, rack |
| brand | Brand | text | |
| weight_spec | Weight / spec | text | |
| purchase_date | Purchase date | date | |
| condition | Condition | select | like_new, excellent, good, fair, needs_repair |
| last_maintenance_date | Last maintenance date | date | |

### Outdoor Gear
`sports.outdoor`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| type | Type | select | tent, sleeping_bag, backpack, kayak, canoe, raft, climbing_gear, hiking_boots |
| brand | Brand | text | |
| packed_weight | Packed weight (lbs) | number | |
| capacity | Capacity / rating | text | |
| purchase_date | Purchase date | date | |
| condition | Condition | select | like_new, excellent, good, fair, needs_repair |
| last_inspection_date | Last inspection date | date | |

### Sports Equipment
`sports.sports_equipment`

| Key | Label | Type | Options |
|-----|-------|------|---------|
| sport | Sport | select | baseball, basketball, football, soccer, tennis, golf, hockey, lacrosse, skateboarding, surfing |
| type | Type | text | |
| brand | Brand | text | |
| size_spec | Size / spec | text | |
| dominant_hand | Dominant hand | select | left, right, ambidextrous, N/A |
| purchase_date | Purchase date | date | |
| condition | Condition | select | like_new, excellent, good, fair, needs_repair |
| last_restring_date | Last restring / reshaft / regrip | date | |
