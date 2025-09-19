import pytest

from app.core.utils.text_analyzer import TextAnalyzer


class TestTextAnalyzer:

    @pytest.fixture
    def analyzer(self):
        return TextAnalyzer()

    def test_normalize_text(self, analyzer):
        """Тест нормализации текста"""
        assert analyzer.normalize_text("Привет, мир!") == "привет мир"
        assert analyzer.normalize_text("  Много    пробелов  ") == "много пробелов"
        assert analyzer.normalize_text("Text123!@#") == "text123"

    def test_is_meaningful_word(self, analyzer):
        """Тест определения значимых слов"""
        # Значимые слова
        assert analyzer.is_meaningful_word("дом") is True
        assert analyzer.is_meaningful_word("красивый") is True
        assert analyzer.is_meaningful_word("работать") is True

        # Служебные слова
        assert analyzer.is_meaningful_word("в") is False
        assert analyzer.is_meaningful_word("и") is False
        assert analyzer.is_meaningful_word("не") is False

        # Короткие слова
        assert analyzer.is_meaningful_word("я") is False
        assert analyzer.is_meaningful_word("") is False

    def test_extract_meaningful_words(self, analyzer):
        """Тест извлечения значимых слов"""
        text = "В красивом доме живут люди"
        words = analyzer.extract_meaningful_words(text)

        # Должны остаться только значимые слова
        assert "красивый" in words  # прилагательное
        assert "дом" in words  # существительное
        assert "жить" in words  # глагол (лемма от "живут")
        assert "человек" in words  # лемма от "люди"

        # Служебные слова должны быть исключены
        assert "в" not in words

    def test_all_query_words_present(self, analyzer):
        """Тест проверки присутствия всех слов запроса"""
        query = "красивый дом"

        # Позитивный случай
        fragment1 = "В нашем красивом доме живут счастливые люди"
        assert analyzer.all_query_words_present(fragment1, query) is True

        # Негативный случай
        fragment2 = "Красивая машина стоит во дворе"
        assert analyzer.all_query_words_present(fragment2, query) is False
