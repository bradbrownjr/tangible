package io.github.bradbrownjr.tangible.ui.screen.grocery

import androidx.annotation.StringRes
import io.github.bradbrownjr.tangible.R

internal data class ShoppingCategoryPreset(val slug: String, @StringRes val labelRes: Int)

/** Grocery category presets, alphabetised by English label. */
internal val SHOPPING_CATEGORY_PRESETS: List<ShoppingCategoryPreset> = listOf(
    ShoppingCategoryPreset("alcohol",             R.string.cat_alcohol),
    ShoppingCategoryPreset("bakery",              R.string.cat_bakery),
    ShoppingCategoryPreset("beverages",           R.string.cat_beverages),
    ShoppingCategoryPreset("bread",               R.string.cat_bread),
    ShoppingCategoryPreset("breakfast-cereal",    R.string.cat_breakfast_cereal),
    ShoppingCategoryPreset("canned-pantry",       R.string.cat_canned_pantry),
    ShoppingCategoryPreset("cleaning-household",  R.string.cat_cleaning_household),
    ShoppingCategoryPreset("condiments-spices",   R.string.cat_condiments_spices),
    ShoppingCategoryPreset("dairy-eggs",          R.string.cat_dairy_eggs),
    ShoppingCategoryPreset("deli",                R.string.cat_deli),
    ShoppingCategoryPreset("frozen",              R.string.cat_frozen),
    ShoppingCategoryPreset("health-beauty",       R.string.cat_health_beauty),
    ShoppingCategoryPreset("meat-seafood",        R.string.cat_meat_seafood),
    ShoppingCategoryPreset("pasta-grains",        R.string.cat_pasta_grains),
    ShoppingCategoryPreset("pet-supplies",        R.string.cat_pet_supplies),
    ShoppingCategoryPreset("produce",             R.string.cat_produce),
    ShoppingCategoryPreset("snacks",              R.string.cat_snacks),
)

/** Hardware store category presets, alphabetised by English label. */
internal val HARDWARE_CATEGORY_PRESETS: List<ShoppingCategoryPreset> = listOf(
    ShoppingCategoryPreset("adhesives-tape",         R.string.cat_hw_adhesives_tape),
    ShoppingCategoryPreset("caulk-sealant",          R.string.cat_hw_caulk_sealant),
    ShoppingCategoryPreset("concrete-masonry",       R.string.cat_hw_concrete_masonry),
    ShoppingCategoryPreset("electrical",             R.string.cat_hw_electrical),
    ShoppingCategoryPreset("fasteners",              R.string.cat_hw_fasteners),
    ShoppingCategoryPreset("flooring",               R.string.cat_hw_flooring),
    ShoppingCategoryPreset("hand-tools",             R.string.cat_hw_hand_tools),
    ShoppingCategoryPreset("hardware-hinges",        R.string.cat_hw_hardware_hinges),
    ShoppingCategoryPreset("hvac-filters",           R.string.cat_hw_hvac_filters),
    ShoppingCategoryPreset("lumber-sheet-goods",     R.string.cat_hw_lumber_sheet_goods),
    ShoppingCategoryPreset("paint-finishes",         R.string.cat_hw_paint_finishes),
    ShoppingCategoryPreset("plumbing",               R.string.cat_hw_plumbing),
    ShoppingCategoryPreset("power-tool-accessories", R.string.cat_hw_power_tool_accessories),
    ShoppingCategoryPreset("safety-ppe",             R.string.cat_hw_safety_ppe),
    ShoppingCategoryPreset("storage-organization",   R.string.cat_hw_storage_organization),
)

/** Home goods category presets, alphabetised by English label. */
internal val HOME_GOODS_CATEGORY_PRESETS: List<ShoppingCategoryPreset> = listOf(
    ShoppingCategoryPreset("bathroom",          R.string.cat_hg_bathroom),
    ShoppingCategoryPreset("bedding-pillows",   R.string.cat_hg_bedding_pillows),
    ShoppingCategoryPreset("candles-fragrance", R.string.cat_hg_candles_fragrance),
    ShoppingCategoryPreset("cleaning-supplies", R.string.cat_hg_cleaning_supplies),
    ShoppingCategoryPreset("cookware-bakeware", R.string.cat_hg_cookware_bakeware),
    ShoppingCategoryPreset("curtains-blinds",   R.string.cat_hg_curtains_blinds),
    ShoppingCategoryPreset("decor-accents",     R.string.cat_hg_decor_accents),
    ShoppingCategoryPreset("furniture",         R.string.cat_hg_furniture),
    ShoppingCategoryPreset("kitchen-gadgets",   R.string.cat_hg_kitchen_gadgets),
    ShoppingCategoryPreset("lighting",          R.string.cat_hg_lighting),
    ShoppingCategoryPreset("linens-towels",     R.string.cat_hg_linens_towels),
    ShoppingCategoryPreset("outdoor-garden",    R.string.cat_hg_outdoor_garden),
    ShoppingCategoryPreset("rugs-mats",         R.string.cat_hg_rugs_mats),
    ShoppingCategoryPreset("small-appliances",  R.string.cat_hg_small_appliances),
    ShoppingCategoryPreset("storage",           R.string.cat_hg_storage),
)

internal fun presetsForType(listType: String): List<ShoppingCategoryPreset> = when (listType) {
    "hardware"   -> HARDWARE_CATEGORY_PRESETS
    "home_goods" -> HOME_GOODS_CATEGORY_PRESETS
    else         -> SHOPPING_CATEGORY_PRESETS
}

internal val PRESET_SLUGS: Set<String> = SHOPPING_CATEGORY_PRESETS.map { it.slug }.toSet()
