package io.github.bradbrownjr.covet.di

import android.content.Context
import androidx.room.Room
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import io.github.bradbrownjr.covet.data.local.CategoryDao
import io.github.bradbrownjr.covet.data.local.CollectionDao
import io.github.bradbrownjr.covet.data.local.CovetDatabase
import io.github.bradbrownjr.covet.data.local.ItemDao
import io.github.bradbrownjr.covet.data.local.LocationDao
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides @Singleton
    fun database(@ApplicationContext ctx: Context): CovetDatabase =
        Room.databaseBuilder(ctx, CovetDatabase::class.java, "covet.db")
            .fallbackToDestructiveMigration()
            .build()

    @Provides fun collectionDao(db: CovetDatabase): CollectionDao = db.collections()
    @Provides fun categoryDao(db: CovetDatabase): CategoryDao = db.categories()
    @Provides fun itemDao(db: CovetDatabase): ItemDao = db.items()
    @Provides fun locationDao(db: CovetDatabase): LocationDao = db.locations()
}
