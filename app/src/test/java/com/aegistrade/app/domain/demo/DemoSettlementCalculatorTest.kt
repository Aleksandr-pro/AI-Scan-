package com.aegistrade.app.domain.demo

import com.aegistrade.app.domain.risk.PositionSide
import java.math.BigDecimal
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class DemoSettlementCalculatorTest {

    private fun decimal(value: String): BigDecimal = BigDecimal(value)

    private fun input(): DemoSettlementInput {
        return DemoSettlementInput(
            balanceBeforeClose = decimal("1000"),
            entryPrice = decimal("100"),
            exitPrice = decimal("110"),
            quantity = decimal("2"),
            side = PositionSide.BUY
        )
    }

    private fun assertDecimalEquals(expected: String, actual: BigDecimal) {
        assertEquals(
            "Expected $expected, actual $actual",
            0,
            decimal(expected).compareTo(actual)
        )
    }

    private fun calculate(input: DemoSettlementInput):
        DemoSettlementResult.Calculated {
        val result = DemoSettlementCalculator.calculate(input)

        assertTrue(result is DemoSettlementResult.Calculated)
        return result as DemoSettlementResult.Calculated
    }

    @Test
    fun buyProfitIncreasesBalance() {
        val result = calculate(input())

        assertDecimalEquals("20", result.profitAndLoss)
        assertDecimalEquals("1020", result.balanceAfterClose)
    }

    @Test
    fun buyLossDecreasesBalance() {
        val result = calculate(input().copy(exitPrice = decimal("90")))

        assertDecimalEquals("-20", result.profitAndLoss)
        assertDecimalEquals("980", result.balanceAfterClose)
    }

    @Test
    fun sellProfitIncreasesBalance() {
        val result = calculate(
            input().copy(
                side = PositionSide.SELL,
                exitPrice = decimal("90")
            )
        )

        assertDecimalEquals("20", result.profitAndLoss)
        assertDecimalEquals("1020", result.balanceAfterClose)
    }

    @Test
    fun sellLossDecreasesBalance() {
        val result = calculate(input().copy(side = PositionSide.SELL))

        assertDecimalEquals("-20", result.profitAndLoss)
        assertDecimalEquals("980", result.balanceAfterClose)
    }

    @Test
    fun unchangedPriceProducesZeroResult() {
        val result = calculate(input().copy(exitPrice = decimal("100")))

        assertDecimalEquals("0", result.profitAndLoss)
        assertDecimalEquals("1000", result.balanceAfterClose)
    }

    @Test
    fun fractionalValuesAreCalculatedExactly() {
        val result = calculate(
            input().copy(
                entryPrice = decimal("100.25"),
                exitPrice = decimal("101.75"),
                quantity = decimal("0.125")
            )
        )

        assertDecimalEquals("0.1875", result.profitAndLoss)
        assertDecimalEquals("1000.1875", result.balanceAfterClose)
    }

    @Test
    fun lossGreaterThanBalanceIsNotHidden() {
        val result = calculate(
            input().copy(
                balanceBeforeClose = decimal("5"),
                exitPrice = decimal("90")
            )
        )

        assertDecimalEquals("-20", result.profitAndLoss)
        assertDecimalEquals("-15", result.balanceAfterClose)
    }

    @Test
    fun zeroBalanceIsAllowedForSettlement() {
        val result = calculate(input().copy(balanceBeforeClose = decimal("0")))

        assertDecimalEquals("20", result.profitAndLoss)
        assertDecimalEquals("20", result.balanceAfterClose)
    }

    @Test
    fun negativeBalanceBeforeCloseIsRejected() {
        val result = DemoSettlementCalculator.calculate(
            input().copy(balanceBeforeClose = decimal("-1"))
        )

        assertEquals(
            DemoSettlementResult.InvalidInput(
                DemoSettlementError.INVALID_BALANCE
            ),
            result
        )
    }

    @Test
    fun invalidPricesAndQuantityAreRejected() {
        val cases = listOf(
            input().copy(entryPrice = decimal("0")) to
                DemoSettlementError.INVALID_ENTRY_PRICE,
            input().copy(entryPrice = decimal("-1")) to
                DemoSettlementError.INVALID_ENTRY_PRICE,
            input().copy(exitPrice = decimal("0")) to
                DemoSettlementError.INVALID_EXIT_PRICE,
            input().copy(exitPrice = decimal("-1")) to
                DemoSettlementError.INVALID_EXIT_PRICE,
            input().copy(quantity = decimal("0")) to
                DemoSettlementError.INVALID_QUANTITY,
            input().copy(quantity = decimal("-1")) to
                DemoSettlementError.INVALID_QUANTITY
        )

        cases.forEach { (invalidInput, expectedError) ->
            assertEquals(
                DemoSettlementResult.InvalidInput(expectedError),
                DemoSettlementCalculator.calculate(invalidInput)
            )
        }
    }
}
