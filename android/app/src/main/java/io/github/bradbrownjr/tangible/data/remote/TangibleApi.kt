package io.github.bradbrownjr.tangible.data.remote

import okhttp3.MultipartBody
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.PUT
import retrofit2.http.Query

interface TangibleApi {

    // --- Auth ---
    @POST("auth/login")
    suspend fun login(@Body body: LoginRequest): SessionInfoDto

    @GET("auth/me")
    suspend fun me(): UserDto

    @PATCH("auth/me")
    suspend fun patchMe(@Body body: PatchMeRequest): UserDto

    @POST("auth/tokens")
    suspend fun createToken(@Query("name") name: String): TokenInfo

    // --- Collections ---
    @GET("collections")
    suspend fun listCollections(): List<CollectionDto>

    @POST("collections")
    suspend fun createCollection(@Body body: CollectionCreate): CollectionDto

    @GET("collections/{id}")
    suspend fun getCollection(@Path("id") id: String): CollectionDto

    @PATCH("collections/{id}")
    suspend fun patchCollection(@Path("id") id: String, @Body body: CollectionPatch): CollectionDto

    @DELETE("collections/{id}")
    suspend fun deleteCollection(@Path("id") id: String)

    @GET("changelog")
    suspend fun changelog(): String

    // --- Categories ---
    @GET("categories")
    suspend fun listCategories(): List<CategoryDto>

    @GET("tags")
    suspend fun listTags(): List<TagDto>

    @GET("contacts")
    suspend fun listContacts(): List<ContactDto>

    // --- Locations ---
    @GET("locations")
    suspend fun listLocations(@Query("collection_id") collectionId: String): List<LocationDto>

    @POST("locations")
    suspend fun createLocation(@Body body: LocationCreate): LocationDto

    @PATCH("locations/{id}")
    suspend fun patchLocation(@Path("id") id: String, @Body body: LocationPatch): LocationDto

    @DELETE("locations/{id}")
    suspend fun deleteLocation(@Path("id") id: String)

    // --- Items ---
    @GET("items")
    suspend fun listItems(
        @Query("collection_id") collectionId: String,
        @Query("search") search: String? = null,
        @Query("category_subtree") categorySubtree: String? = null,
    ): List<ItemDto>

    @POST("items")
    suspend fun createItem(@Body body: ItemCreate): ItemDto

    @PATCH("items/{id}")
    suspend fun patchItem(@Path("id") id: String, @Body body: ItemPatch): ItemDto

    @GET("items/{id}")
    suspend fun getItem(@Path("id") id: String): ItemDto

    @GET("items/search")
    suspend fun searchItems(
        @Query("q") q: String,
        @Query("field") field: String? = null,
        @Query("include_archived") includeArchived: Boolean? = null,
        @Query("limit") limit: Int? = null,
    ): List<ItemDto>

    @DELETE("items/{id}")
    suspend fun deleteItem(@Path("id") id: String)

    @POST("items/bulk-patch")
    suspend fun bulkPatchItems(@Body body: ItemBulkPatchRequest): List<ItemDto>

    @POST("items/bulk-archive")
    suspend fun bulkArchiveItems(@Body body: ItemBulkArchiveRequest): List<ItemDto>

    @POST("items/bulk-restore")
    suspend fun bulkRestoreItems(@Body body: ItemBulkRestoreRequest): List<ItemDto>

    @POST("items/bulk-delete")
    suspend fun bulkDeleteItems(@Body body: ItemBulkDeleteRequest): ItemBulkDeleteResponse

    @POST("items/bulk-tags")
    suspend fun bulkTagItems(@Body body: ItemBulkTagRequest): List<ItemDto>

    @POST("items/bulk-lend")
    suspend fun bulkLendItems(@Body body: ItemBulkLendRequest): List<LoanDto>

    @GET("items/grocery-list")
    suspend fun getShoppingList(): List<ItemDto>

    @GET("lists")
    suspend fun getShoppingFeed(
        @Query("list_type") listType: String? = null
    ): List<ShoppingFeedEntryDto>

    @POST("lists")
    suspend fun createShoppingItem(@Body body: ShoppingItemCreateRequest): ShoppingItemReadDto

    @PATCH("lists/{id}")
    suspend fun patchShoppingItem(@Path("id") id: String, @Body body: ShoppingItemPatchRequest): ShoppingItemReadDto

    @DELETE("lists/{id}")
    suspend fun deleteShoppingItem(@Path("id") id: String)

    @POST("lists/{id}/purchase")
    suspend fun purchaseShoppingItem(
        @Path("id") id: String,
        @Header("Idempotency-Key") idempotencyKey: String? = null,
    )

    // Shopping stores
    @GET("lists/stores")
    suspend fun listShoppingStores(): List<ShoppingStoreDto>

    @POST("lists/stores")
    suspend fun createShoppingStore(@Body body: ShoppingStoreCreate): ShoppingStoreDto

    @PATCH("lists/stores/{id}")
    suspend fun updateShoppingStore(@Path("id") id: String, @Body body: ShoppingStorePatch): ShoppingStoreDto

    @DELETE("lists/stores/{id}")
    suspend fun deleteShoppingStore(@Path("id") id: String)

    // Shopping aisles
    @GET("lists/stores/{storeId}/aisles")
    suspend fun listShoppingAisles(@Path("storeId") storeId: String): List<ShoppingAisleDto>

    @POST("lists/stores/{storeId}/aisles")
    suspend fun createShoppingAisle(@Path("storeId") storeId: String, @Body body: ShoppingAisleCreate): ShoppingAisleDto

    @PATCH("lists/stores/{storeId}/aisles/{aisleId}")
    suspend fun updateShoppingAisle(
        @Path("storeId") storeId: String,
        @Path("aisleId") aisleId: String,
        @Body body: ShoppingAislePatch,
    ): ShoppingAisleDto

    @DELETE("lists/stores/{storeId}/aisles/{aisleId}")
    suspend fun deleteShoppingAisle(
        @Path("storeId") storeId: String,
        @Path("aisleId") aisleId: String,
    )

    @PUT("lists/stores/{storeId}/aisles/reorder")
    suspend fun reorderShoppingAisles(@Path("storeId") storeId: String, @Body order: List<String>)

    @POST("items/{id}/restock")
    suspend fun restockItem(
        @Path("id") id: String,
        @Body body: RestockRequest,
        @Header("Idempotency-Key") idempotencyKey: String? = null,
    ): ItemLotDto

    @GET("alerts")
    suspend fun getAlerts(@Query("within_days") withinDays: Int = 14): List<DueAlertDto>

    // --- Metadata ---
    @POST("metadata/scrape")
    suspend fun scrape(@Body body: ScrapeRequest): ScrapeResponse

    @POST("metadata/barcode")
    suspend fun barcodeLookup(@Body body: BarcodeLookupRequest): BarcodeLookupResponse

    // --- Photos ---
    @GET("items/{id}/photos")
    suspend fun listPhotos(@Path("id") itemId: String): List<PhotoDto>

    @Multipart
    @POST("items/{id}/photos")
    suspend fun uploadPhotos(
        @Path("id") itemId: String,
        @Part file: MultipartBody.Part,
    ): List<PhotoDto>

    @DELETE("photos/{id}")
    suspend fun deletePhoto(@Path("id") id: String)

    // --- Manual / asset bundles ---
    @GET("collections/{cid}/bundles")
    suspend fun listBundles(@Path("cid") collectionId: String): List<ManualBundleDto>

    @GET("items/{id}/bundles")
    suspend fun listItemBundles(@Path("id") itemId: String): List<ManualBundleDto>

    @GET("bundles/{id}")
    suspend fun getBundle(@Path("id") bundleId: String): ManualBundleDto

    // --- Notification preferences ---
    @GET("notifications")
    suspend fun listNotificationPrefs(): List<NotificationPrefDto>

    @PUT("notifications/{kind}")
    suspend fun updateNotificationPref(
        @Path("kind") kind: String,
        @Body body: NotificationPrefUpdate,
    ): NotificationPrefDto

    // --- Chores ---
    @GET("collections/{collectionId}/chores")
    suspend fun listChores(@Path("collectionId") collectionId: String): List<ChoreDto>

    @POST("collections/{collectionId}/chores")
    suspend fun createChore(
        @Path("collectionId") collectionId: String,
        @Body body: ChoreCreateDto,
    ): ChoreDto

    @POST("chores/{choreId}/complete")
    suspend fun completeChore(
        @Path("choreId") choreId: String,
        @Body body: ChoreCompletePayloadDto,
    ): ChoreDto

    @DELETE("chores/{choreId}")
    suspend fun deleteChore(@Path("choreId") choreId: String)
}
