#!/usr/bin/env python3
"""Тест нового парсера без агрегации"""
import asyncio
from steamcharts_parser import SteamChartsParser

async def test():
    parser = SteamChartsParser()
    try:
        data = await parser.fetch_ccu_data(730)
        print(f"✅ Тест успешен!")
        print(f"   Всего точек avg: {len(data['avg'])}")
        print(f"   Всего точек peak: {len(data['peak'])}")
        print(f"\n   Первые 3 точки:")
        for i, point in enumerate(data['avg'][:3]):
            print(f"     {i+1}. {point['datetime']} - {point['players']} игроков")
        print(f"\n   Последние 3 точки:")
        for i, point in enumerate(data['avg'][-3:]):
            print(f"     {i+1}. {point['datetime']} - {point['players']} игроков")
    finally:
        await parser.close()

if __name__ == "__main__":
    asyncio.run(test())



