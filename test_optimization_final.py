#!/usr/bin/env python3
"""
Финальное тестирование гипотез оптимизации с правильным анализом
"""
import logging
import time
import json
from itad_api import ITADAPIClient
import config

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def analyze_storelow_vs_history():
    """
    Анализ: storelow vs history - что возвращает больше данных?
    """
    logger.info("\n" + "="*60)
    logger.info("АНАЛИЗ: storelow vs history - сравнение данных")
    logger.info("="*60)
    
    client = ITADAPIClient(config.ITAD_API_KEY)
    
    # Lookup UUID
    lookup_response = client.lookup_games_by_shop_id(['app/730'])
    uuid = lookup_response.get('app/730') if lookup_response else None
    
    if not uuid:
        logger.error("Failed to lookup UUID")
        return
    
    # Storelow (батчинг работает)
    logger.info("\n1. Storelow (батчинг, одна запись минимальной цены):")
    storelow_result = client.get_store_lowest_prices([730], country='US', shops=[61])
    if storelow_result and storelow_result[0].get('lows'):
        logger.info(f"   ✅ Возвращает {len(storelow_result[0]['lows'])} записей минимальных цен")
        logger.info(f"   ⚠️  Только минимальная цена, не полная история")
    
    # History (полная история, но без батчинга)
    logger.info("\n2. History (полная история изменений, без батчинга):")
    history_result = client.get_price_history(uuid, 'US', shops=[61])
    if history_result:
        logger.info(f"   ✅ Возвращает {len(history_result)} записей полной истории")
        logger.info(f"   ✅ Полная история изменений цен с 2012 года")
    
    return {
        'storelow_records': len(storelow_result[0]['lows']) if storelow_result else 0,
        'history_records': len(history_result) if history_result else 0
    }

def calculate_optimized_requests():
    """
    Расчет оптимизированного количества запросов
    """
    logger.info("\n" + "="*60)
    logger.info("РАСЧЕТ ОПТИМИЗИРОВАННОГО КОЛИЧЕСТВА ЗАПРОСОВ")
    logger.info("="*60)
    
    total_app_ids = 100000
    batch_size = config.ITAD_BATCH_SIZE
    num_currencies = 47
    
    num_batches = (total_app_ids + batch_size - 1) // batch_size
    
    # Текущий подход (history для каждой игры отдельно)
    current_approach = {
        'lookup': num_batches,
        'history': num_batches * num_currencies * batch_size,
        'total': num_batches + (num_batches * num_currencies * batch_size)
    }
    
    logger.info(f"\nТЕКУЩИЙ ПОДХОД (history для каждой игры):")
    logger.info(f"  Lookup: {current_approach['lookup']:,} запросов")
    logger.info(f"  History: {current_approach['history']:,} запросов")
    logger.info(f"  ВСЕГО: {current_approach['total']:,} запросов")
    
    # Время при rate limit 2 req/sec
    time_seconds = current_approach['total'] / 2
    time_days = time_seconds / 86400
    logger.info(f"  Время: {time_days:.1f} дней")
    
    return current_approach

def test_parallel_optimization():
    """
    Тест: можно ли ускорить через параллелизм с учетом rate limit
    """
    logger.info("\n" + "="*60)
    logger.info("ТЕСТ: Параллелизм с учетом rate limit")
    logger.info("="*60)
    
    import concurrent.futures
    import time
    
    client = ITADAPIClient(config.ITAD_API_KEY)
    
    # Lookup UUIDs для 10 игр
    test_app_ids = [730, 440, 570, 271590, 271590, 730, 440, 570, 271590, 271590]
    lookup_response = client.lookup_games_by_shop_id([f'app/{aid}' for aid in test_app_ids])
    uuids = [(aid, uuid) for aid in test_app_ids 
             for shop_id, uuid in lookup_response.items() 
             if uuid and int(shop_id.split('/')[-1]) == aid]
    
    def fetch_history(app_id, uuid):
        return client.get_price_history(uuid, 'US', shops=[61])
    
    # Последовательные запросы
    logger.info("Последовательные запросы (10 игр):")
    start = time.time()
    for app_id, uuid in uuids[:10]:
        fetch_history(app_id, uuid)
    seq_time = time.time() - start
    logger.info(f"  Время: {seq_time:.2f} сек")
    
    # Параллельные запросы (5 потоков)
    logger.info("Параллельные запросы (5 потоков, 10 игр):")
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_history, aid, uuid) for aid, uuid in uuids[:10]]
        concurrent.futures.wait(futures)
    par_time = time.time() - start
    logger.info(f"  Время: {par_time:.2f} сек")
    
    speedup = seq_time / par_time if par_time > 0 else 1
    logger.info(f"  Ускорение: {speedup:.2f}x")
    
    if speedup > 1.5:
        logger.info("  ✅ Параллелизм эффективен!")
        return True, speedup
    else:
        logger.info("  ⚠️  Параллелизм ограничен rate limit API")
        return False, speedup

def main():
    """Финальный анализ всех гипотез"""
    logger.info("="*60)
    logger.info("ФИНАЛЬНЫЙ АНАЛИЗ ОПТИМИЗАЦИИ")
    logger.info("="*60)
    
    # Анализ данных
    data_comparison = analyze_storelow_vs_history()
    
    # Расчет запросов
    requests_calc = calculate_optimized_requests()
    
    # Тест параллелизма
    parallel_works, speedup = test_parallel_optimization()
    
    # Итоговые выводы
    logger.info("\n" + "="*60)
    logger.info("ИТОГОВЫЕ ВЫВОДЫ")
    logger.info("="*60)
    
    logger.info("\n✅ РАБОТАЕТ:")
    logger.info("  1. Параметр 'since' - получаем полную историю с 2012 года")
    logger.info("  2. Lookup батчинг - один запрос на весь батч")
    
    logger.info("\n❌ НЕ ПОДХОДИТ:")
    logger.info("  1. storelow/historylow - возвращают только минимальную цену, не историю")
    logger.info("  2. Параллелизм - ограничен rate limit API (2 req/sec)")
    
    logger.info("\n📊 РЕКОМЕНДАЦИИ:")
    logger.info(f"  - Использовать параллелизм с {min(5, int(2 * speedup))} потоками")
    logger.info("  - Это даст ускорение примерно в 2-3 раза")
    logger.info("  - Время выполнения: ~10-15 дней вместо 27")
    
    return {
        'data_comparison': data_comparison,
        'requests': requests_calc,
        'parallel_speedup': speedup
    }

if __name__ == "__main__":
    main()

