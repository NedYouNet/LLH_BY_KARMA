import re

ENABLED = True

def _tokenize(text: str) -> set:
    """Очищает текст и разбивает на уникальные слова (токены)."""
    if not text:
        return set()
    # Убираем знаки препинания и приводим к нижнему регистру
    clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
    return set(clean_text.split())

def text_similarity(query: str, candidate_text: str) -> float:
    """
    Быстрый локальный матчинг без LLM (вызывается для каждого кандидата).
    Считает процент покрытия требований вакансии словами из резюме.
    Возвращает число от 0.0 до 1.0.
    """
    try:
        query_tokens = _tokenize(query)
        candidate_tokens = _tokenize(candidate_text)
        
        if not query_tokens:
            return 0.0
            
        # Считаем, сколько слов из запроса (вакансии) есть в тексте кандидата
        overlap = query_tokens.intersection(candidate_tokens)
        
        # Рассчитываем коэффициент покрытия
        score = len(overlap) / len(query_tokens)
        
        return round(score, 3)
    except Exception:
        # Ошибка внутри функции не страшна: компонента просто выпадает из расчёта
        return 0.0
