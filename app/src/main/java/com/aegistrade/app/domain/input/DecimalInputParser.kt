package com.aegistrade.app.domain.input

import java.math.BigDecimal

/**
 * Разбирает положительную десятичную запись без знака.
 *
 * Принимает:
 * - от 1 до 18 цифр до разделителя;
 * - при наличии разделителя — от 1 до 8 цифр после него;
 * - точку или запятую как десятичный разделитель.
 *
 * Ноль допускается на этом этапе: проверка допустимости
 * значения выполняется отдельно в RiskCalculator.
 */
object DecimalInputParser {

    private val pattern = Regex("""[0-9]{1,18}(\.[0-9]{1,8})?""")

    fun parse(value: String): BigDecimal? {
        val normalized = value.replace(',', '.')

        if (!pattern.matches(normalized)) {
            return null
        }

        return normalized.toBigDecimalOrNull()
    }
}
