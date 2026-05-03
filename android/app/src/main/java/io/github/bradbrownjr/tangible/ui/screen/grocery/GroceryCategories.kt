package io.github.bradbrownjr.tangible.ui.screen.grocery

import androidx.annotation.StringRes
import io.github.bradbrownjr.tangible.R

internal data class GroceryCategoryPreset(val slug: String, @StringRes val labelRes: Int)

/** All grocery category presets, alphabetised by English label. Custom is handled separately. */
internal val GROCERY_CATEGORY_PRESETS: List<GroceryCategoryPreset> = listOf(
    GroceryCategoryPreset("alcohol",             R.string.cat_alcohol),
    GroceryCategoryPreset("bakery",              R.string.cat_bakery),
    GroceryCategoryPreset("beverages",           R.string.cat_beverages),
    GroceryCategoryPreset("bread",               R.string.cat_bread),
    GroceryCategoryPreset("breakfast-cereal",    R.string.cat_breakfast_cereal),
    GroceryCategoryPreset("canned-pantry",       R.string.cat_canned_pantry),
    GroceryCategoryPreset("cleaning-household",  R.string.cat_cleaning_household),
    GroceryCategoryPreset("condiments-spices",   R.string.cat_condiments_spices),
    GroceryCategoryPreset("dairy-eggs",          R.string.cat_dairy_eggs),
    GroceryCategoryPreset("deli",                R.string.cat_deli),
    GroceryCategoryPreset("frozen",              R.string.cat_frozen),
    GroceryCategoryPreset("health-beauty",       R.string.cat_health_beauty),
    GroceryCategoryPreset("meat-seafood",        R.string.cat_meat_seafood),
    GroceryCategoryPreset("pasta-grains",        R.string.cat_pasta_grains),
    GroceryCategoryPreset("pet-supplies",        R.string.cat_pet_supplies),
    GroceryCategoryPreset("produce",             R.string.cat_produce),
    GroceryCategoryPreset("snacks",              R.string.cat_snacks),
)

internal val PRESET_SLUGS: Set<String> = GROCERY_CATEGORY_PRESETS.map { it.slug }.toSet()
