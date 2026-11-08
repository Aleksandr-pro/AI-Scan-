package com.aegistrade.app.domain.demo

import com.aegistrade.app.domain.risk.PositionSide
import com.aegistrade.app.domain.risk.RiskInputError
import com.aegistrade.app.domain.risk.RiskResult
import java.math.BigDecimal
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class DemoAccountTest {

    private fun decimal(value: String) = BigDecimal(value)

    private fun account() = DemoAccount(
        balance = decimal("1000")
    )

    private fun request() = DemoOpenRequest(
        entryPrice = decimal("100"),
        stopPrice = decimal("90"),
        quantity = decimal("1"),
        side = PositionSide.BUY,
        maxRiskPercent = decimal("2")
    )

    private fun openAccount(): DemoAccount {
        val result = DemoAccountOperations.open(account(), request())
        assertTrue(result is DemoOpenResult.Opened)
        return (result as DemoOpenResult.Opened).account
    }

    private fun assertDecimalEquals(
        expected: String,
        actual: BigDecimal
    ) {
        assertEquals(0, decimal(expected).compareTo(actual))
    }

    @Test
    fun validPositionOpensWithoutChangingBalance() {
        val original = account()
        val result = DemoAccountOperations.open(original, request())

        assertTrue(result is DemoOpenResult.Opened)
        result as DemoOpenResult.Opened

        assertDecimalEquals("1000", result.account.balance)
        assertDecimalEquals("10", result.risk.plannedLoss)
        assertEquals(PositionSide.BUY, result.account.openPosition?.side)

        // Исходное состояние не изменяется.
        assertNull(original.openPosition)
    }

    @Test
    fun secondPositionCannotBeOpened() {
        val result = DemoAccountOperations.open(openAccount(), request())

        assertEquals(DemoOpenResult.PositionAlreadyOpen, result)
    }

    @Test
    fun excessiveRiskPreventsOpening() {
        val result = DemoAccountOperations.open(
            account(),
            request().copy(maxRiskPercent = decimal("0.5"))
        )

        assertTrue(result is DemoOpenResult.RiskRejected)
        result as DemoOpenResult.RiskRejected

        assertTrue(result.reason is RiskResult.LimitExceeded)
    }

    @Test
    fun invalidStopPreventsOpening() {
        val result = DemoAccountOperations.open(
            account(),
            request().copy(stopPrice = decimal("110"))
        )

        assertTrue(result is DemoOpenResult.RiskRejected)
        result as DemoOpenResult.RiskRejected

        assertEquals(
            RiskResult.InvalidInput(RiskInputError.INVALID_STOP_DIRECTION),
            result.reason
        )
    }

    @Test
    fun nonPositiveBalancePreventsOpening() {
        listOf("0", "-15").forEach { balance ->
            val result = DemoAccountOperations.open(
                DemoAccount(balance = decimal(balance)),
                request()
            )

            assertTrue(result is DemoOpenResult.RiskRejected)
            result as DemoOpenResult.RiskRejected

            assertEquals(
                RiskResult.InvalidInput(RiskInputError.INVALID_BALANCE),
                result.reason
            )
        }
    }

    @Test
    fun profitableCloseUpdatesBalanceAndRemovesPosition() {
        val result = DemoAccountOperations.close(
            openAccount(),
            exitPrice = decimal("110")
        )

        assertTrue(result is DemoCloseResult.Closed)
        result as DemoCloseResult.Closed

        assertDecimalEquals("10", result.profitAndLoss)
        assertDecimalEquals("1010", result.account.balance)
        assertNull(result.account.openPosition)
    }

    @Test
    fun closeCanProduceNegativeBalance() {
        val openResult = DemoAccountOperations.open(
            DemoAccount(balance = decimal("100")),
            request().copy(
                quantity = decimal("2"),
                maxRiskPercent = decimal("20")
            )
        )

        assertTrue(openResult is DemoOpenResult.Opened)
        openResult as DemoOpenResult.Opened

        val closeResult = DemoAccountOperations.close(
            openResult.account,
            exitPrice = decimal("1")
        )

        assertTrue(closeResult is DemoCloseResult.Closed)
        closeResult as DemoCloseResult.Closed

        assertDecimalEquals("-198", closeResult.profitAndLoss)
        assertDecimalEquals("-98", closeResult.account.balance)
    }

    @Test
    fun closeWithoutPositionIsRejected() {
        val result = DemoAccountOperations.close(
            account(),
            exitPrice = decimal("110")
        )

        assertEquals(DemoCloseResult.NoOpenPosition, result)
    }

    @Test
    fun closingReturnedStateTwiceIsRejected() {
        val first = DemoAccountOperations.close(
            openAccount(),
            exitPrice = decimal("110")
        )

        assertTrue(first is DemoCloseResult.Closed)
        first as DemoCloseResult.Closed

        val second = DemoAccountOperations.close(
            first.account,
            exitPrice = decimal("110")
        )

        assertEquals(DemoCloseResult.NoOpenPosition, second)
    }

    @Test
    fun invalidExitPriceDoesNotProduceNewAccount() {
        val opened = openAccount()

        val result = DemoAccountOperations.close(
            opened,
            exitPrice = decimal("0")
        )

        assertEquals(
            DemoCloseResult.InvalidInput(
                DemoSettlementError.INVALID_EXIT_PRICE
            ),
            result
        )

        // Оригинальное состояние остаётся доступным.
        assertTrue(opened.openPosition != null)
        assertDecimalEquals("1000", opened.balance)
    }

    @Test
    fun sellPositionCanBeOpenedAndClosed() {
        val openResult = DemoAccountOperations.open(
            account(),
            request().copy(
                side = PositionSide.SELL,
                stopPrice = decimal("110")
            )
        )

        assertTrue(openResult is DemoOpenResult.Opened)
        openResult as DemoOpenResult.Opened

        val closeResult = DemoAccountOperations.close(
            openResult.account,
            exitPrice = decimal("90")
        )

        assertTrue(closeResult is DemoCloseResult.Closed)
        closeResult as DemoCloseResult.Closed

        assertDecimalEquals("10", closeResult.profitAndLoss)
        assertDecimalEquals("1010", closeResult.account.balance)
    }
}
