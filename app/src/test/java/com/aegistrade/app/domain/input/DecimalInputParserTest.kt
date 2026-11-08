package com.aegistrade.app.domain.input

import java.math.BigDecimal
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class DecimalInputParserTest {

    private fun assertParsed(expected: String, input: String) {
        val actual = DecimalInputParser.parse(input)

        requireNotNull(actual) {
            "Expected '$input' to be parsed"
        }

        assertEquals(
            "Unexpected value for '$input'",
            0,
            BigDecimal(expected).compareTo(actual)
        )
    }

    @Test
    fun parsesIntegerAndZero() {
        assertParsed("10", "10")
        assertParsed("0", "0")
        assertParsed("1", "0001")
    }

    @Test
    fun parsesDecimalWithDotOrComma() {
        assertParsed("10.5", "10.5")
        assertParsed("10.5", "10,5")
        assertParsed("0.00000001", "0,00000001")
    }

    @Test
    fun acceptsMaximumNumberOfDigits() {
        assertParsed(
            "123456789012345678.12345678",
            "123456789012345678.12345678"
        )
    }

    @Test
    fun rejectsTooManyDigits() {
        assertNull(DecimalInputParser.parse("1234567890123456789"))
        assertNull(DecimalInputParser.parse("1.123456789"))
    }

    @Test
    fun rejectsEmptyAndIncompleteValues() {
        assertNull(DecimalInputParser.parse(""))
        assertNull(DecimalInputParser.parse(".5"))
        assertNull(DecimalInputParser.parse(",5"))
        assertNull(DecimalInputParser.parse("5."))
        assertNull(DecimalInputParser.parse("5,"))
    }

    @Test
    fun rejectsSignsSpacesAndScientificNotation() {
        listOf(
            "-1",
            "+1",
            " 1",
            "1 ",
            "1 000",
            "1e3",
            "1E3"
        ).forEach { value ->
            assertNull("Should reject '$value'", DecimalInputParser.parse(value))
        }
    }

    @Test
    fun rejectsMultipleSeparatorsAndNonDigits() {
        listOf(
            "1.2.3",
            "1,2,3",
            "1,2.3",
            "abc",
            "1a",
            "١٢"
        ).forEach { value ->
            assertNull("Should reject '$value'", DecimalInputParser.parse(value))
        }
    }
}
