import pytest
from app.repositories.document_repository import DocumentRepository


class TestParseHeadlineFragments:
    
    @pytest.fixture
    def repository(self):
        return DocumentRepository(None)
    
    def test_single_highlight(self, repository):
        """Тест одного выделения"""
        html = "Отчет по <mark>продажам</mark> за июнь"
        context_size_before = 4
        context_size_after = 4
        
        fragments = repository._parse_ts_headline_fragments(html, context_size_before, context_size_after)
        print(fragments)
        assert len(fragments) == 1
        assert fragments[0].text == "продажам"
        assert "Отчет по" in fragments[0].context.text
        assert "за июнь" in fragments[0].context.text
    
    def test_multiple_highlights(self, repository):
        """Тест множественных выделений"""
        html = "В <mark>отдел</mark> продаж и <mark>отдел</mark> рекламы"
        context_size_before = 3
        context_size_after = 3
        
        fragments = repository._parse_ts_headline_fragments(html, context_size_before, context_size_after)
        
        assert len(fragments) == 2
        assert fragments[0].text == "отдел"
        assert fragments[1].text == "отдел"
        assert fragments[0].context.text != fragments[1].context.text
    
    def test_empty_input(self, repository):
        """Тест пустого ввода"""
        fragments = repository._parse_ts_headline_fragments("", 10, 10)
        assert fragments == []

    
    def test_no_highlights(self, repository):
        """Тест без выделений"""
        html = "Обычный текст без выделений"
        fragments = repository._parse_ts_headline_fragments(html, 10, 10)
        assert fragments == []
    
    def test_context_size_limits(self, repository):
        """Тест ограничений размера контекста"""
        html = "Один два три <mark>четыре</mark> пять шесть семь"
        
        # Маленький контекст
        fragments = repository._parse_ts_headline_fragments(html, 2, 2)
        context_words = fragments[0].context.text.split()
        assert len(context_words) == 5
        
        # Большой контекст
        fragments = repository._parse_ts_headline_fragments(html, 10, 10)
        assert "Один" in fragments[0].context.text
        assert "семь" in fragments[0].context.text
        assert len(fragments[0].context.text.split()) == len(html.split(" "))
    
    def test_highlight_positions(self, repository):
        """Тест правильности позиций выделения"""
        html = "Начало <mark>выделение</mark> конец"
        fragments = repository._parse_ts_headline_fragments(html, 6, 6)
        
        fragment = fragments[0]
        context = fragment.context
        
        # Проверяем что highlight_start указывает на правильную позицию
        highlighted_part = context.text[
            context.highlight_start:
            context.highlight_start + context.highlight_length
        ]
        assert highlighted_part == fragment.text
    
    def test_html_tags_removal(self, repository):
        """Тест удаления HTML тегов из контекста"""
        html = "<mark>первое</mark> слово <mark>второе</mark> слово"
        fragments = repository._parse_ts_headline_fragments(html, 8, 8)
        
        # В контексте не должно быть HTML тегов
        for fragment in fragments:
            assert "<mark>" not in fragment.context.text
            assert "</mark>" not in fragment.context.text
    
    
    def test_edge_case_start_end(self, repository):
        """Тест выделений в начале и конце"""
        # В начале
        html = "<mark>начало</mark> текста документа"
        fragments = repository._parse_ts_headline_fragments(html, 4, 4)
        assert len(fragments) == 1
        
        # В конце  
        html = "текста документа <mark>конец</mark>"
        fragments = repository._parse_ts_headline_fragments(html, 4, 4)
        assert len(fragments) == 1
    
    def test_long_highlight(self, repository):
        """Тест длинного выделения"""
        html = "Текст <mark>очень длинное выделение с множеством слов</mark> текст"
        fragments = repository._parse_ts_headline_fragments(html, 4, 4)
        
        fragment = fragments[0]
        assert fragment.text == "очень длинное выделение с множеством слов"
        assert fragment.context.highlight_length == len(fragment.text)
    
    @pytest.mark.parametrize("context_size_before", [1, 2, 5, 10, 20])
    @pytest.mark.parametrize("context_size_after", [1, 2, 5, 10, 20])
    def test_various_context_sizes(self, repository, context_size_before, context_size_after):
        """Тест различных размеров контекста"""
        html = "a b c d <mark>выделение</mark> e f g h i j"
        fragments = repository._parse_ts_headline_fragments(html, context_size_before, context_size_after)
        
        assert len(fragments) == 1
        context_words = fragments[0].context.text.split()
        # Контекст не должен быть больше чем ожидается
        assert len(context_words) <= context_size_before + context_size_after + 1


    def test_context_whitespces_between_words(self, repository):
        """Тест пробелов между словами в контексте"""
        html = "a b c d <mark>выделение</mark> e f g h i j"
        fragments = repository._parse_ts_headline_fragments(html, 4, 6)
        assert fragments[0].context.text == "a b c d выделение e f g h i j"


    def test_context_with_big_and_zero_length(self, repository):
        """Тест контекста с большой длиной и нулевой длиной"""
        html = "a b c d <mark>выделение</mark> e f g h i j"
        fragments = repository._parse_ts_headline_fragments(html, 1000, 1000)
        assert fragments[0].context.text == "a b c d выделение e f g h i j"

        fragments = repository._parse_ts_headline_fragments(html, 0, 0)
        assert fragments[0].context.text == "выделение"


    def test_amount_of_symbols_in_context(self, repository):
        """Тест количества символов в контексте после парсинга"""
        html = "a b c d      <mark>выделение</mark> e f g h i j"
        len_of_context = len(html) - len("<mark></mark>")
        fragments = repository._parse_ts_headline_fragments(html, 100, 100)
        assert len(fragments[0].context.text) == len_of_context


    def test_amount_of_symbols_in_highlight(self, repository):
        """Тест количества символов в выделении после парсинга"""
        html = "a b c d      <mark>выделение</mark> e f g h i j"
        len_of_highlight = len("выделение")
        fragments = repository._parse_ts_headline_fragments(html, 100, 100)
        assert fragments[0].context.highlight_length == len_of_highlight





