package io.github.bradbrownjr.tangible.di

import android.content.Context
import androidx.room.Room
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import io.github.bradbrownjr.tangible.data.local.CategoryDao
import io.github.bradbrownjr.tangible.data.local.CollectionDao
import io.github.bradbrownjr.tangible.data.local.TangibleDatabase
import io.github.bradbrownjr.tangible.data.local.ItemDao
import io.github.bradbrownjr.tangible.data.local.LocationDao
import io.github.bradbrownjr.tangible.data.local.PendingMutationDao
import io.github.bradbrownjr.tangible.data.local.ShoppingFeedItemDao
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides @Singleton
    fun database(@ApplicationContext ctx: Context): TangibleDatabase =
        Room.databaseBuilder(ctx, TangibleDatabase::class.java, "tangible.db")
            .fallbackToDestructiveMigration()
            .build()

    @Provides fun collectionDao(db: TangibleDatabase): CollectionDao = db.collections()
    @Provides fun categoryDao(db: TangibleDatabase): CategoryDao = db.categories()
    @Provides fun itemDao(db: TangibleDatabase): ItemDao = db.items()
    @Provides fun locationDao(db: TangibleDatabase): LocationDao = db.locations()
    @Provides fun shoppingFeedItemDao(db: TangibleDatabase): ShoppingFeedItemDao = db.shoppingFeedItems()
    @Provides fun pendingMutationDao(db: TangibleDatabase): PendingMutationDao = db.pendingMutations()
}
