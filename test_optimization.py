#!/usr/bin/env python3
"""
Тестирование гипотез оптимизации ITAD API
"""
import logging
import time
import json
from itad_api import ITADAPIClient
import config

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Тестовые данные
test_app_ids = [730, 440]
test_currencies = ['USD', 'EUR', 'GBP']  # Тестируем на 3 валютах

def test_hypothesis_1_storelow_batching():
    """
    Гипотеза 1: Использовать /games/storelow/v2 для батчинга
    Этот эндпоинт принимает список UUID и может вернуть историю для нескольких игр сразу
    """
    logger.info("\n" + "="*60)
    logger.info("ГИПОТЕЗА 1: Использование /games/storelow/v2 для батчинга")
    logger.info("="*60)
    
    client = ITADAPIClient(config.ITAD_API_KEY)
    
    # Lookup UUIDs
    game_ids_list = [f"steam/app/{app_id}" for app_id in test_app_ids]
    lookup_response = client.lookup_games_by_shop_id(game_ids_list)
    
    if not lookup_response:
        logger.error("Failed to lookup UUIDs")
        return False
    
    uuids = [uuid for uuid in lookup_response.values() if uuid]
    logger.info(f"Found {len(uuids)} UUIDs: {uuids[:2]}")
    
    # Тест storelow для одной валюты
    start_time = time.time()
    result = client.get_store_lowest_prices(test_app_ids, country='US', shops=[config.STEAM_SHOP_ID])
    elapsed = time.time() - start_time
    
    if result:
        logger.info(f"✅ Успешно! Получено {len(result)} результатов за {elapsed:.2f} сек")
        logger.info(f"   Структура ответа: {type(result)}")
        if result and len(result) > 0:
            logger.info(f"   Пример записи: {json.dumps(result[0], indent=2)[:200]}...")
        return True, elapsed, len(result)
    else:
        logger.error("❌ Не удалось получить данные")
        return False, elapsed, 0

def test_hypothesis_2_historylow_batching():
    """
    Гипотеза 2: Использовать /games/historylow/v1 для батчинга
    Этот эндпоинт принимает список UUID и может вернуть минимальные цены для нескольких игр
    """
    logger.info("\n" + "="*60)
    logger.info("ГИПОТЕЗА 2: Использование /games/historylow/v1 для батчинга")
    logger.info("="*60)
    
    client = ITADAPIClient(config.ITAD_API_KEY)
    
    # Lookup UUIDs
    game_ids_list = [f"steam/app/{app_id}" for app_id in test_app_ids]
    lookup_response = client.lookup_games_by_shop_id(game_ids_list)
    
    if not lookup_response:
        logger.error("Failed to lookup UUIDs")
        return False
    
    uuids = [uuid for uuid in lookup_response.values() if uuid]
    logger.info(f"Found {len(uuids)} UUIDs: {uuids[:2]}")
    
    # Тест historylow для одной валюты
    start_time = time.time()
    result = client.get_lowest_price_history(test_app_ids, country='US')
    elapsed = time.time() - start_time
    
    if result:
        logger.info(f"✅ Успешно! Получено {len(result)} результатов за {elapsed:.2f} сек")
        logger.info(f"   Структура ответа: {type(result)}")
        if result and len(result) > 0:
            logger.info(f"   Пример записи: {json.dumps(result[0], indent=2)[:200]}...")
        return True, elapsed, len(result)
    else:
        logger.error("❌ Не удалось получить данные")
        return False, elapsed, 0

def test_hypothesis_3_history_with_since():
    """
    Гипотеза 3: Проверить работает ли параметр since для получения полной истории
    """
    logger.info("\n" + "="*60)
    logger.info("ГИПОТЕЗА 3: Проверка параметра 'since' для полной истории")
    logger.info("="*60)
    
    client = ITADAPIClient(config.ITAD_API_KEY)
    
    # Lookup UUID для одной игры
    lookup_response = client.lookup_games_by_shop_id(['app/730'])
    if not lookup_response or not lookup_response.get('app/730'):
        logger.error("Failed to lookup UUID")
        return False
    
    uuid = lookup_response['app/730']
    logger.info(f"UUID для app 730: {uuid}")
    
    # Тест без since (по умолчанию 3 месяца)
    start_time = time.time()
    result_no_since = client._request('/games/history/v2', params={
        'id': uuid,
        'country': 'US',
        'shops': '61'
    })
    elapsed_no_since = time.time() - start_time
    
    # Тест с since (с 2012 года)
    start_time = time.time()
    result_with_since = client._request('/games/history/v2', params={
        'id': uuid,
        'country': 'US',
        'shops': '61',
        'since': '2012-01-01T00:00:00Z'
    })
    elapsed_with_since = time.time() - start_time
    
    if result_no_since and result_with_since:
        count_no_since = len(result_no_since) if isinstance(result_no_since, list) else 0
        count_with_since = len(result_with_since) if isinstance(result_with_since, list) else 0
        
        logger.info(f"✅ Без 'since': {count_no_since} записей за {elapsed_no_since:.2f} сек")
        logger.info(f"✅ С 'since': {count_with_since} записей за {elapsed_with_since:.2f} сек")
        logger.info(f"   Разница: {count_with_since - count_no_since} записей")
        
        if count_with_since > count_no_since:
            logger.info("   ✅ Параметр 'since' работает - получаем больше данных!")
            return True, count_with_since, count_no_since
        else:
            logger.warning("   ⚠️  Параметр 'since' не увеличил количество данных")
            return False, count_with_since, count_no_since
    else:
        logger.error("❌ Не удалось получить данные")
        return False, 0, 0

def test_hypothesis_4_parallel_requests():
    """
    Гипотеза 4: Проверить можно ли делать параллельные запросы
    """
    logger.info("\n" + "="*60)
    logger.info("ГИПОТЕЗА 4: Тестирование параллельных запросов")
    logger.info("="*60)
    
    import concurrent.futures
    
    client = ITADAPIClient(config.ITAD_API_KEY)
    
    # Lookup UUIDs
    lookup_response = client.lookup_games_by_shop_id(['app/730', 'app/440'])
    if not lookup_response:
        logger.error("Failed to lookup UUIDs")
        return False
    
    uuids = {app_id: uuid for shop_id, uuid in lookup_response.items() 
             for app_id in [int(shop_id.split('/')[-1])] if uuid}
    
    def fetch_history(app_id, uuid):
        start = time.time()
        result = client.get_price_history(uuid, 'US', shops=[config.STEAM_SHOP_ID])
        elapsed = time.time() - start
        return app_id, result, elapsed
    
    # Последовательные запросы
    logger.info("Последовательные запросы:")
    start_time = time.time()
    sequential_results = []
    for app_id, uuid in uuids.items():
        app_id, result, elapsed = fetch_history(app_id, uuid)
        sequential_results.append((app_id, result, elapsed))
    sequential_time = time.time() - start_time
    
    logger.info(f"   Время: {sequential_time:.2f} сек")
    
    # Параллельные запросы (2 потока)
    logger.info("Параллельные запросы (2 потока):")
    start_time = time.time()
    parallel_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(fetch_history, app_id, uuid) 
                   for app_id, uuid in uuids.items()]
        for future in concurrent.futures.as_completed(futures):
            parallel_results.append(future.result())
    parallel_time = time.time() - start_time
    
    logger.info(f"   Время: {parallel_time:.2f} сек")
    
    speedup = sequential_time / parallel_time if parallel_time > 0 else 0
    logger.info(f"   Ускорение: {speedup:.2f}x")
    
    if speedup > 1.2:
        logger.info("   ✅ Параллелизм работает эффективно!")
        return True, speedup
    else:
        logger.warning("   ⚠️  Параллелизм не дает значительного ускорения (возможно rate limit)")
        return False, speedup

def test_hypothesis_5_check_other_endpoints():
    """
    Гипотеза 5: Проверить другие эндпоинты которые могут поддерживать батчинг
    """
    logger.info("\n" + "="*60)
    logger.info("ГИПОТЕЗА 5: Проверка других эндпоинтов API")
    logger.info("="*60)
    
    client = ITADAPIClient(config.ITAD_API_KEY)
    
    # Проверяем /games/prices/v3 - может поддерживать батчинг
    logger.info("Проверка /games/prices/v3:")
    lookup_response = client.lookup_games_by_shop_id(['app/730', 'app/440'])
    if lookup_response:
        uuids = [uuid for uuid in lookup_response.values() if uuid]
        
        # Попробуем prices endpoint
        params = {
            'ids': ','.join(uuids),
            'country': 'US',
            'shops': 'steam'
        }
        result = client._request('/games/prices/v3', params=params)
        
        if result:
            logger.info(f"   ✅ /games/prices/v3 работает с батчингом!")
            logger.info(f"   Получено данных: {len(result) if isinstance(result, list) else 'dict'}")
            return True
        else:
            logger.warning("   ⚠️  /games/prices/v3 не вернул данные")
    
    return False

def main():
    """Запуск всех тестов"""
    logger.info("="*60)
    logger.info("ТЕСТИРОВАНИЕ ГИПОТЕЗ ОПТИМИЗАЦИИ ITAD API")
    logger.info("="*60)
    
    results = {}
    
    # Тест 1: storelow батчинг
    try:
        success, elapsed, count = test_hypothesis_1_storelow_batching()
        results['storelow_batching'] = {'success': success, 'elapsed': elapsed, 'count': count}
    except Exception as e:
        logger.error(f"Ошибка в тесте 1: {e}")
        results['storelow_batching'] = {'success': False, 'error': str(e)}
    
    # Тест 2: historylow батчинг
    try:
        success, elapsed, count = test_hypothesis_2_historylow_batching()
        results['historylow_batching'] = {'success': success, 'elapsed': elapsed, 'count': count}
    except Exception as e:
        logger.error(f"Ошибка в тесте 2: {e}")
        results['historylow_batching'] = {'success': False, 'error': str(e)}
    
    # Тест 3: параметр since
    try:
        success, count_with, count_without = test_hypothesis_3_history_with_since()
        results['since_parameter'] = {'success': success, 'with_since': count_with, 'without_since': count_without}
    except Exception as e:
        logger.error(f"Ошибка в тесте 3: {e}")
        results['since_parameter'] = {'success': False, 'error': str(e)}
    
    # Тест 4: параллелизм
    try:
        success, speedup = test_hypothesis_4_parallel_requests()
        results['parallel_requests'] = {'success': success, 'speedup': speedup}
    except Exception as e:
        logger.error(f"Ошибка в тесте 4: {e}")
        results['parallel_requests'] = {'success': False, 'error': str(e)}
    
    # Тест 5: другие эндпоинты
    try:
        success = test_hypothesis_5_check_other_endpoints()
        results['other_endpoints'] = {'success': success}
    except Exception as e:
        logger.error(f"Ошибка в тесте 5: {e}")
        results['other_endpoints'] = {'success': False, 'error': str(e)}
    
    # Итоговый отчет
    logger.info("\n" + "="*60)
    logger.info("ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    logger.info("="*60)
    
    for hypothesis, result in results.items():
        status = "✅ РАБОТАЕТ" if result.get('success') else "❌ НЕ РАБОТАЕТ"
        logger.info(f"{hypothesis}: {status}")
        if 'error' in result:
            logger.info(f"  Ошибка: {result['error']}")
    
    return results

if __name__ == "__main__":
    main()

