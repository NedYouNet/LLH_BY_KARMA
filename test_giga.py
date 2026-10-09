import json
from gigachat import GigaChat

# Импортируем ваши рабочие файлы
from invariants import TASK_INVARIANTS
from prompts import get_masking_system_prompt
import config


def test_tournament_generation():
    theme = "Киберпанк и хакерские атаки"

    # Жестко указываем ключи 3 задач разной сложности, которые мы добавили ранее
    task_ids = ["binary_search_1", "sliding_window_1", "graph_bfs_1"]

    print(f"Запуск генерации турнира. Тематика: {theme}")
    print("=" * 50)

    try:
        # Открываем единое соединение с GigaChat
        with GigaChat(credentials=config.GIGA_TOKEN, verify_ssl_certs=False, model="GigaChat-2-Pro") as giga:

            for t_id in task_ids:
                invariant = TASK_INVARIANTS.get(t_id)
                if not invariant:
                    print(f"Пропуск: инвариант {t_id} не найден в базе!")
                    continue

                print(f"\n⏳ Генерируем задачу уровня [{invariant['difficulty']}]...")

                user_prompt = f"""
                Тематика (общий сеттинг): {theme}
                Сложность: {invariant['difficulty']}
                Суть алгоритма: {invariant['math_core']}
                Вход: {invariant['inputs']}
                Вывод: {invariant['outputs']}
                Сгенерируй JSON.
                """

                # Отправляем запрос
                response = giga.chat({
                    "messages": [
                        {"role": "system", "content": get_masking_system_prompt()},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.8
                })

                # Чистим и парсим ответ
                raw_response = response.choices[0].message.content
                clean_json = raw_response.replace("```json", "").replace("```", "").strip()

                try:
                    ai_data = json.loads(clean_json)
                    print(f"✅ УСПЕХ!")
                    print(f"   Название: {ai_data.get('title')}")
                    # Выводим первые 80 символов легенды, чтобы не засорять консоль
                    print(f"   Легенда:  {ai_data.get('description', '')[:80]}...")
                except json.JSONDecodeError:
                    print("❌ ОШИБКА: Нейросеть сломала JSON структуру в этой задаче.")
                    print("Сырой текст ответа:")
                    print(raw_response)

    except Exception as e:
        print(f"Сетевая ошибка или неверный токен: {e}")


if __name__ == "__main__":
    test_tournament_generation()