package io.github.bradbrownjr.covet.data.remote

import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
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

    // --- Items ---
    @GET("items")
    suspend fun listItems(
        @Query("collection_id") collectionId: String,
        @Query("search") search: String? = null,
        @Query("type") type: String? = null,
    ): List<ItemDto>

    @POST("items")
    suspend fun createItem(@Body body: ItemCreate): ItemDto

    @DELETE("items/{id}")
    suspend fun deleteItem(@Path("id") id: String)
}
