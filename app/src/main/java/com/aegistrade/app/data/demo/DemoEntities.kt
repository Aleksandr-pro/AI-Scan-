package com.aegistrade.app.data.demo

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(tableName = "demo_accounts")
data class DemoAccountEntity(
    @PrimaryKey
    val id: Long,
    val balance: String
)

@Entity(
    tableName = "demo_open_positions",
    primaryKeys = ["accountId"],
    foreignKeys = [
        ForeignKey(
            entity = DemoAccountEntity::class,
            parentColumns = ["id"],
            childColumns = ["accountId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [
        Index("accountId"),
        Index(value = ["positionId"], unique = true)
    ]
)
data class DemoOpenPositionEntity(
    val accountId: Long,
    val positionId: String,
    val entryPrice: String,
    val stopPrice: String,
    val quantity: String,
    val side: String
)

@Entity(
    tableName = "demo_closed_positions",
    foreignKeys = [
        ForeignKey(
            entity = DemoAccountEntity::class,
            parentColumns = ["id"],
            childColumns = ["accountId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index("accountId")]
)
data class DemoClosedPositionEntity(
    @PrimaryKey
    val positionId: String,
    val accountId: Long,
    val entryPrice: String,
    val stopPrice: String,
    val quantity: String,
    val side: String,
    val exitPrice: String,
    val profitAndLoss: String,
    val balanceBeforeClose: String,
    val balanceAfterClose: String
)
