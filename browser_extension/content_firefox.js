// Content script for Firefox (Manifest V2)

let isParsing = false;
let parseQueue = [];
let currentBatch = [];

// Listen for API responses
browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'apiResponse') {
    // Extract app_id from URL
    const urlMatch = request.url.match(/appid=(\d+)/);
    if (urlMatch) {
      const appId = urlMatch[1];
      // Fetch the data using the browser's session
      fetch(request.url)
        .then(response => response.json())
        .then(data => {
          // Send data to background script for storage
          browser.runtime.sendMessage({
            action: 'saveData',
            key: `ccu_data_${appId}`,
            data: data
          });
        })
        .catch(error => console.error('Error fetching API data:', error));
    }
  }
  
  if (request.action === 'parseCurrentPage') {
    // Parse current page for CCU data
    const appIds = extractAppIdsFromPage();
    parseAppIds(appIds);
  }
  
  if (request.action === 'parseBatch') {
    // Parse a batch of APP IDs from Compare URL
    parseBatchFromCompare(request.appIds);
  }
  
  if (request.action === 'startBatchParsing') {
    // Start parsing multiple batches
    startBatchParsing(request.appIds, request.batchSize || 10);
  }
  
  if (request.action === 'getStatus') {
    sendResponse({
      isParsing: isParsing,
      queueLength: parseQueue.length,
      currentBatch: currentBatch.length
    });
  }
  
  if (request.action === 'continueBatchParsing') {
    if (parseQueue.length > 0) {
      currentBatch = parseQueue.shift();
      setTimeout(() => parseBatchFromCompare(currentBatch), 2000);
    } else {
      isParsing = false;
      console.log('✅ All batches completed!');
      browser.runtime.sendMessage({ action: 'allBatchesComplete' });
    }
  }
  
  return true; // Keep channel open for async responses
});

// Extract APP IDs from current page
function extractAppIdsFromPage() {
  const appIds = [];
  
  // Check if we're on a Compare page
  const urlParams = new URLSearchParams(window.location.search);
  const compareParam = urlParams.get('compare');
  if (compareParam) {
    appIds.push(...compareParam.split(',').map(id => parseInt(id.trim())));
  }
  
  // Or extract from current app page
  const appIdMatch = window.location.pathname.match(/\/app\/(\d+)/);
  if (appIdMatch) {
    appIds.push(parseInt(appIdMatch[1]));
  }
  
  return appIds;
}

// Parse APP IDs and fetch their CCU data
async function parseAppIds(appIds) {
  for (const appId of appIds) {
    try {
      const apiUrl = `https://steamdb.info/api/GetGraphMax/?appid=${appId}`;
      const response = await fetch(apiUrl);
      if (response.ok) {
        const data = await response.json();
        // Save to storage
        browser.runtime.sendMessage({
          action: 'saveData',
          key: `ccu_data_${appId}`,
          data: data
        });
        console.log(`✅ Fetched data for APP ID ${appId}:`, data.length, 'points');
      }
    } catch (error) {
      console.error(`❌ Error fetching data for APP ID ${appId}:`, error);
    }
  }
}

// Parse batch from Compare URL
async function parseBatchFromCompare(appIds) {
  if (!appIds || appIds.length === 0) return;
  
  const compareUrl = `https://steamdb.info/charts/?compare=${appIds.join(',')}`;
  console.log(`📊 Opening Compare page for ${appIds.length} APP IDs...`);
  
  // Navigate to compare page
  window.location.href = compareUrl;
  
  // Wait for page to load and API calls to complete
  setTimeout(async () => {
    // Fetch data for each APP ID in the batch
    for (const appId of appIds) {
      try {
        const apiUrl = `https://steamdb.info/api/GetGraphMax/?appid=${appId}`;
        const response = await fetch(apiUrl);
        if (response.ok) {
          const data = await response.json();
          browser.runtime.sendMessage({
            action: 'saveData',
            key: `ccu_data_${appId}`,
            data: data
          });
          console.log(`✅ Fetched data for APP ID ${appId}:`, data.length, 'points');
        }
      } catch (error) {
        console.error(`❌ Error fetching data for APP ID ${appId}:`, error);
      }
      // Small delay between requests
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    // Notify background that batch is done
    browser.runtime.sendMessage({
      action: 'batchComplete',
      appIds: appIds
    });
  }, 5000); // Wait 5 seconds for page to load
}

// Start batch parsing with queue
async function startBatchParsing(allAppIds, batchSize = 10) {
  if (isParsing) {
    console.log('⚠️ Parsing already in progress');
    return;
  }
  
  isParsing = true;
  parseQueue = [];
  
  // Split into batches
  for (let i = 0; i < allAppIds.length; i += batchSize) {
    parseQueue.push(allAppIds.slice(i, i + batchSize));
  }
  
  console.log(`🚀 Starting batch parsing: ${parseQueue.length} batches, ${allAppIds.length} total APP IDs`);
  
  // Process first batch
  if (parseQueue.length > 0) {
    currentBatch = parseQueue.shift();
    await parseBatchFromCompare(currentBatch);
  }
}

// Auto-parse when page loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
      const appIds = extractAppIdsFromPage();
      if (appIds.length > 0) {
        parseAppIds(appIds);
      }
    }, 3000); // Wait for page to fully load
  });
} else {
  setTimeout(() => {
    const appIds = extractAppIdsFromPage();
    if (appIds.length > 0) {
      parseAppIds(appIds);
    }
  }, 3000);
}


