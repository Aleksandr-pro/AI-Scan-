package com.aegistrade.app.data.demo

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

@Dao
interface DemoAccountDao {

    @Query("SELECT * FROM demo_accounts WHERE id = :accountId")
    suspend fun get(accountId: Long): DemoAccountEntity?

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insertIgnore(account: DemoAccountEntity): Long

    @Query("UPDATE demo_accounts SET balance = :balance WHERE id = :accountId")
    suspend fun updateBalance(accountId: Long, balance: String): Int
}

@Dao
interface DemoOpenPositionDao {

    @Query("SELECT * FROM demo_open_positions WHERE accountId = :accountId")
    suspend fun get(accountId: Long): DemoOpenPositionEntity?

    @Insert
    suspend fun insert(position: DemoOpenPositionEntity)

    @Query(
        "DELETE FROM demo_open_positions " +
            "WHERE accountId = :accountId AND positionId = :positionId"
    )
    suspend fun delete(accountId: Long, positionId: String): Int
}

@Dao
interface DemoClosedPositionDao {

    @Insert
    suspend fun insert(position: DemoClosedPositionEntity)

    @Query("SELECT * FROM demo_closed_positions ORDER BY rowid DESC")
    suspend fun getAll(): List<DemoClosedPositionEntity>
}
