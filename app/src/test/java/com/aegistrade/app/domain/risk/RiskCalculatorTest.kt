package com.aegistrade.app.domain.risk

import java.math.BigDecimal
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class RiskCalculatorTest {

    private fun decimal(value: String): BigDecimal = BigDecimal(value)

    private fun validBuyInput(): RiskInput {
        return RiskInput(
            balance = decimal("1000"),
            entryPrice = decimal("100"),
            stopPrice = decimal("90"),
            quantity = decimal("1"),
            side = PositionSide.BUY,
            maxRiskPercent = decimal("2")
        )
    }

    private fun assertDecimalEquals(
        expected: String,
        actual: BigDecimal
    ) {
        assertEquals(
            "Expected $expected, actual $actual",
            0,
            decimal(expected).compareTo(actual)
        )
    }

    private fun assertInvalid(
        input: RiskInput,
        expectedError: RiskInputError
    ) {
        val result = RiskCalculator.calculate(input)

        assertEquals(
            RiskResult.InvalidInput(expectedError),
            result
        )
    }

    @Test
    fun buyCalculatesLossAndRisk() {
        val result = RiskCalculator.calculate(validBuyInput())

        assertTrue(result is RiskResult.Accepted)
        result as RiskResult.Accepted

        assertDecimalEquals("10", result.plannedLoss)
        assertDecimalEquals("1", result.riskPercent)
    }

    @Test
    fun sellCalculatesLossAndRisk() {
        val input = validBuyInput().copy(
            entryPrice = decimal("100"),
            stopPrice = decimal("110"),
            side = PositionSide.SELL
        )

        val result = RiskCalculator.calculate(input)

        assertTrue(result is RiskResult.Accepted)
        result as RiskResult.Accepted

        assertDecimalEquals("10", result.plannedLoss)
        assertDecimalEquals("1", result.riskPercent)
    }

    @Test
    fun riskExactlyAtLimitIsAccepted() {
        val input = validBuyInput().copy(
            maxRiskPercent = decimal("1")
        )

        val result = RiskCalculator.calculate(input)

        assertTrue(result is RiskResult.Accepted)
    }

    @Test
    fun riskAboveLimitIsRejected() {
        val input = validBuyInput().copy(
            maxRiskPercent = decimal("0.5")
        )

        val result = RiskCalculator.calculate(input)

        assertTrue(result is RiskResult.LimitExceeded)
        result as RiskResult.LimitExceeded

        assertDecimalEquals("10", result.plannedLoss)
        assertDecimalEquals("1", result.riskPercent)
        assertDecimalEquals("0.5", result.maxRiskPercent)
    }

    @Test
    fun limitComparisonDoesNotUseRoundedRiskPercent() {
        val input = validBuyInput().copy(
            balance = decimal("100"),
            entryPrice = decimal("2.000000001"),
            stopPrice = decimal("1"),
            quantity = decimal("1"),
            maxRiskPercent = decimal("1")
        )

        val result = RiskCalculator.calculate(input)

        assertTrue(result is RiskResult.LimitExceeded)
        result as RiskResult.LimitExceeded

        // Для отображения риск округляется до 1%.
        // Но фактическое значение немного выше лимита.
        assertDecimalEquals("1", result.riskPercent)
    }

    @Test
    fun fractionalQuantityIsCalculated() {
        val input = validBuyInput().copy(
            quantity = decimal("0.125")
        )

        val result = RiskCalculator.calculate(input)

        assertTrue(result is RiskResult.Accepted)
        result as RiskResult.Accepted

        assertDecimalEquals("1.25", result.plannedLoss)
        assertDecimalEquals("0.125", result.riskPercent)
    }

    @Test
    fun zeroAndNegativeBalanceAreRejected() {
        assertInvalid(
            validBuyInput().copy(balance = decimal("0")),
            RiskInputError.INVALID_BALANCE
        )
        assertInvalid(
            validBuyInput().copy(balance = decimal("-1")),
            RiskInputError.INVALID_BALANCE
        )
    }

    @Test
    fun zeroAndNegativeEntryPriceAreRejected() {
        assertInvalid(
            validBuyInput().copy(entryPrice = decimal("0")),
            RiskInputError.INVALID_ENTRY_PRICE
        )
        assertInvalid(
            validBuyInput().copy(entryPrice = decimal("-1")),
            RiskInputError.INVALID_ENTRY_PRICE
        )
    }

    @Test
    fun zeroAndNegativeStopPriceAreRejected() {
        assertInvalid(
            validBuyInput().copy(stopPrice = decimal("0")),
            RiskInputError.INVALID_STOP_PRICE
        )
        assertInvalid(
            validBuyInput().copy(stopPrice = decimal("-1")),
            RiskInputError.INVALID_STOP_PRICE
        )
    }

    @Test
    fun zeroAndNegativeQuantityAreRejected() {
        assertInvalid(
            validBuyInput().copy(quantity = decimal("0")),
            RiskInputError.INVALID_QUANTITY
        )
        assertInvalid(
            validBuyInput().copy(quantity = decimal("-1")),
            RiskInputError.INVALID_QUANTITY
        )
    }

    @Test
    fun invalidRiskLimitsAreRejected() {
        assertInvalid(
            validBuyInput().copy(maxRiskPercent = decimal("0")),
            RiskInputError.INVALID_MAX_RISK_PERCENT
        )
        assertInvalid(
            validBuyInput().copy(maxRiskPercent = decimal("-1")),
            RiskInputError.INVALID_MAX_RISK_PERCENT
        )
        assertInvalid(
            validBuyInput().copy(maxRiskPercent = decimal("100.01")),
            RiskInputError.INVALID_MAX_RISK_PERCENT
        )
    }

    @Test
    fun oneHundredPercentLimitIsValid() {
        val input = validBuyInput().copy(
            maxRiskPercent = decimal("100")
        )

        val result = RiskCalculator.calculate(input)

        assertTrue(result is RiskResult.Accepted)
    }

    @Test
    fun buyStopAtOrAboveEntryIsRejected() {
        assertInvalid(
            validBuyInput().copy(stopPrice = decimal("100")),
            RiskInputError.INVALID_STOP_DIRECTION
        )
        assertInvalid(
            validBuyInput().copy(stopPrice = decimal("101")),
            RiskInputError.INVALID_STOP_DIRECTION
        )
    }

    @Test
    fun sellStopAtOrBelowEntryIsRejected() {
        val sellInput = validBuyInput().copy(
            side = PositionSide.SELL
        )

        assertInvalid(
            sellInput.copy(stopPrice = decimal("100")),
            RiskInputError.INVALID_STOP_DIRECTION
        )
        assertInvalid(
            sellInput.copy(stopPrice = decimal("90")),
            RiskInputError.INVALID_STOP_DIRECTION
        )
    }

    @Test
    fun firstInvalidFieldIsReturned() {
        val input = validBuyInput().copy(
            balance = decimal("0"),
            quantity = decimal("0")
        )

        assertInvalid(input, RiskInputError.INVALID_BALANCE)
    }
}
