package com.aegistrade.app.data.demo

import androidx.room.withTransaction
import com.aegistrade.app.domain.demo.DemoAccount
import com.aegistrade.app.domain.demo.DemoAccountOperations
import com.aegistrade.app.domain.demo.DemoCloseResult
import com.aegistrade.app.domain.demo.DemoOpenRequest
import com.aegistrade.app.domain.demo.DemoOpenResult
import com.aegistrade.app.domain.demo.DemoPosition
import com.aegistrade.app.domain.demo.DemoSettlementError
import com.aegistrade.app.domain.risk.PositionSide
import com.aegistrade.app.domain.risk.RiskResult
import java.math.BigDecimal
import java.util.UUID

private const val DEMO_ACCOUNT_ID = 1L

data class StoredDemoOpenPosition(
    val positionId: String,
    val entryPrice: BigDecimal,
    val stopPrice: BigDecimal,
    val quantity: BigDecimal,
    val side: PositionSide
)

data class StoredDemoClosedPosition(
    val positionId: String,
    val entryPrice: BigDecimal,
    val stopPrice: BigDecimal,
    val quantity: BigDecimal,
    val side: PositionSide,
    val exitPrice: BigDecimal,
    val profitAndLoss: BigDecimal,
    val balanceBeforeClose: BigDecimal,
    val balanceAfterClose: BigDecimal
)

sealed interface DemoInitializeResult {
    data object Initialized : DemoInitializeResult
    data object AlreadyInitialized : DemoInitializeResult
    data object InvalidInitialBalance : DemoInitializeResult
}

sealed interface DemoStoreOpenResult {

    data class Opened(
        val positionId: String,
        val account: DemoAccount,
        val risk: RiskResult.Accepted
    ) : DemoStoreOpenResult

    data object AccountNotFound : DemoStoreOpenResult

    data object PositionAlreadyOpen : DemoStoreOpenResult

    data class RiskRejected(
        val reason: RiskResult
    ) : DemoStoreOpenResult
}

sealed interface DemoStoreCloseResult {

    data class Closed(
        val positionId: String,
        val account: DemoAccount,
        val profitAndLoss: BigDecimal
    ) : DemoStoreCloseResult

    data object AccountNotFound : DemoStoreCloseResult

    data object NoOpenPosition : DemoStoreCloseResult

    data object PositionIdMismatch : DemoStoreCloseResult

    data class InvalidInput(
        val error: DemoSettlementError
    ) : DemoStoreCloseResult
}

/**
 * Сохраняет демо-счёт и выполняет каждую операцию в транзакции Room.
 *
 * Все денежные значения и цены записываются как десятичные строки.
 * Расчёты делегируются доменным операциям без дублирования формул.
 */
class DemoAccountRepository(
    private val database: DemoDatabase,
    private val positionIdGenerator: () -> String = {
        UUID.randomUUID().toString()
    }
) {

    suspend fun initialize(
        initialBalance: BigDecimal
    ): DemoInitializeResult {
        if (initialBalance <= BigDecimal.ZERO) {
            return DemoInitializeResult.InvalidInitialBalance
        }

        return database.withTransaction {
            val insertedId = database.accountDao().insertIgnore(
                DemoAccountEntity(
                    id = DEMO_ACCOUNT_ID,
                    balance = initialBalance.toPlainString()
                )
            )

            if (insertedId == -1L) {
                DemoInitializeResult.AlreadyInitialized
            } else {
                DemoInitializeResult.Initialized
            }
        }
    }

    suspend fun open(request: DemoOpenRequest): DemoStoreOpenResult {
        return database.withTransaction {
            val accountEntity = database.accountDao().get(DEMO_ACCOUNT_ID)
                ?: return@withTransaction DemoStoreOpenResult.AccountNotFound
            val openPositionEntity =
                database.openPositionDao().get(DEMO_ACCOUNT_ID)

            val account = DemoAccount(
                balance = accountEntity.balance.toBigDecimal(),
                openPosition = openPositionEntity?.toDomainPosition()
            )

            when (val result = DemoAccountOperations.open(account, request)) {
                DemoOpenResult.PositionAlreadyOpen ->
                    DemoStoreOpenResult.PositionAlreadyOpen

                is DemoOpenResult.RiskRejected ->
                    DemoStoreOpenResult.RiskRejected(result.reason)

                is DemoOpenResult.Opened -> {
                    val position = requireNotNull(result.account.openPosition)
                    val positionId = positionIdGenerator()

                    database.openPositionDao().insert(
                        DemoOpenPositionEntity(
                            accountId = DEMO_ACCOUNT_ID,
                            positionId = positionId,
                            entryPrice = position.entryPrice.toPlainString(),
                            stopPrice = position.stopPrice.toPlainString(),
                            quantity = position.quantity.toPlainString(),
                            side = position.side.name
                        )
                    )

                    DemoStoreOpenResult.Opened(
                        positionId = positionId,
                        account = result.account,
                        risk = result.risk
                    )
                }
            }
        }
    }

    suspend fun close(
        expectedPositionId: String,
        exitPrice: BigDecimal
    ): DemoStoreCloseResult {
        return database.withTransaction {
            val accountEntity = database.accountDao().get(DEMO_ACCOUNT_ID)
                ?: return@withTransaction DemoStoreCloseResult.AccountNotFound
            val positionEntity = database.openPositionDao().get(DEMO_ACCOUNT_ID)
                ?: return@withTransaction DemoStoreCloseResult.NoOpenPosition

            if (positionEntity.positionId != expectedPositionId) {
                return@withTransaction DemoStoreCloseResult.PositionIdMismatch
            }

            val position = positionEntity.toDomainPosition()
            val account = DemoAccount(
                balance = accountEntity.balance.toBigDecimal(),
                openPosition = position
            )

            when (
                val result = DemoAccountOperations.close(account, exitPrice)
            ) {
                DemoCloseResult.NoOpenPosition ->
                    DemoStoreCloseResult.NoOpenPosition

                is DemoCloseResult.InvalidInput ->
                    DemoStoreCloseResult.InvalidInput(result.error)

                is DemoCloseResult.Closed -> {
                    check(
                        database.accountDao().updateBalance(
                            accountId = DEMO_ACCOUNT_ID,
                            balance = result.account.balance.toPlainString()
                        ) == 1
                    ) { "Demo account balance was not updated" }

                    database.closedPositionDao().insert(
                        DemoClosedPositionEntity(
                            positionId = positionEntity.positionId,
                            accountId = DEMO_ACCOUNT_ID,
                            entryPrice = position.entryPrice.toPlainString(),
                            stopPrice = position.stopPrice.toPlainString(),
                            quantity = position.quantity.toPlainString(),
                            side = position.side.name,
                            exitPrice = exitPrice.toPlainString(),
                            profitAndLoss = result.profitAndLoss.toPlainString(),
                            balanceBeforeClose = account.balance.toPlainString(),
                            balanceAfterClose =
                                result.account.balance.toPlainString()
                        )
                    )

                    check(
                        database.openPositionDao().delete(
                            accountId = DEMO_ACCOUNT_ID,
                            positionId = expectedPositionId
                        ) == 1
                    ) { "Open demo position was not deleted" }

                    DemoStoreCloseResult.Closed(
                        positionId = expectedPositionId,
                        account = result.account,
                        profitAndLoss = result.profitAndLoss
                    )
                }
            }
        }
    }

    suspend fun getAccount(): DemoAccount? {
        return database.withTransaction {
            val accountEntity = database.accountDao().get(DEMO_ACCOUNT_ID)
                ?: return@withTransaction null

            DemoAccount(
                balance = accountEntity.balance.toBigDecimal(),
                openPosition = database.openPositionDao()
                    .get(DEMO_ACCOUNT_ID)
                    ?.toDomainPosition()
            )
        }
    }

    suspend fun getOpenPosition(): StoredDemoOpenPosition? {
        return database.openPositionDao().get(DEMO_ACCOUNT_ID)?.toStored()
    }

    suspend fun getClosedPositions(): List<StoredDemoClosedPosition> {
        return database.closedPositionDao().getAll().map { entity ->
            StoredDemoClosedPosition(
                positionId = entity.positionId,
                entryPrice = entity.entryPrice.toBigDecimal(),
                stopPrice = entity.stopPrice.toBigDecimal(),
                quantity = entity.quantity.toBigDecimal(),
                side = PositionSide.valueOf(entity.side),
                exitPrice = entity.exitPrice.toBigDecimal(),
                profitAndLoss = entity.profitAndLoss.toBigDecimal(),
                balanceBeforeClose = entity.balanceBeforeClose.toBigDecimal(),
                balanceAfterClose = entity.balanceAfterClose.toBigDecimal()
            )
        }
    }
}

private fun DemoOpenPositionEntity.toDomainPosition(): DemoPosition {
    return DemoPosition(
        entryPrice = entryPrice.toBigDecimal(),
        stopPrice = stopPrice.toBigDecimal(),
        quantity = quantity.toBigDecimal(),
        side = PositionSide.valueOf(side)
    )
}

private fun DemoOpenPositionEntity.toStored(): StoredDemoOpenPosition {
    return StoredDemoOpenPosition(
        positionId = positionId,
        entryPrice = entryPrice.toBigDecimal(),
        stopPrice = stopPrice.toBigDecimal(),
        quantity = quantity.toBigDecimal(),
        side = PositionSide.valueOf(side)
    )
}
