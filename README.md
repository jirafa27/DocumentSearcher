Для первого запуска проекта требуется:

1) Собрать докер контейнеры
В терминале выполнить:
docker-compose up -d 
2) Создать базу данных. 
Применить миграции к базе:
docker-compose exec app alembic upgrade head


