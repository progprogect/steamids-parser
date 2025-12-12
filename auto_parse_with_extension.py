#!/usr/bin/env python3
"""
Автоматический запуск парсинга через расширение браузера
Открывает батчи последовательно, расширение автоматически собирает данные
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

EXTENSION_PATH = Path(__file__).parent / "browser_extension"
APP_IDS_FILE = Path(__file__).parent / "app_ids.txt"
BATCH_SIZE = 10  # Размер батча для Compare

def load_app_ids():
    """Load APP IDs from file"""
    with open(APP_IDS_FILE, 'r') as f:
        app_ids = [int(line.strip()) for line in f if line.strip() and line.strip().isdigit()]
    return app_ids

async def run_auto_parsing():
    """Автоматически открывает батчи для парсинга"""
    app_ids = load_app_ids()
    total_batches = (len(app_ids) + BATCH_SIZE - 1) // BATCH_SIZE
    
    print(f"✅ Загружено {len(app_ids)} APP IDs")
    print(f"📊 Будет обработано {total_batches} батчей по {BATCH_SIZE} APP IDs")
    print(f"🚀 Запуск браузера с расширением...")
    
    async with async_playwright() as p:
        # Launch browser with extension
        context = await p.chromium.launch_persistent_context(
            user_data_dir="/tmp/chrome-steam-parser-ext",
            headless=False,
            args=[
                f"--disable-extensions-except={EXTENSION_PATH.absolute()}",
                f"--load-extension={EXTENSION_PATH.absolute()}",
            ]
        )
        
        page = await context.new_page()
        
        # Open SteamDB first to pass Cloudflare
        print("📂 Открытие SteamDB...")
        await page.goto("https://steamdb.info", wait_until="networkidle")
        await asyncio.sleep(5)  # Wait for Cloudflare if needed
        
        print("✅ SteamDB загружен. Начинаю обработку батчей...")
        print("💡 Расширение будет автоматически собирать данные при загрузке каждой страницы Compare")
        print("⏸️  Нажмите Ctrl+C для остановки\n")
        
        processed = 0
        try:
            for i in range(0, len(app_ids), BATCH_SIZE):
                batch = app_ids[i:i + BATCH_SIZE]
                batch_num = i // BATCH_SIZE + 1
                
                # Create Compare URL
                compare_url = f"https://steamdb.info/charts/?compare={','.join(map(str, batch))}"
                
                print(f"[{batch_num}/{total_batches}] Обработка батча: {len(batch)} APP IDs")
                print(f"   URL: {compare_url}")
                
                # Navigate to Compare page
                await page.goto(compare_url, wait_until="networkidle", timeout=60000)
                
                # Wait for API calls to complete (extension will intercept them)
                await asyncio.sleep(10)  # Wait for all API calls
                
                processed += len(batch)
                progress = (processed / len(app_ids)) * 100
                
                print(f"   ✅ Обработано: {processed}/{len(app_ids)} ({progress:.1f}%)")
                print()
                
                # Small delay between batches
                await asyncio.sleep(2)
                
        except KeyboardInterrupt:
            print(f"\n⏹️  Остановлено пользователем")
            print(f"📊 Обработано: {processed}/{len(app_ids)} APP IDs")
        
        print("\n💾 Данные сохранены расширением в chrome.storage.local")
        print("📥 Используйте кнопку 'Export Data' в popup расширения для экспорта")
        print("⏸️  Браузер останется открытым. Закройте его вручную когда закончите.")
        
        # Keep browser open
        input("\nНажмите Enter для закрытия браузера...")
        await context.close()

if __name__ == "__main__":
    asyncio.run(run_auto_parsing())



