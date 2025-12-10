// Background script for Firefox (Manifest V2)

// Listen for messages from content script
browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getApiData') {
    // Fetch API data using the browser's session (which has passed Cloudflare)
    fetch(request.url)
      .then(response => response.json())
      .then(data => {
        sendResponse({ success: true, data: data });
      })
      .catch(error => {
        sendResponse({ success: false, error: error.message });
      });
    return true; // Keep channel open for async response
  }
  
  if (request.action === 'saveData') {
    // Save parsed data to storage
    browser.storage.local.set({ [request.key]: request.data }).then(() => {
      sendResponse({ success: true });
    });
    return true;
  }
  
  if (request.action === 'getData') {
    // Get saved data from storage
    browser.storage.local.get([request.key]).then((result) => {
      sendResponse({ success: true, data: result[request.key] });
    });
    return true;
  }
  
  if (request.action === 'batchComplete') {
    // Continue with next batch
    browser.tabs.query({ active: true, currentWindow: true }).then((tabs) => {
      if (tabs[0]) {
        browser.tabs.sendMessage(tabs[0].id, { action: 'continueBatchParsing' });
      }
    });
  }
  
  if (request.action === 'allBatchesComplete') {
    // Notify user
    browser.notifications.create({
      type: 'basic',
      iconUrl: 'icon.png',
      title: 'SteamDB Parser',
      message: 'All batches completed! Check the extension popup to export data.'
    });
  }
  
  return true;
});

// Intercept API requests to capture data
browser.webRequest.onCompleted.addListener(
  (details) => {
    if (details.url.includes('GetGraphMax') && details.statusCode === 200) {
      // Notify content script about successful API call
      browser.tabs.sendMessage(details.tabId, {
        action: 'apiResponse',
        url: details.url
      }).catch(() => {}); // Ignore errors if tab doesn't have content script
    }
  },
  { urls: ["https://steamdb.info/api/*"] }
);


