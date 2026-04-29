package io.github.bradbrownjr.covet.data.repo

import com.squareup.moshi.Moshi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import io.github.bradbrownjr.covet.data.local.CollectionDao
import io.github.bradbrownjr.covet.data.local.ItemDao
import io.github.bradbrownjr.covet.data.local.toDto
import io.github.bradbrownjr.covet.data.local.toEntity
import io.github.bradbrownjr.covet.data.remote.CollectionCreate
import io.github.bradbrownjr.covet.data.remote.CollectionDto
import io.github.bradbrownjr.covet.data.remote.CovetApi
import io.github.bradbrownjr.covet.data.remote.ItemCreate
import io.github.bradbrownjr.covet.data.remote.ItemDto
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Offline-first collection repository.
 *
 * Reads stream from Room (`observe()`); `list()` / `get()` pull the network
 * and upsert into the cache. Mutations still hit the network synchronously
 * and write through to the cache on success — pending-op queueing for
 * offline writes is Phase 5.6.
 */
@Singleton
class CollectionRepository @Inject constructor(
    private val api: CovetApi,
    private val dao: CollectionDao,
) {
    fun observe(): Flow<List<CollectionDto>> =
        dao.observeAll().map { rows -> rows.map { it.toDto() } }

    fun observeOne(id: String): Flow<CollectionDto?> =
        dao.observe(id).map { it?.toDto() }

    suspend fun list(): List<CollectionDto> {
        val remote = api.listCollections()
        dao.upsertAll(remote.map { it.toEntity() })
        dao.deleteMissing(remote.map { it.id })
        return remote
    }

    suspend fun get(id: String): CollectionDto {
        val cached = dao.get(id)
        return try {
            val fresh = api.getCollection(id)
            dao.upsertAll(listOf(fresh.toEntity()))
            fresh
        } catch (t: Throwable) {
            cached?.toDto() ?: throw t
        }
    }

    suspend fun create(name: String, description: String? = null): CollectionDto {
        val created = api.createCollection(CollectionCreate(name = name, description = description))
        dao.upsertAll(listOf(created.toEntity()))
        return created
    }
}

@Singleton
class ItemRepository @Inject constructor(
    private val api: CovetApi,
    private val dao: ItemDao,
    private val moshi: Moshi,
) {
    fun observe(collectionId: String): Flow<List<ItemDto>> =
        dao.observeForCollection(collectionId).map { rows -> rows.map { it.toDto(moshi) } }

    suspend fun list(collectionId: String, search: String? = null, type: String? = null): List<ItemDto> {
        val remote = api.listItems(
            collectionId = collectionId,
            search = search?.takeIf { it.isNotBlank() },
            type = type,
        )
        // Only mirror unfiltered results into the cache so filters don't
        // delete entries that simply didn't match the current query.
        if (search.isNullOrBlank() && type == null) {
            dao.upsertAll(remote.map { it.toEntity(moshi) })
            dao.deleteMissingIn(collectionId, remote.map { it.id })
        }
        return remote
    }

    suspend fun create(
        collectionId: String,
        type: String,
        title: String,
        identifiers: Map<String, String> = emptyMap(),
    ): ItemDto {
        val created = api.createItem(
            ItemCreate(
                collection_id = collectionId,
                type = type,
                title = title,
                identifiers = identifiers,
            ),
        )
        dao.upsertAll(listOf(created.toEntity(moshi)))
        return created
    }

    suspend fun delete(id: String) {
        api.deleteItem(id)
        dao.delete(id)
    }
}
