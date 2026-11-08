package com.aegistrade.app.domain.risk

import java.math.BigDecimal
import java.math.RoundingMode

/**
 * Направление линейной позиции.
 */
enum class PositionSide {
    BUY,
    SELL
}

/**
 * Данные для расчёта планового риска.
 *
 * balance, entryPrice и stopPrice должны быть выражены
 * в одной валюте. quantity — количество единиц актива.
 *
 * Комиссии, проскальзывание, плечо и ликвидация не учитываются.
 */
data class RiskInput(
    val balance: BigDecimal,
    val entryPrice: BigDecimal,
    val stopPrice: BigDecimal,
    val quantity: BigDecimal,
    val side: PositionSide,
    val maxRiskPercent: BigDecimal
)

/**
 * Причина, по которой входные данные не могут быть рассчитаны.
 */
enum class RiskInputError {
    INVALID_BALANCE,
    INVALID_ENTRY_PRICE,
    INVALID_STOP_PRICE,
    INVALID_QUANTITY,
    INVALID_MAX_RISK_PERCENT,
    INVALID_STOP_DIRECTION
}

/**
 * Результат проверки.
 *
 * riskPercent округляется только для отображения.
 * Решение о превышении лимита принимается без округления.
 */
sealed interface RiskResult {

    data class Accepted(
        val plannedLoss: BigDecimal,
        val riskPercent: BigDecimal
    ) : RiskResult

    data class LimitExceeded(
        val plannedLoss: BigDecimal,
        val riskPercent: BigDecimal,
        val maxRiskPercent: BigDecimal
    ) : RiskResult

    data class InvalidInput(
        val error: RiskInputError
    ) : RiskResult
}

/**
 * Расчёт риска линейной позиции без учёта торговых издержек.
 *
 * Плановый убыток не гарантирует фактический результат:
 * исполнение по стоп-цене может отличаться от ожидаемого.
 */
object RiskCalculator {

    private val ZERO = BigDecimal.ZERO
    private val HUNDRED = BigDecimal("100")

    fun calculate(input: RiskInput): RiskResult {
        validate(input)?.let { error ->
            return RiskResult.InvalidInput(error)
        }

        val priceDifference = when (input.side) {
            PositionSide.BUY -> input.entryPrice.subtract(input.stopPrice)
            PositionSide.SELL -> input.stopPrice.subtract(input.entryPrice)
        }

        val plannedLoss = priceDifference.multiply(input.quantity)
        val lossTimesHundred = plannedLoss.multiply(HUNDRED)

        // Этот процент предназначен для отображения.
        val riskPercent = lossTimesHundred.divide(
            input.balance,
            8,
            RoundingMode.HALF_UP
        )

        // Сравнение без деления и округления:
        // loss / balance * 100 > maxRiskPercent
        // эквивалентно:
        // loss * 100 > balance * maxRiskPercent
        val allowedLossTimesHundred =
            input.balance.multiply(input.maxRiskPercent)

        return if (lossTimesHundred > allowedLossTimesHundred) {
            RiskResult.LimitExceeded(
                plannedLoss = plannedLoss,
                riskPercent = riskPercent,
                maxRiskPercent = input.maxRiskPercent
            )
        } else {
            RiskResult.Accepted(
                plannedLoss = plannedLoss,
                riskPercent = riskPercent
            )
        }
    }

    private fun validate(input: RiskInput): RiskInputError? {
        if (input.balance <= ZERO) {
            return RiskInputError.INVALID_BALANCE
        }

        if (input.entryPrice <= ZERO) {
            return RiskInputError.INVALID_ENTRY_PRICE
        }

        if (input.stopPrice <= ZERO) {
            return RiskInputError.INVALID_STOP_PRICE
        }

        if (input.quantity <= ZERO) {
            return RiskInputError.INVALID_QUANTITY
        }

        if (input.maxRiskPercent <= ZERO || input.maxRiskPercent > HUNDRED) {
            return RiskInputError.INVALID_MAX_RISK_PERCENT
        }

        val validStop = when (input.side) {
            PositionSide.BUY -> input.stopPrice < input.entryPrice
            PositionSide.SELL -> input.stopPrice > input.entryPrice
        }

        if (!validStop) {
            return RiskInputError.INVALID_STOP_DIRECTION
        }

        return null
    }
}
