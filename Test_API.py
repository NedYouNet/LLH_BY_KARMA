from gigachat import GigaChat

# Твой правильный ключ
token = "MDFhMTFkMTQtMzFiMi03MDQ4LWFkMGEtYzFhNzUwNzk5YTMxOjIyZGQ0NmU0LTVjY2ItNGEyOC05ZTNmLTk3M2Q0MGNiZGI2YQ=="

print("Отправляем запрос в Сбер...")

try:
    # ДОБАВЛЕН ПАРАМЕТР model="GigaChat"
    with GigaChat(credentials=token, verify_ssl_certs=False, model="GigaChat-2") as giga:
        response = giga.chat({
            "messages": [
                {"role": "user", "content": "Скажи одно слово: Успех!"}
            ]
        })
        print("✅ ПОДКЛЮЧЕНО! Ответ GigaChat:", response.choices[0].message.content)
except Exception as e:
    print("❌ ОШИБКА:", e)