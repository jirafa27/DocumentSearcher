import pytest
from app.repositories.document_repository import DocumentRepository

class TestMergePhraseHighlights:
    
    def test_merge_simple_phrase(self):
        """Тест простого объединения фразы"""
        repo = DocumentRepository(None)
        input_html = '<mark>отдел</mark> <mark>продаж</mark>'
        expected = '<mark>отдел продаж</mark>'
        result = repo._merge_phrase_highlights(input_html)
        assert result == expected
    
    def test_merge_with_short_word(self):
        """Тест с коротким словом между"""
        repo = DocumentRepository(None)
        input_html = '<mark>отдел</mark> по <mark>продаж</mark>'
        expected = '<mark>отдел по продаж</mark>'
        result = repo._merge_phrase_highlights(input_html)
        assert result == expected
    
    def test_no_merge_with_long_word(self):
        """Тест: длинные слова НЕ объединяются"""
        repo = DocumentRepository(None)
        input_html = '<mark>отдел</mark> кадров <mark>продаж</mark>'
        expected = '<mark>отдел</mark> кадров <mark>продаж</mark>'  # Не изменилось
        result = repo._merge_phrase_highlights(input_html)
        assert result == expected
    
    def test_multiple_merges(self):
        """Тест множественных объединений"""
        repo = DocumentRepository(None)
        input_html = '<mark>отдел</mark> <mark>продаж</mark> и <mark>отдел</mark> по <mark>рекламе</mark>'
        expected = '<mark>отдел продаж и отдел по рекламе</mark>'
        result = repo._merge_phrase_highlights(input_html)
        assert result == expected
    
    def test_empty_input(self):
        """Тест пустого ввода"""
        repo = DocumentRepository(None)
        result = repo._merge_phrase_highlights('')
        assert result == ''
    
    def test_no_marks(self):
        """Тест без тегов mark"""
        repo = DocumentRepository(None)
        input_html = 'отдел продаж'
        result = repo._merge_phrase_highlights(input_html)
        assert result == 'отдел продаж'
    
    def test_single_mark(self):
        """Тест с одним тегом mark"""
        repo = DocumentRepository(None)
        input_html = '<mark>отдел</mark> продаж'
        result = repo._merge_phrase_highlights(input_html)
        assert result == '<mark>отдел</mark> продаж'
    
    def test_only_spaces_between(self):
        """Тест только пробелов между тегами"""
        repo = DocumentRepository(None)
        input_html = '<mark>отдел</mark>   <mark>продаж</mark>'
        expected = '<mark>отдел   продаж</mark>'
        result = repo._merge_phrase_highlights(input_html)
        assert result == expected
    
    def test_edge_case_boundary_words(self):
        """Тест граничных случаев (3 символа)"""
        repo = DocumentRepository(None)
        input_html = '<mark>отдел</mark> или <mark>продаж</mark>'  # "или" = 3 символа
        expected = '<mark>отдел или продаж</mark>'
        result = repo._merge_phrase_highlights(input_html)
        assert result == expected
        
        input_html2 = '<mark>отдел</mark> тест <mark>продаж</mark>'  # "тест" = 4 символа
        expected2 = '<mark>отдел</mark> тест <mark>продаж</mark>'  # Не объединяется
        result2 = repo._merge_phrase_highlights(input_html2)
        assert result2 == expected2

    def test_merge_with_punctuation(self):
        """Тест с пунктуацией"""
        repo = DocumentRepository(None)
        input_html = '<mark>отдел</mark>, <mark>продаж</mark>'
        expected = '<mark>отдел, продаж</mark>'
        result = repo._merge_phrase_highlights(input_html)
        assert result == expected
