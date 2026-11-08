package com.aegistrade.app.domain.demo

import com.aegistrade.app.domain.risk.PositionSide
import com.aegistrade.app.domain.risk.RiskCalculator
import com.aegistrade.app.domain.risk.RiskInput
import com.aegistrade.app.domain.risk.RiskResult
import java.math.BigDecimal

/**
 * Открытая линейная демо-позиция.
 *
 * Все значения записываются в момент открытия и не должны
 * изменяться при закрытии.
 */
data class DemoPosition(
    val entryPrice: BigDecimal,
    val stopPrice: BigDecimal,
    val quantity: BigDecimal,
    val side: PositionSide
)

/**
 * Состояние счёта.
 *
 * balance — расчётный баланс после закрытых сделок.
 * Результат открытой позиции в него не включён.
 */
data class DemoAccount(
    val balance: BigDecimal,
    val openPosition: DemoPosition? = null
)

data class DemoOpenRequest(
    val entryPrice: BigDecimal,
    val stopPrice: BigDecimal,
    val quantity: BigDecimal,
    val side: PositionSide,
    val maxRiskPercent: BigDecimal
)

sealed interface DemoOpenResult {

    data class Opened(
        val account: DemoAccount,
        val risk: RiskResult.Accepted
    ) : DemoOpenResult

    data object PositionAlreadyOpen : DemoOpenResult

    data class RiskRejected(
        val reason: RiskResult
    ) : DemoOpenResult
}

sealed interface DemoCloseResult {

    data class Closed(
        val account: DemoAccount,
        val profitAndLoss: BigDecimal
    ) : DemoCloseResult

    data object NoOpenPosition : DemoCloseResult

    data class InvalidInput(
        val error: DemoSettlementError
    ) : DemoCloseResult
}

/**
 * Чистые операции над состоянием демо-счёта.
 *
 * Вызов не изменяет переданный объект: успешная операция
 * возвращает новое состояние. Сохранение и защита от
 * параллельных операций реализуются отдельно.
 */
object DemoAccountOperations {

    fun open(
        account: DemoAccount,
        request: DemoOpenRequest
    ): DemoOpenResult {
        if (account.openPosition != null) {
            return DemoOpenResult.PositionAlreadyOpen
        }

        val risk = RiskCalculator.calculate(
            RiskInput(
                balance = account.balance,
                entryPrice = request.entryPrice,
                stopPrice = request.stopPrice,
                quantity = request.quantity,
                side = request.side,
                maxRiskPercent = request.maxRiskPercent
            )
        )

        if (risk !is RiskResult.Accepted) {
            return DemoOpenResult.RiskRejected(risk)
        }

        val position = DemoPosition(
            entryPrice = request.entryPrice,
            stopPrice = request.stopPrice,
            quantity = request.quantity,
            side = request.side
        )

        return DemoOpenResult.Opened(
            account = account.copy(openPosition = position),
            risk = risk
        )
    }

    fun close(
        account: DemoAccount,
        exitPrice: BigDecimal
    ): DemoCloseResult {
        val position = account.openPosition
            ?: return DemoCloseResult.NoOpenPosition

        val settlement = DemoSettlementCalculator.calculate(
            DemoSettlementInput(
                balanceBeforeClose = account.balance,
                entryPrice = position.entryPrice,
                exitPrice = exitPrice,
                quantity = position.quantity,
                side = position.side
            )
        )

        return when (settlement) {
            is DemoSettlementResult.InvalidInput ->
                DemoCloseResult.InvalidInput(settlement.error)

            is DemoSettlementResult.Calculated ->
                DemoCloseResult.Closed(
                    account = account.copy(
                        balance = settlement.balanceAfterClose,
                        openPosition = null
                    ),
                    profitAndLoss = settlement.profitAndLoss
                )
        }
    }
}
