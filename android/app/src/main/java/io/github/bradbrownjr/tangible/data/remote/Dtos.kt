package io.github.bradbrownjr.tangible.data.remote

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class LoginRequest(val username: String, val password: String)

@JsonClass(generateAdapter = true)
data class TokenInfo(
    val id: String,
    val name: String,
    val token: String? = null,
    val last_used_at: String? = null,
    val expires_at: String? = null,
    val created_at: String,
)

@JsonClass(generateAdapter = true)
data class UserDto(
    val id: String,
    val username: String,
    val email: String? = null,
    val display_name: String? = null,
    val is_admin: Boolean = false,
    val locale: String? = null,
)

@JsonClass(generateAdapter = true)
data class PatchMeRequest(
    val locale: String? = null,
)

@JsonClass(generateAdapter = true)
data class SessionInfoDto(val user: UserDto, val expires_at: String)

@JsonClass(generateAdapter = true)
data class CollectionDto(
    val id: String,
    val name: String,
    val description: String? = null,
    val icon: String? = null,
    val is_public: Boolean = false,
    val owner_id: String,
    val default_category_slug: String? = null,
    val my_role: String? = null,
)

@JsonClass(generateAdapter = true)
data class CollectionPatch(
    val name: String? = null,
    val description: String? = null,
)

@JsonClass(generateAdapter = true)
data class CollectionCreate(
    val name: String,
    val description: String? = null,
    val default_category_slug: String? = null,
)

@JsonClass(generateAdapter = true)
data class CategoryDto(
    val id: String,
    val parent_id: String? = null,
    val slug: String,
    val name: String,
    val description: String? = null,
    val position: Int = 0,
)

@JsonClass(generateAdapter = true)
data class TagDto(
    val id: String,
    val name: String,
    val color: String? = null,
)

@JsonClass(generateAdapter = true)
data class ContactDto(
    val id: String,
    val owner_id: String,
    val name: String,
    val email: String? = null,
    val phone: String? = null,
    val notes: String? = null,
)

@JsonClass(generateAdapter = true)
data class LoanDto(
    val id: String,
    val item_id: String,
    val contact_id: String,
    val loaned_at: String,
    val due_at: String? = null,
    val returned_at: String? = null,
    val notes: String? = null,
)

@JsonClass(generateAdapter = true)
data class ScrapeResponse(
    val title: String? = null,
    val description: String? = null,
    val category: String? = null,
)

@JsonClass(generateAdapter = true)
data class ScrapeRequest(val url: String)

@JsonClass(generateAdapter = true)
data class BarcodeLookupRequest(val barcode: String)

@JsonClass(generateAdapter = true)
data class BarcodeCandidateDto(
    val provider: String,
    val url: String,
    val title: String? = null,
    val description: String? = null,
    val image_url: String? = null,
    val category: String? = null,
    val attrs: Map<String, @JvmSuppressWildcards Any?> = emptyMap(),
)

@JsonClass(generateAdapter = true)
data class BarcodeLookupResponse(val candidates: List<BarcodeCandidateDto>)

@JsonClass(generateAdapter = true)
data class ItemDto(
    val id: String,
    val collection_id: String,
    val category_id: String,
    val category_slug: String? = null,
    val primary_photo_id: String? = null,
    val title: String,
    val subtitle: String? = null,
    val notes: String? = null,
    val condition: String? = null,
    val quantity: Int = 1,
    val purchase_price: Double? = null,
    val current_value: Double? = null,
    val rollup_current_value: Double? = null,
    val currency: String? = null,
    val location_id: String? = null,
    val location_path: List<String>? = null,
    val identifiers: Map<String, Any?> = emptyMap(),
    val attrs: Map<String, Any?> = emptyMap(),
    val depleted: Boolean = false,
    val wanted: Boolean = false,
    val archived_at: String? = null,
    val purchased_at: String? = null,
    val use_by_date: String? = null,
    val date_frozen: String? = null,
    val date_opened: String? = null,
)

@JsonClass(generateAdapter = true)
data class ItemCreate(
    val collection_id: String,
    val category: String,       // leaf slug, e.g. "music.vinyl"
    val title: String,
    val subtitle: String? = null,
    val notes: String? = null,
    val identifiers: Map<String, String> = emptyMap(),
)

@JsonClass(generateAdapter = true)
data class ItemPatch(
    val title: String? = null,
    val subtitle: String? = null,
    val notes: String? = null,
    val condition: String? = null,
    val quantity: Int? = null,
    val purchase_price: Double? = null,
    val current_value: Double? = null,
    val currency: String? = null,
    val location_id: String? = null,
    val depleted: Boolean? = null,
    val wanted: Boolean? = null,
)

@JsonClass(generateAdapter = true)
data class ItemBulkPatchRequest(
    val collection_id: String,
    val item_ids: List<String>,
    val depleted: Boolean? = null,
    val wanted: Boolean? = null,
    val location_id: String? = null,
)

@JsonClass(generateAdapter = true)
data class ItemBulkTagRequest(
    val collection_id: String,
    val item_ids: List<String>,
    val tag_ids: List<String>,
    val mode: String = "add",
)

@JsonClass(generateAdapter = true)
data class ItemBulkLendRequest(
    val collection_id: String,
    val item_ids: List<String>,
    val contact_id: String,
    val due_at: String? = null,
)

@JsonClass(generateAdapter = true)
data class ItemBulkArchiveRequest(
    val collection_id: String,
    val item_ids: List<String>,
    val disposition_type: String = "archived",
)

@JsonClass(generateAdapter = true)
data class ItemBulkRestoreRequest(
    val collection_id: String,
    val item_ids: List<String>,
)

@JsonClass(generateAdapter = true)
data class ItemBulkDeleteRequest(
    val collection_id: String,
    val item_ids: List<String>,
)

@JsonClass(generateAdapter = true)
data class ItemBulkDeleteResponse(
    val deleted: Int,
)

@JsonClass(generateAdapter = true)
data class RestockRequest(
    val label: String? = null,
    val notes: String? = null,
    val quantity: Int = 1,
    val purchased_at: String? = null,
    val use_by_date: String? = null,
    val date_frozen: String? = null,
    val date_opened: String? = null,
    val mark_in_stock: Boolean = true,
)

@JsonClass(generateAdapter = true)
data class ItemLotDto(
    val id: String,
    val item_id: String,
    val collection_id: String,
    val quantity: Int,
    val is_active: Boolean,
)

@JsonClass(generateAdapter = true)
data class PhotoDto(
    val id: String,
    val item_id: String,
    val sha256: String,
    val mime_type: String,
    val width: Int? = null,
    val height: Int? = null,
    val byte_size: Int,
    val sort_order: Int,
    val is_primary: Boolean,
    val created_at: String,
)

@JsonClass(generateAdapter = true)
data class DueAlertDto(
    val id: String,
    val kind: String,
    val severity: String,
    val title: String,
    val collection_id: String,
    val item_id: String? = null,
    val lot_id: String? = null,
    val due_at: String? = null,
    val details: String? = null,
)

@JsonClass(generateAdapter = true)
data class LocationDto(
    val id: String,
    val collection_id: String,
    val parent_id: String? = null,
    val name: String,
    val kind: String = "container",
    val notes: String? = null,
    val qr_slug: String? = null,
    val item_count: Int = 0,
    val children: List<LocationDto> = emptyList(),
)

@JsonClass(generateAdapter = true)
data class LocationCreate(
    val collection_id: String,
    val name: String,
    val kind: String = "container",
    val parent_id: String? = null,
    val notes: String? = null,
)

@JsonClass(generateAdapter = true)
data class LocationPatch(
    val name: String? = null,
    val kind: String? = null,
    val parent_id: String? = null,
    val notes: String? = null,
)

@JsonClass(generateAdapter = true)
data class BundleAssetDto(
    val id: String,
    val bundle_id: String,
    val sha256: String,
    val mime_type: String,
    val byte_size: Long,
    val filename: String,
    val label: String? = null,
    val kind: String = "other",
    val sort_order: Int = 0,
    val created_at: String,
    val updated_at: String,
)

@JsonClass(generateAdapter = true)
data class ManualBundleDto(
    val id: String,
    val collection_id: String,
    val title: String,
    val description: String? = null,
    val primary_asset_id: String? = null,
    val created_at: String,
    val updated_at: String,
    val assets: List<BundleAssetDto> = emptyList(),
    val item_ids: List<String> = emptyList(),
)

@JsonClass(generateAdapter = true)
data class NotificationPrefDto(
    val kind: String,
    val email_enabled: Boolean,
    val push_enabled: Boolean,
    val browser_enabled: Boolean,
    val lead_days: Int,
)

@JsonClass(generateAdapter = true)
data class NotificationPrefUpdate(
    val email_enabled: Boolean,
    val push_enabled: Boolean,
    val browser_enabled: Boolean,
    val lead_days: Int,
)

// ---------------------------------------------------------------------------
// Shopping list
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class ShoppingSourceDto(
    val kind: String, // "ad_hoc" | "depleted_item"
    val item_id: String? = null,
)

@JsonClass(generateAdapter = true)
data class ShoppingFeedEntryDto(
    val id: String,
    val source: ShoppingSourceDto,
    val collection_id: String,
    val name: String,
    val subtitle: String? = null,
    val quantity: Int = 1,
    val unit: String? = null,
    val notes: String? = null,
    val category_slug: String? = null,
    val linked_item_id: String? = null,
    val purchased_at: String? = null,
    val created_at: String,
)

@JsonClass(generateAdapter = true)
data class ShoppingItemCreateRequest(
    val collection_id: String,
    val name: String,
    val quantity: Int = 1,
    val unit: String? = null,
    val notes: String? = null,
    val category_slug: String? = null,
    val list_type: String = "groceries",
)

/** Matches the server's ShoppingItemRead (not ShoppingFeedEntry — no `source` field). */
@JsonClass(generateAdapter = true)
data class ShoppingItemReadDto(
    val id: String,
    val collection_id: String,
    val name: String,
    val quantity: Int = 1,
    val notes: String? = null,
    val category_slug: String? = null,
    val list_type: String = "groceries",
    val created_at: String,
)

@JsonClass(generateAdapter = true)
data class ShoppingItemPatchRequest(
    val name: String? = null,
    val quantity: Int? = null,
    val notes: String? = null,
)

// ---------------------------------------------------------------------------
// Shopping stores + aisles
// ---------------------------------------------------------------------------

@JsonClass(generateAdapter = true)
data class ShoppingAisleDto(
    val id: String,
    val store_id: String,
    val name: String,
    val position: Int = 0,
    val category_slugs: List<String> = emptyList(),
    val created_at: String,
    val updated_at: String,
)

@JsonClass(generateAdapter = true)
data class ShoppingStoreDto(
    val id: String,
    val owner_user_id: String,
    val name: String,
    val aisles: List<ShoppingAisleDto> = emptyList(),
    val created_at: String,
    val updated_at: String,
)

@JsonClass(generateAdapter = true)
data class ShoppingStoreCreate(val name: String)

@JsonClass(generateAdapter = true)
data class ShoppingStorePatch(val name: String? = null)

@JsonClass(generateAdapter = true)
data class ShoppingAisleCreate(
    val name: String,
    val position: Int = 0,
    val category_slugs: List<String> = emptyList(),
)

@JsonClass(generateAdapter = true)
data class ShoppingAislePatch(
    val name: String? = null,
    val position: Int? = null,
    val category_slugs: List<String>? = null,
)
