package com.aegistrade.app.domain.demo

import com.aegistrade.app.domain.risk.PositionSide
import java.math.BigDecimal

/**
 * Входные данные для расчёта закрытия линейной демо-позиции.
 *
 * balanceBeforeClose, entryPrice и exitPrice выражены в одной валюте.
 * quantity — количество единиц актива.
 */
data class DemoSettlementInput(
    val balanceBeforeClose: BigDecimal,
    val entryPrice: BigDecimal,
    val exitPrice: BigDecimal,
    val quantity: BigDecimal,
    val side: PositionSide
)

enum class DemoSettlementError {
    INVALID_ENTRY_PRICE,
    INVALID_EXIT_PRICE,
    INVALID_QUANTITY
}

sealed interface DemoSettlementResult {

    data class Calculated(
        val profitAndLoss: BigDecimal,
        val balanceAfterClose: BigDecimal
    ) : DemoSettlementResult

    data class InvalidInput(
        val error: DemoSettlementError
    ) : DemoSettlementResult
}

/**
 * Рассчитывает результат закрытия линейной демо-позиции.
 *
 * Комиссии, проскальзывание, плечо и ликвидация не учитываются.
 * Баланс до и после закрытия может быть отрицательным.
 * Допустимость открытия новой позиции проверяется отдельно.
 */
object DemoSettlementCalculator {

    fun calculate(input: DemoSettlementInput): DemoSettlementResult {
        if (input.entryPrice <= BigDecimal.ZERO) {
            return DemoSettlementResult.InvalidInput(
                DemoSettlementError.INVALID_ENTRY_PRICE
            )
        }

        if (input.exitPrice <= BigDecimal.ZERO) {
            return DemoSettlementResult.InvalidInput(
                DemoSettlementError.INVALID_EXIT_PRICE
            )
        }

        if (input.quantity <= BigDecimal.ZERO) {
            return DemoSettlementResult.InvalidInput(
                DemoSettlementError.INVALID_QUANTITY
            )
        }

        val priceDifference = when (input.side) {
            PositionSide.BUY ->
                input.exitPrice.subtract(input.entryPrice)

            PositionSide.SELL ->
                input.entryPrice.subtract(input.exitPrice)
        }

        val profitAndLoss = priceDifference.multiply(input.quantity)
        val balanceAfterClose =
            input.balanceBeforeClose.add(profitAndLoss)

        return DemoSettlementResult.Calculated(
            profitAndLoss = profitAndLoss,
            balanceAfterClose = balanceAfterClose
        )
    }
}
