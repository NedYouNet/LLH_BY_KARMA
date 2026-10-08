<!-- fsp-frontend-libraries -->
## Фронтенд

Версии зафиксированы в `frontend/package-lock.json`; установка: `npm ci`. Ниже версии из проверенной установки этой сборки.

| Библиотека | Версия | Назначение |
|---|---|---|
| React / React DOM | 19.3.0 | Компоненты интерфейса и отображение приложения |
| Vite | 8.3.3 | Сервер разработки, прокси API и production-сборка |
| @vitejs/plugin-react | 6.1.2 | Поддержка React в Vite |
| Tailwind CSS / @tailwindcss/vite | 4.3.3 | Стили и сборка CSS |
| @monaco-editor/react | 4.7.0 | Редактор кода в серверном тесте |
| ESLint / @eslint/js | 10.12.0 / 10.0.1 | Проверка JavaScript |
| eslint-plugin-react-hooks | 7.1.1 | Проверка правил React Hooks и зависимостей эффектов |
| globals | 17.13.0 | Описание глобальных объектов браузера и Node для ESLint |

`@types/react` и `@types/react-dom` 19.3.0 помогают редактору кода. `eslint-plugin-react-refresh` 0.5.7 установлен в исходном проекте; текущая конфигурация ESLint его не включает. Клиент API написан на `fetch`, дополнительная библиотека HTTP не требуется.

