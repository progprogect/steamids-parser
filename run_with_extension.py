#!/usr/bin/env python3
"""
Script to run parsing via browser extension
Uses Playwright to control browser with extension installed
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

EXTENSION_PATH = Path(__file__).parent / "browser_extension"
APP_IDS_FILE = Path(__file__).parent / "app_ids.txt"

async def load_app_ids():
    """Load APP IDs from file"""
    with open(APP_IDS_FILE, 'r') as f:
        app_ids = [int(line.strip()) for line in f if line.strip() and line.strip().isdigit()]
    return app_ids

async def run_parsing():
    """Run parsing via browser extension"""
    app_ids = await load_app_ids()
    print(f"✅ Загружено {len(app_ids)} APP IDs")
    
    async with async_playwright() as p:
        # Launch browser with extension
        print("🚀 Запуск браузера с расширением...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir="/tmp/chrome-steam-parser",
            headless=False,
            args=[
                f"--disable-extensions-except={EXTENSION_PATH.absolute()}",
                f"--load-extension={EXTENSION_PATH.absolute()}",
            ]
        )
        
        # Open SteamDB
        print("📂 Открытие SteamDB...")
        page = await context.new_page()
        await page.goto("https://steamdb.info", wait_until="networkidle")
        
        # Wait for Cloudflare challenge if needed
        print("⏳ Ожидание загрузки страницы...")
        await asyncio.sleep(5)
        
        # Check if page loaded successfully
        title = await page.title()
        print(f"📄 Заголовок страницы: {title}")
        
        if "SteamDB" not in title:
            print("⚠️ Возможно требуется пройти Cloudflare challenge вручную")
            print("⏳ Ожидание 30 секунд для ручного прохождения...")
            await asyncio.sleep(30)
        
        # Load first batch of APP IDs (100 for testing)
        batch_size = 100
        test_batch = app_ids[:batch_size]
        
        print(f"🎯 Запуск парсинга для первых {len(test_batch)} APP IDs...")
        
        # Inject script to start parsing via extension
        script = f"""
        (async function() {{
            const appIds = {json.dumps(test_batch)};
            const batchSize = 10;
            
            console.log('🚀 Starting parsing for', appIds.length, 'APP IDs');
            
            // Try to send message to extension
            if (typeof chrome !== 'undefined' && chrome.runtime) {{
                // Get extension ID
                const extensions = await chrome.management.getAll();
                const steamExt = extensions.find(ext => 
                    ext.name && ext.name.toLowerCase().includes('steamdb')
                );
                
                if (steamExt) {{
                    chrome.runtime.sendMessage(steamExt.id, {{
                        action: 'startBatchParsing',
                        appIds: appIds,
                        batchSize: batchSize
                    }}, (response) => {{
                        console.log('Response:', response);
                    }});
                }} else {{
                    console.log('Extension not found, starting direct parsing...');
                    startDirectParsing(appIds, batchSize);
                }}
            }} else {{
                console.log('Chrome API not available, starting direct parsing...');
                startDirectParsing(appIds, batchSize);
            }}
            
            function startDirectParsing(appIds, batchSize) {{
                let currentIndex = 0;
                
                async function processNextBatch() {{
                    if (currentIndex >= appIds.length) {{
                        console.log('✅ All batches completed!');
                        return;
                    }}
                    
                    const batch = appIds.slice(currentIndex, currentIndex + batchSize);
                    currentIndex += batchSize;
                    
                    console.log(`Processing batch ${{Math.floor(currentIndex / batchSize)}}/${{Math.ceil(appIds.length / batchSize)}}: ${{batch.length}} APP IDs`);
                    
                    // Create Compare URL
                    const compareUrl = `https://steamdb.info/charts/?compare=${{batch.join(',')}}`;
                    console.log(`Opening: ${{compareUrl}}`);
                    
                    // Navigate to Compare page
                    window.location.href = compareUrl;
                    
                    // Wait for page to load and API calls
                    await new Promise(resolve => setTimeout(resolve, 10000));
                    
                    // Extract data from API responses
                    // This would be handled by the extension's content script
                    console.log('Batch processed, continuing...');
                    
                    // Process next batch
                    if (currentIndex < appIds.length) {{
                        setTimeout(processNextBatch, 2000);
                    }}
                }}
                
                processNextBatch();
            }}
        }})();
        """
        
        # Execute script
        await page.evaluate(script)
        
        print("✅ Парсинг запущен! Браузер будет работать в фоновом режиме.")
        print("📊 Отслеживайте прогресс в консоли браузера (F12)")
        print("⏸️  Нажмите Enter для остановки...")
        
        # Keep browser open
        try:
            await asyncio.sleep(3600)  # Keep for 1 hour or until interrupted
        except KeyboardInterrupt:
            print("\n⏹️  Остановка...")
        
        await context.close()

if __name__ == "__main__":
    asyncio.run(run_parsing())

