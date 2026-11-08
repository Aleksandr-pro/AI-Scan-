package com.aegistrade.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.aegistrade.app.domain.input.DecimalInputParser
import com.aegistrade.app.domain.risk.PositionSide
import com.aegistrade.app.domain.risk.RiskCalculator
import com.aegistrade.app.domain.risk.RiskInput
import com.aegistrade.app.domain.risk.RiskInputError
import com.aegistrade.app.domain.risk.RiskResult

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            MaterialTheme(colorScheme = darkColorScheme()) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    RiskScreen()
                }
            }
        }
    }
}

@Composable
private fun RiskScreen() {
    var balance by rememberSaveable { mutableStateOf("") }
    var entryPrice by rememberSaveable { mutableStateOf("") }
    var stopPrice by rememberSaveable { mutableStateOf("") }
    var quantity by rememberSaveable { mutableStateOf("") }
    var maxRiskPercent by rememberSaveable { mutableStateOf("") }
    var isBuy by rememberSaveable { mutableStateOf(true) }

    // Результат не сохраняется при пересоздании экрана:
    // после восстановления пользователь может пересчитать его.
    var resultMessage by remember { mutableStateOf<String?>(null) }
    var isError by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(
            text = "AEGIS Trade",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold
        )

        Text(
            text = "Расчёт риска линейной позиции",
            style = MaterialTheme.typography.titleMedium
        )

        Text(
            text = "Демо-режим: приложение не подключено к биржам " +
                "и не совершает сделки.",
            style = MaterialTheme.typography.bodyMedium
        )

        RiskField(
            value = balance,
            label = "Баланс",
            onValueChange = {
                balance = it
                resultMessage = null
            }
        )

        RiskField(
            value = entryPrice,
            label = "Цена входа",
            onValueChange = {
                entryPrice = it
                resultMessage = null
            }
        )

        RiskField(
            value = stopPrice,
            label = "Стоп-цена",
            onValueChange = {
                stopPrice = it
                resultMessage = null
            }
        )

        RiskField(
            value = quantity,
            label = "Количество актива",
            onValueChange = {
                quantity = it
                resultMessage = null
            }
        )

        RiskField(
            value = maxRiskPercent,
            label = "Максимальный риск, %",
            onValueChange = {
                maxRiskPercent = it
                resultMessage = null
            }
        )

        Text(
            text = "Направление",
            style = MaterialTheme.typography.titleSmall
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            DirectionButton(
                text = "Покупка",
                selected = isBuy,
                modifier = Modifier.weight(1f),
                onClick = {
                    isBuy = true
                    resultMessage = null
                }
            )

            DirectionButton(
                text = "Продажа",
                selected = !isBuy,
                modifier = Modifier.weight(1f),
                onClick = {
                    isBuy = false
                    resultMessage = null
                }
            )
        }

        Button(
            modifier = Modifier.fillMaxWidth(),
            onClick = {
                val parsedBalance = DecimalInputParser.parse(balance)
                val parsedEntry = DecimalInputParser.parse(entryPrice)
                val parsedStop = DecimalInputParser.parse(stopPrice)
                val parsedQuantity = DecimalInputParser.parse(quantity)
                val parsedLimit = DecimalInputParser.parse(maxRiskPercent)

                if (
                    parsedBalance == null ||
                    parsedEntry == null ||
                    parsedStop == null ||
                    parsedQuantity == null ||
                    parsedLimit == null
                ) {
                    isError = true
                    resultMessage =
                        "Проверьте заполнение полей. Введите числа без " +
                        "пробелов: до 18 цифр перед разделителем и " +
                        "до 8 после него."
                } else {
                    val input = RiskInput(
                        balance = parsedBalance,
                        entryPrice = parsedEntry,
                        stopPrice = parsedStop,
                        quantity = parsedQuantity,
                        side = if (isBuy) {
                            PositionSide.BUY
                        } else {
                            PositionSide.SELL
                        },
                        maxRiskPercent = parsedLimit
                    )

                    when (val result = RiskCalculator.calculate(input)) {
                        is RiskResult.Accepted -> {
                            isError = false
                            resultMessage = buildString {
                                appendLine("Лимит риска не превышен.")
                                appendLine(
                                    "Плановый убыток: " +
                                        result.plannedLoss.toPlainString()
                                )
                                append(
                                    "Риск: примерно " +
                                        "${result.riskPercent.toPlainString()}%"
                                )
                            }
                        }

                        is RiskResult.LimitExceeded -> {
                            isError = true
                            resultMessage = buildString {
                                appendLine("Лимит риска превышен.")
                                appendLine(
                                    "Плановый убыток: " +
                                        result.plannedLoss.toPlainString()
                                )
                                appendLine(
                                    "Риск: примерно " +
                                        "${result.riskPercent.toPlainString()}%"
                                )
                                append(
                                    "Лимит: " +
                                        "${result.maxRiskPercent.toPlainString()}%"
                                )
                            }
                        }

                        is RiskResult.InvalidInput -> {
                            isError = true
                            resultMessage = inputErrorMessage(result.error)
                        }
                    }
                }
            }
        ) {
            Text("Рассчитать риск")
        }

        resultMessage?.let { message ->
            Text(
                text = message,
                color = if (isError) {
                    MaterialTheme.colorScheme.error
                } else {
                    MaterialTheme.colorScheme.primary
                },
                style = MaterialTheme.typography.bodyLarge
            )
        }

        Text(
            text = "Баланс и цены указываются в одной валюте, " +
                "количество — в единицах актива. Комиссии, " +
                "проскальзывание, плечо и ликвидация не учитываются. " +
                "Фактический убыток может превысить плановый.",
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.padding(top = 8.dp, bottom = 16.dp)
        )
    }
}

@Composable
private fun RiskField(
    value: String,
    label: String,
    onValueChange: (String) -> Unit
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        modifier = Modifier.fillMaxWidth(),
        label = { Text(label) },
        singleLine = true,
        keyboardOptions = KeyboardOptions(
            keyboardType = KeyboardType.Decimal
        )
    )
}

@Composable
private fun DirectionButton(
    text: String,
    selected: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    if (selected) {
        Button(
            modifier = modifier,
            onClick = onClick
        ) {
            Text(text)
        }
    } else {
        OutlinedButton(
            modifier = modifier,
            onClick = onClick
        ) {
            Text(text)
        }
    }
}

private fun inputErrorMessage(error: RiskInputError): String {
    return when (error) {
        RiskInputError.INVALID_BALANCE ->
            "Баланс должен быть больше нуля."

        RiskInputError.INVALID_ENTRY_PRICE ->
            "Цена входа должна быть больше нуля."

        RiskInputError.INVALID_STOP_PRICE ->
            "Стоп-цена должна быть больше нуля."

        RiskInputError.INVALID_QUANTITY ->
            "Количество должно быть больше нуля."

        RiskInputError.INVALID_MAX_RISK_PERCENT ->
            "Лимит риска должен быть больше 0% и не больше 100%."

        RiskInputError.INVALID_STOP_DIRECTION ->
            "Проверьте стоп-цену: для покупки она должна быть ниже " +
                "цены входа, для продажи — выше."
    }
}
