"""
Анализатор текста для извлечения значимых слов
"""

import re
import string
from typing import List, Set

import pymorphy2


class TextAnalyzer:
    """Класс для морфологического анализа русского текста"""

    def __init__(self):
        self.morph = pymorphy2.MorphAnalyzer()

        # Служебные части речи, которые исключаем
        self.non_meaningful_pos = {
            "PREP",  # предлог (в, на, за)
            "CONJ",  # союз (и, или, но)
            "PRCL",  # частица (не, ли, же)
            "INTJ",  # междометие (ах, ой)
            "NPRO",  # местоимение (я, ты, он)
        }

    def normalize_text(self, text: str) -> str:
        """Нормализует текст: убирает пунктуацию и лишние пробелы"""
        if not text:
            return ""

        # Убираем пунктуацию
        text_no_punct = text.translate(str.maketrans("", "", string.punctuation))

        # Нормализуем пробелы и приводим к нижнему регистру
        normalized = re.sub(r"\s+", " ", text_no_punct).strip().lower()

        return normalized

    def is_meaningful_word(self, word: str) -> bool:
        """Проверяет, является ли слово значимым (не служебным)"""
        if not word or len(word) < 2:
            return False

        try:
            parsed = self.morph.parse(word)[0]
            return parsed.tag.POS not in self.non_meaningful_pos
        except Exception:
            # Если не удалось разобрать - считаем значимым
            return True

    def extract_meaningful_words(self, text: str) -> List[str]:
        """Извлекает только значимые слова из текста"""
        normalized_text = self.normalize_text(text)
        words = normalized_text.split()

        meaningful_words = []
        for word in words:
            if self.is_meaningful_word(word):
                try:
                    # Приводим к нормальной форме (лемматизация)
                    parsed = self.morph.parse(word)[0]
                    lemma = parsed.normal_form
                    meaningful_words.append(lemma)
                except Exception:
                    # Если лемматизация не удалась - используем исходное слово
                    meaningful_words.append(word)

        return meaningful_words

    def extract_meaningful_words_set(self, text: str) -> Set[str]:
        """Возвращает множество уникальных значимых слов"""
        return set(self.extract_meaningful_words(text))

    def all_query_words_present(self, fragment_text: str, query: str) -> bool:
        """Проверяет, что все значимые слова запроса есть во фрагменте"""
        query_words = self.extract_meaningful_words_set(query)
        fragment_words = self.extract_meaningful_words_set(fragment_text)

        if not query_words:
            return True  # Если запрос только из служебных слов

        return query_words.issubset(fragment_words)


# Создаем глобальный экземпляр для переиспользования
text_analyzer = TextAnalyzer()
