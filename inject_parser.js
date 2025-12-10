// Script to inject into SteamDB page to start parsing via extension
(async function() {
    console.log('🚀 Запуск парсинга через расширение...');
    
    // Load APP IDs (first 1000 for testing)
    const appIds = [364770,364790,364800,364810,364820,364830,364850,1606000,1606030,1818320,1818340,1818370,1818450,796140,796260,1002,3149800,3149810,3149820,3149840,3149850,1818640,1818690,1208370,1208380,1208390,1208400,1208410,1208420,2255910,2255950,2255970,2255980,1607200,1607240,1607250,2686950,2686960,2686980,2686990,2687000,2256450,2256520,2687250,2687280,2687300,1819370,1819430,1819440,1819450,585180,585190,2025080,366510,366530,366550,366570,366590,1819950,1819960,1819970,1819980,1209980,1209990,1210010,1210030,1210060,1608290,1608310,1608330,586080,586100,586110,586130,586140,586150,1409780,1409810,1409830,1409840,798240,798280,798290,798420,3810,3820,3830,3900,2688390,2688400,2688440,367580,367660,4470,4500,4520,4530,4560,4570,4580];
    
    const batchSize = 10;
    let currentIndex = 0;
    
    console.log(`📊 Всего APP IDs: ${appIds.length}, батчей: ${Math.ceil(appIds.length / batchSize)}`);
    
    // Try to send message to extension
    if (typeof chrome !== 'undefined' && chrome.runtime) {
        try {
            // Get extension ID
            const extensions = await chrome.management.getAll();
            const steamExt = extensions.find(ext => 
                ext.name && ext.name.toLowerCase().includes('steamdb')
            );
            
            if (steamExt) {
                console.log(`✅ Найдено расширение: ${steamExt.name} (${steamExt.id})`);
                
                // Send message to extension to start parsing
                chrome.runtime.sendMessage(steamExt.id, {
                    action: 'startBatchParsing',
                    appIds: appIds,
                    batchSize: batchSize
                }, (response) => {
                    if (chrome.runtime.lastError) {
                        console.error('❌ Ошибка отправки сообщения:', chrome.runtime.lastError);
                        startDirectParsing();
                    } else {
                        console.log('✅ Сообщение отправлено расширению:', response);
                    }
                });
            } else {
                console.log('⚠️ Расширение не найдено, запускаю прямой парсинг...');
                startDirectParsing();
            }
        } catch (error) {
            console.error('❌ Ошибка:', error);
            startDirectParsing();
        }
    } else {
        console.log('⚠️ Chrome API недоступен, запускаю прямой парсинг...');
        startDirectParsing();
    }
    
    function startDirectParsing() {
        console.log('🔄 Запуск прямого парсинга...');
        
        async function processNextBatch() {
            if (currentIndex >= appIds.length) {
                console.log('✅ Все батчи обработаны!');
                return;
            }
            
            const batch = appIds.slice(currentIndex, currentIndex + batchSize);
            currentIndex += batchSize;
            const batchNum = Math.floor(currentIndex / batchSize);
            const totalBatches = Math.ceil(appIds.length / batchSize);
            
            console.log(`📊 Батч ${batchNum}/${totalBatches}: ${batch.length} APP IDs`);
            
            // Create Compare URL
            const compareUrl = `https://steamdb.info/charts/?compare=${batch.join(',')}`;
            console.log(`🔗 Открываю: ${compareUrl}`);
            
            // Navigate to Compare page
            window.location.href = compareUrl;
            
            // Wait for page to load and API calls (extension will intercept)
            await new Promise(resolve => setTimeout(resolve, 15000));
            
            // Process next batch
            if (currentIndex < appIds.length) {
                setTimeout(processNextBatch, 2000);
            }
        }
        
        processNextBatch();
    }
})();

