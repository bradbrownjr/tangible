package io.github.bradbrownjr.covet.data.remote

import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface CovetApi {

    // --- Auth ---
    @POST("auth/login")
    suspend fun login(@Body body: LoginRequest): SessionInfoDto

    @GET("auth/me")
    suspend fun me(): UserDto

    @POST("auth/tokens")
    suspend fun createToken(@Query("name") name: String): TokenInfo

    // --- Collections ---
    @GET("collections")
    suspend fun listCollections(): List<CollectionDto>

    @POST("collections")
    suspend fun createCollection(@Body body: CollectionCreate): CollectionDto

    @GET("collections/{id}")
    suspend fun getCollection(@Path("id") id: String): CollectionDto

    @DELETE("collections/{id}")
    suspend fun deleteCollection(@Path("id") id: String)

    // --- Categories ---
    @GET("categories")
    suspend fun listCategories(): List<CategoryDto>

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

    @DELETE("items/{id}")
    suspend fun deleteItem(@Path("id") id: String)

    // --- Metadata ---
    @POST("metadata/scrape")
    suspend fun scrape(@Body body: ScrapeRequest): ScrapeResponse

    @POST("metadata/barcode")
    suspend fun barcodeLookup(@Body body: BarcodeLookupRequest): BarcodeLookupResponse
}
