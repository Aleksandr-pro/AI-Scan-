package com.aegistrade.app.data.demo

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [
        DemoAccountEntity::class,
        DemoOpenPositionEntity::class,
        DemoClosedPositionEntity::class
    ],
    version = 1,
    exportSchema = false
)
abstract class DemoDatabase : RoomDatabase() {

    abstract fun accountDao(): DemoAccountDao

    abstract fun openPositionDao(): DemoOpenPositionDao

    abstract fun closedPositionDao(): DemoClosedPositionDao

    companion object {

        fun create(context: Context): DemoDatabase {
            return Room.databaseBuilder(
                context.applicationContext,
                DemoDatabase::class.java,
                "aegis-trade-demo.db"
            ).build()
        }
    }
}
