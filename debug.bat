@echo off
echo Запуск приложения в режиме отладки...
echo.

echo 1. Остановка существующих контейнеров
docker-compose -f docker-compose.debug.yml down

echo.
echo 2. Сборка и запуск контейнеров для отладки
docker-compose -f docker-compose.debug.yml up --build

echo.
echo 3. Для подключения отладчика:
echo    - Дождитесь сообщения "Отладочный сервер запущен на порту 5678"
echo    - Откройте Cursor
echo    - Перейдите в раздел "Run and Debug" (Ctrl+Shift+D)
echo    - Выберите "FastAPI Debug (Container)"
echo    - Нажмите F5 или кнопку "Start Debugging"
echo.
echo 4. Приложение будет доступно по адресу: http://localhost:8000
echo 5. API документация: http://localhost:8000/docs
