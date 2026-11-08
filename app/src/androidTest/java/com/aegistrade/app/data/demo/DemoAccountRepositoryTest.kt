package com.aegistrade.app.data.demo

import android.content.Context
import android.database.sqlite.SQLiteConstraintException
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.aegistrade.app.domain.demo.DemoOpenRequest
import com.aegistrade.app.domain.demo.DemoSettlementError
import com.aegistrade.app.domain.risk.PositionSide
import com.aegistrade.app.domain.risk.RiskResult
import java.math.BigDecimal
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class DemoAccountRepositoryTest {

    private lateinit var database: DemoDatabase
    private lateinit var repository: DemoAccountRepository

    @Before
    fun setUp() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        database = Room.inMemoryDatabaseBuilder(
            context,
            DemoDatabase::class.java
        ).build()
        repository = DemoAccountRepository(database)
    }

    @After
    fun tearDown() {
        database.close()
    }

    private fun decimal(value: String) = BigDecimal(value)

    private fun request() = DemoOpenRequest(
        entryPrice = decimal("100"),
        stopPrice = decimal("90"),
        quantity = decimal("1"),
        side = PositionSide.BUY,
        maxRiskPercent = decimal("2")
    )

    private suspend fun initialize(balance: String = "1000") {
        assertEquals(
            DemoInitializeResult.Initialized,
            repository.initialize(decimal(balance))
        )
    }

    private suspend fun openPosition(): DemoStoreOpenResult.Opened {
        val result = repository.open(request())
        assertTrue(result is DemoStoreOpenResult.Opened)
        return result as DemoStoreOpenResult.Opened
    }

    private fun assertDecimalEquals(expected: String, actual: BigDecimal) {
        assertEquals(0, decimal(expected).compareTo(actual))
    }

    @Test
    fun initializationRejectsNonPositiveBalanceAndCreatesAccount() = runTest {
        assertEquals(
            DemoInitializeResult.InvalidInitialBalance,
            repository.initialize(decimal("0"))
        )
        assertEquals(
            DemoInitializeResult.InvalidInitialBalance,
            repository.initialize(decimal("-1"))
        )
        assertNull(repository.getAccount())

        initialize()

        assertDecimalEquals("1000", requireNotNull(repository.getAccount()).balance)
    }

    @Test
    fun repeatedInitializationDoesNotResetAccount() = runTest {
        initialize()
        openPosition()

        assertEquals(
            DemoInitializeResult.AlreadyInitialized,
            repository.initialize(decimal("5000"))
        )

        assertDecimalEquals("1000", requireNotNull(repository.getAccount()).balance)
        assertNotNull(repository.getOpenPosition())
        assertTrue(repository.getClosedPositions().isEmpty())
    }

    @Test
    fun validPositionIsSaved() = runTest {
        initialize()

        val result = openPosition()

        assertTrue(result.positionId.isNotBlank())
        assertDecimalEquals("1000", result.account.balance)
        val saved = requireNotNull(repository.getOpenPosition())
        assertEquals(result.positionId, saved.positionId)
        assertDecimalEquals("100", saved.entryPrice)
        assertDecimalEquals("90", saved.stopPrice)
        assertDecimalEquals("1", saved.quantity)
        assertEquals(PositionSide.BUY, saved.side)
    }

    @Test
    fun repeatedOpenAndExcessiveRiskAreRejectedWithoutWrites() = runTest {
        initialize()

        val excessiveRisk = repository.open(
            request().copy(maxRiskPercent = decimal("0.5"))
        )
        assertTrue(excessiveRisk is DemoStoreOpenResult.RiskRejected)
        assertTrue(
            (excessiveRisk as DemoStoreOpenResult.RiskRejected).reason
                is RiskResult.LimitExceeded
        )
        assertNull(repository.getOpenPosition())

        openPosition()
        assertEquals(
            DemoStoreOpenResult.PositionAlreadyOpen,
            repository.open(request())
        )
        assertEquals(1, database.openPositionDao().getAllForTest().size)
    }

    @Test
    fun operationsWithoutAccountAreRejected() = runTest {
        assertEquals(
            DemoStoreOpenResult.AccountNotFound,
            repository.open(request())
        )
        assertEquals(
            DemoStoreCloseResult.AccountNotFound,
            repository.close("missing", decimal("110"))
        )
        assertNull(repository.getAccount())
    }

    @Test
    fun closeUpdatesBalanceHistoryAndOpenPositionAtomically() = runTest {
        initialize()
        val opened = openPosition()

        val result = repository.close(opened.positionId, decimal("110"))

        assertTrue(result is DemoStoreCloseResult.Closed)
        result as DemoStoreCloseResult.Closed
        assertDecimalEquals("10", result.profitAndLoss)
        assertDecimalEquals("1010", result.account.balance)
        assertNull(repository.getOpenPosition())

        val history = repository.getClosedPositions()
        assertEquals(1, history.size)
        val closed = history.single()
        assertEquals(opened.positionId, closed.positionId)
        assertDecimalEquals("100", closed.entryPrice)
        assertDecimalEquals("90", closed.stopPrice)
        assertDecimalEquals("1", closed.quantity)
        assertEquals(PositionSide.BUY, closed.side)
        assertDecimalEquals("110", closed.exitPrice)
        assertDecimalEquals("10", closed.profitAndLoss)
        assertDecimalEquals("1000", closed.balanceBeforeClose)
        assertDecimalEquals("1010", closed.balanceAfterClose)
    }

    @Test
    fun repeatedCloseDoesNotChangeBalanceOrHistory() = runTest {
        initialize()
        val opened = openPosition()
        repository.close(opened.positionId, decimal("110"))

        val second = repository.close(opened.positionId, decimal("110"))

        assertEquals(DemoStoreCloseResult.NoOpenPosition, second)
        assertDecimalEquals("1010", requireNotNull(repository.getAccount()).balance)
        assertEquals(1, repository.getClosedPositions().size)
    }

    @Test
    fun wrongPositionIdDoesNotCloseCurrentPosition() = runTest {
        initialize()
        val opened = openPosition()

        val result = repository.close("wrong-id", decimal("110"))

        assertEquals(DemoStoreCloseResult.PositionIdMismatch, result)
        assertEquals(opened.positionId, repository.getOpenPosition()?.positionId)
        assertDecimalEquals("1000", requireNotNull(repository.getAccount()).balance)
        assertTrue(repository.getClosedPositions().isEmpty())
    }

    @Test
    fun staleCloseRequestDoesNotCloseNewPosition() = runTest {
        initialize()
        val first = openPosition()
        repository.close(first.positionId, decimal("110"))
        val second = openPosition()

        val result = repository.close(first.positionId, decimal("90"))

        assertEquals(DemoStoreCloseResult.PositionIdMismatch, result)
        assertEquals(second.positionId, repository.getOpenPosition()?.positionId)
        assertDecimalEquals("1010", requireNotNull(repository.getAccount()).balance)
        assertEquals(1, repository.getClosedPositions().size)
    }

    @Test
    fun invalidExitPriceDoesNotChangeData() = runTest {
        initialize()
        val opened = openPosition()

        val result = repository.close(opened.positionId, decimal("0"))

        assertEquals(
            DemoStoreCloseResult.InvalidInput(
                DemoSettlementError.INVALID_EXIT_PRICE
            ),
            result
        )
        assertEquals(opened.positionId, repository.getOpenPosition()?.positionId)
        assertDecimalEquals("1000", requireNotNull(repository.getAccount()).balance)
        assertTrue(repository.getClosedPositions().isEmpty())
    }

    @Test
    fun closeCanSaveNegativeBalance() = runTest {
        initialize("100")
        val opened = repository.open(
            request().copy(
                quantity = decimal("2"),
                maxRiskPercent = decimal("20")
            )
        )
        assertTrue(opened is DemoStoreOpenResult.Opened)
        opened as DemoStoreOpenResult.Opened

        val result = repository.close(opened.positionId, decimal("1"))

        assertTrue(result is DemoStoreCloseResult.Closed)
        result as DemoStoreCloseResult.Closed
        assertDecimalEquals("-198", result.profitAndLoss)
        assertDecimalEquals("-98", result.account.balance)
        assertDecimalEquals("-98", requireNotNull(repository.getAccount()).balance)
        assertDecimalEquals(
            "-98",
            repository.getClosedPositions().single().balanceAfterClose
        )
    }

    @Test
    fun historyWriteFailureRollsBackBalanceAndPositionDeletion() = runTest {
        repository = DemoAccountRepository(
            database = database,
            positionIdGenerator = { "conflicting-position" }
        )
        initialize()
        val opened = openPosition()
        database.closedPositionDao().insert(
            DemoClosedPositionEntity(
                positionId = opened.positionId,
                accountId = 1L,
                entryPrice = "1",
                stopPrice = "0.5",
                quantity = "1",
                side = "BUY",
                exitPrice = "2",
                profitAndLoss = "1",
                balanceBeforeClose = "1000",
                balanceAfterClose = "1001"
            )
        )

        var failure: Throwable? = null
        try {
            repository.close(opened.positionId, decimal("110"))
        } catch (expected: SQLiteConstraintException) {
            failure = expected
        }

        assertTrue(failure is SQLiteConstraintException)
        assertDecimalEquals("1000", requireNotNull(repository.getAccount()).balance)
        assertEquals(opened.positionId, repository.getOpenPosition()?.positionId)
        assertEquals(1, repository.getClosedPositions().size)
    }

    @Test
    fun concurrentCloseChangesBalanceOnlyOnce() = runTest {
        initialize()
        val opened = openPosition()

        val results = coroutineScope {
            (1..2).map {
                async(Dispatchers.Default) {
                    repository.close(opened.positionId, decimal("110"))
                }
            }.awaitAll()
        }

        assertEquals(1, results.count { it is DemoStoreCloseResult.Closed })
        assertEquals(1, results.count { it == DemoStoreCloseResult.NoOpenPosition })
        assertDecimalEquals("1010", requireNotNull(repository.getAccount()).balance)
        assertNull(repository.getOpenPosition())
        assertEquals(1, repository.getClosedPositions().size)
    }

    @Test
    fun fractionalDecimalsAreStoredExactlyWithoutDoubleConversion() = runTest {
        initialize()
        val entryPrice = decimal("100.25000000")
        val stopPrice = decimal("100.00000000")
        val quantity = decimal("0.12500000")
        val exitPrice = decimal("101.75000000")
        val opened = repository.open(
            DemoOpenRequest(
                entryPrice = entryPrice,
                stopPrice = stopPrice,
                quantity = quantity,
                side = PositionSide.BUY,
                maxRiskPercent = decimal("2")
            )
        )
        assertTrue(opened is DemoStoreOpenResult.Opened)
        opened as DemoStoreOpenResult.Opened

        val rawOpen = requireNotNull(database.openPositionDao().get(1L))
        assertEquals(entryPrice.toPlainString(), rawOpen.entryPrice)
        assertEquals(stopPrice.toPlainString(), rawOpen.stopPrice)
        assertEquals(quantity.toPlainString(), rawOpen.quantity)

        val result = repository.close(opened.positionId, exitPrice)
        assertTrue(result is DemoStoreCloseResult.Closed)
        result as DemoStoreCloseResult.Closed
        assertDecimalEquals("0.1875", result.profitAndLoss)
        assertDecimalEquals("1000.1875", result.account.balance)

        val rawClosed = database.closedPositionDao().getAll().single()
        assertEquals(exitPrice.toPlainString(), rawClosed.exitPrice)
        assertDecimalEquals("0.1875", decimal(rawClosed.profitAndLoss))
        assertDecimalEquals("1000.1875", decimal(rawClosed.balanceAfterClose))
    }
}

private suspend fun DemoOpenPositionDao.getAllForTest(): List<DemoOpenPositionEntity> {
    return listOfNotNull(get(1L))
}
