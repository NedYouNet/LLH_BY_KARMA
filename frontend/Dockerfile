# Сборка фронтенда для запуска всего проекта одной командой: docker compose up --build
# Шаг 1: собираем React-приложение в статические файлы (папка dist)
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Шаг 2: отдаём dist через nginx, а запросы /api/... пересылаем бэкенду
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
