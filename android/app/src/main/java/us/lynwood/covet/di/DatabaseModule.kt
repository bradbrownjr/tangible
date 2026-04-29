package us.lynwood.covet.di

import android.content.Context
import androidx.room.Room
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import us.lynwood.covet.data.local.CollectionDao
import us.lynwood.covet.data.local.CovetDatabase
import us.lynwood.covet.data.local.ItemDao
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
    @Provides fun itemDao(db: CovetDatabase): ItemDao = db.items()
}
