package io.github.bradbrownjr.tangible.data.local

import androidx.room.ColumnInfo
import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.RoomDatabase
import androidx.room.TypeConverter
import androidx.room.TypeConverters
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

/**
 * Local cache backing the offline-first repository layer.
 *
 * Phase 5.5 scope: read-through cache only. Each `refresh()` from the network
 * upserts rows here; UI observes Flows so it shows stale data immediately
 * while the network call refreshes in the background. Mutations (create /
 * delete) still go straight to the server today; full pending-op queueing
 * with CRDT writes is deferred to Phase 5.6.
 */

@Entity(tableName = "collections")
data class CollectionEntity(
    @PrimaryKey val id: String,
    val name: String,
    val description: String?,
    val icon: String?,
    @ColumnInfo(name = "is_public") val isPublic: Boolean,
    @ColumnInfo(name = "owner_id") val ownerId: String,
    @ColumnInfo(name = "default_category_slug") val defaultCategorySlug: String?,
    @ColumnInfo(name = "cached_at") val cachedAt: Long,
)

@Entity(tableName = "categories")
data class CategoryEntity(
    @PrimaryKey val id: String,
    @ColumnInfo(name = "parent_id") val parentId: String?,
    val slug: String,
    val name: String,
    val description: String?,
    val position: Int,
    @ColumnInfo(name = "cached_at") val cachedAt: Long,
)

@Entity(tableName = "items")
data class ItemEntity(
    @PrimaryKey val id: String,
    @ColumnInfo(name = "collection_id", index = true) val collectionId: String,
    @ColumnInfo(name = "category_id") val categoryId: String?,
    @ColumnInfo(name = "category_slug") val categorySlug: String?,
    val title: String,
    val subtitle: String?,
    val notes: String?,
    val condition: String?,
    val quantity: Int,
    @ColumnInfo(name = "purchase_price") val purchasePrice: Double?,
    @ColumnInfo(name = "current_value") val currentValue: Double?,
    val currency: String?,
    @ColumnInfo(name = "location_id") val locationId: String?,
    /** JSON-encoded List<String> root-first path; null when unassigned. */
    @ColumnInfo(name = "location_path_json") val locationPathJson: String?,
    /** JSON blob (Map<String, Any?>) — kept as text to avoid a converter explosion. */
    val identifiersJson: String,
    val attrsJson: String,
    val depleted: Boolean,
    @ColumnInfo(name = "purchased_at") val purchasedAt: String?,
    @ColumnInfo(name = "use_by_date") val useByDate: String?,
    @ColumnInfo(name = "date_frozen") val dateFrozen: String?,
    @ColumnInfo(name = "date_opened") val dateOpened: String?,
    @ColumnInfo(name = "cached_at") val cachedAt: Long,
)

@Entity(tableName = "locations")
data class LocationEntity(
    @PrimaryKey val id: String,
    @ColumnInfo(name = "collection_id", index = true) val collectionId: String,
    @ColumnInfo(name = "parent_id") val parentId: String?,
    val name: String,
    val kind: String,
    val notes: String?,
    @ColumnInfo(name = "qr_slug") val qrSlug: String?,
    @ColumnInfo(name = "item_count") val itemCount: Int,
    @ColumnInfo(name = "cached_at") val cachedAt: Long,
)

@Dao
interface CollectionDao {
    @Query("SELECT * FROM collections ORDER BY name COLLATE NOCASE ASC")
    fun observeAll(): Flow<List<CollectionEntity>>

    @Query("SELECT * FROM collections WHERE id = :id LIMIT 1")
    fun observe(id: String): Flow<CollectionEntity?>

    @Query("SELECT * FROM collections WHERE id = :id LIMIT 1")
    suspend fun get(id: String): CollectionEntity?

    @Upsert
    suspend fun upsertAll(rows: List<CollectionEntity>)

    @Query("DELETE FROM collections WHERE id NOT IN (:keep)")
    suspend fun deleteMissing(keep: List<String>)

    @Query("DELETE FROM collections WHERE id = :id")
    suspend fun deleteById(id: String)

    @Query("DELETE FROM collections")
    suspend fun clear()
}

@Dao
interface CategoryDao {
    @Query("SELECT * FROM categories ORDER BY position ASC")
    fun observeAll(): Flow<List<CategoryEntity>>

    @Query("SELECT * FROM categories ORDER BY position ASC")
    suspend fun getAll(): List<CategoryEntity>

    @Upsert
    suspend fun upsertAll(rows: List<CategoryEntity>)

    @Query("DELETE FROM categories")
    suspend fun clear()
}

@Dao
interface ItemDao {
    @Query("SELECT * FROM items WHERE collection_id = :collectionId ORDER BY title COLLATE NOCASE ASC")
    fun observeForCollection(collectionId: String): Flow<List<ItemEntity>>

    @Upsert
    suspend fun upsertAll(rows: List<ItemEntity>)

    @Query("DELETE FROM items WHERE id = :id")
    suspend fun delete(id: String)

    @Query("DELETE FROM items WHERE collection_id = :collectionId AND id NOT IN (:keep)")
    suspend fun deleteMissingIn(collectionId: String, keep: List<String>)

    @Query("DELETE FROM items")
    suspend fun clear()
}

@Dao
interface LocationDao {
    @Query("SELECT * FROM locations WHERE collection_id = :collectionId ORDER BY name COLLATE NOCASE ASC")
    fun observeForCollection(collectionId: String): Flow<List<LocationEntity>>

    @Query("SELECT * FROM locations WHERE collection_id = :collectionId ORDER BY name COLLATE NOCASE ASC")
    suspend fun listForCollection(collectionId: String): List<LocationEntity>

    @Upsert
    suspend fun upsertAll(rows: List<LocationEntity>)

    @Query("DELETE FROM locations WHERE collection_id = :collectionId AND id NOT IN (:keep)")
    suspend fun deleteMissingIn(collectionId: String, keep: List<String>)

    @Query("DELETE FROM locations WHERE id = :id")
    suspend fun delete(id: String)

    @Query("DELETE FROM locations")
    suspend fun clear()
}

class Converters {
    @TypeConverter fun fromBoolean(v: Boolean): Int = if (v) 1 else 0
    @TypeConverter fun toBoolean(v: Int): Boolean = v != 0
}

@Entity(tableName = "shopping_feed_cache")
data class ShoppingFeedItemEntity(
    @PrimaryKey val id: String,
    @ColumnInfo(name = "list_type", index = true) val listType: String,
    val name: String,
    val subtitle: String?,
    val quantity: Int,
    val unit: String?,
    val brand: String?,
    val notes: String?,
    @ColumnInfo(name = "category_slug") val categorySlug: String?,
    @ColumnInfo(name = "collection_id") val collectionId: String?,
    @ColumnInfo(name = "source_kind") val sourceKind: String,
    @ColumnInfo(name = "source_item_id") val sourceItemId: String?,
    @ColumnInfo(name = "linked_item_id") val linkedItemId: String?,
    @ColumnInfo(name = "wish_url") val wishUrl: String?,
    @ColumnInfo(name = "wish_priority") val wishPriority: Int?,
    @ColumnInfo(name = "purchased_at") val purchasedAt: String?,
    @ColumnInfo(name = "created_at") val createdAt: String,
    @ColumnInfo(name = "cached_at") val cachedAt: Long,
)

@Dao
interface ShoppingFeedItemDao {
    @Query("SELECT * FROM shopping_feed_cache WHERE list_type = :listType ORDER BY created_at DESC")
    suspend fun getForType(listType: String): List<ShoppingFeedItemEntity>

    @Upsert
    suspend fun upsertAll(rows: List<ShoppingFeedItemEntity>)

    @Query("DELETE FROM shopping_feed_cache WHERE list_type = :listType AND id NOT IN (:keep)")
    suspend fun deleteMissingForType(listType: String, keep: List<String>)

    @Query("DELETE FROM shopping_feed_cache")
    suspend fun clear()
}

/**
 * Queue of mutations that could not be sent to the server (offline).
 * The MutationDrainerWorker drains this table whenever network is available.
 */
@Entity(tableName = "pending_mutations")
data class PendingMutationEntity(
    /** UUID — also used as the Idempotency-Key header sent to the server. */
    @PrimaryKey val id: String,
    /** One of: PURCHASE_SHOPPING_ITEM, RESTOCK_DEPLETED_ITEM. */
    val type: String,
    /** JSON-encoded mutation arguments. */
    @ColumnInfo(name = "payload_json") val payloadJson: String,
    @ColumnInfo(name = "created_at") val createdAt: Long = System.currentTimeMillis(),
)

@Dao
interface PendingMutationDao {
    @Query("SELECT * FROM pending_mutations ORDER BY created_at ASC")
    suspend fun getAll(): List<PendingMutationEntity>

    @Query("SELECT COUNT(*) FROM pending_mutations")
    fun observeCount(): Flow<Int>

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(mutation: PendingMutationEntity)

    @Query("DELETE FROM pending_mutations WHERE id = :id")
    suspend fun delete(id: String)

    @Query("DELETE FROM pending_mutations")
    suspend fun clear()
}

@Database(
    entities = [
        CollectionEntity::class,
        CategoryEntity::class,
        ItemEntity::class,
        LocationEntity::class,
        ShoppingFeedItemEntity::class,
        PendingMutationEntity::class,
    ],
    version = 9,
    exportSchema = false,
)
@TypeConverters(Converters::class)
abstract class TangibleDatabase : RoomDatabase() {
    abstract fun collections(): CollectionDao
    abstract fun categories(): CategoryDao
    abstract fun items(): ItemDao
    abstract fun locations(): LocationDao
    abstract fun shoppingFeedItems(): ShoppingFeedItemDao
    abstract fun pendingMutations(): PendingMutationDao
}

/** Convenience for upsert callers that supply OnConflictStrategy explicitly. */
@Suppress("unused")
internal val ON_CONFLICT_REPLACE: Int = OnConflictStrategy.REPLACE
