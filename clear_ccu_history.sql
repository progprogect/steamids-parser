-- Очистка таблицы ccu_history для освобождения места на диске
-- Выполнить этот SQL запрос в Railway PostgreSQL

-- Проверка размера и количества записей перед очисткой
SELECT 
    pg_size_pretty(pg_total_relation_size('ccu_history')) as total_size,
    pg_size_pretty(pg_relation_size('ccu_history')) as table_size,
    (SELECT COUNT(*) FROM ccu_history) as row_count;

-- Очистка таблицы (TRUNCATE быстрее чем DELETE и сразу освобождает место)
TRUNCATE TABLE ccu_history RESTART IDENTITY CASCADE;

-- Проверка результата
SELECT 
    pg_size_pretty(pg_total_relation_size('ccu_history')) as total_size_after,
    pg_size_pretty(pg_relation_size('ccu_history')) as table_size_after,
    (SELECT COUNT(*) FROM ccu_history) as row_count_after;

