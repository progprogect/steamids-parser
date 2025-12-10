// Content script for SteamDB CSV Downloader extension
// Note: Resource blocking is handled in background.js via webRequest API

let currentBatch = null;
let batchNumber = null;
let isProcessing = false;

// Signal that content script is ready
console.log('✅ SteamDB CSV Downloader content script loaded');

// Listen for messages from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('📥 Received message:', request.action);
  
  // Handle ping
  if (request.action === 'ping') {
    sendResponse({ success: true, ready: true });
    return true;
  }
  
  // Process batch
  if (request.action === 'processBatch') {
    currentBatch = request.batch;
    batchNumber = request.batchNumber;
    processBatch(request.batch, request.batchNumber);
    sendResponse({ success: true });
    return true;
  }
  
  return false;
});

// Process batch: switch to Max tab, wait for load, download CSV
async function processBatch(batch, batchNum) {
  if (isProcessing) {
    console.log('⚠️ Already processing a batch');
    return;
  }
  
  isProcessing = true;
  console.log(`📊 Processing batch ${batchNum}: ${batch.join(', ')}`);
  
  try {
    // Step 1: Wait for page to load
    await waitForPageLoad();
    
    // Step 2: Switch to Max tab
    const maxTabSwitched = await switchToMaxTab();
    if (!maxTabSwitched) {
      console.warn('⚠️ Could not switch to Max tab, continuing anyway...');
    }
    
    // Step 3: Wait for chart to load
    await waitForChartLoad();
    
    // Step 4: Download CSV
    const downloadSuccess = await downloadCSV();
    
    if (downloadSuccess) {
      console.log(`✅ CSV download started for batch ${batchNum}`);
      
      // Notify background
      chrome.runtime.sendMessage({
        action: 'csvDownloaded',
        batch: batch,
        batchNumber: batchNum
      }).catch(err => console.error('Error notifying background:', err));
      
      // Wait a bit for download to start, then notify completion
      setTimeout(() => {
        chrome.runtime.sendMessage({
          action: 'batchComplete',
          success: true
        }).catch(err => console.error('Error notifying batch complete:', err));
        
        isProcessing = false;
      }, 2000);
    } else {
      console.error(`❌ Failed to download CSV for batch ${batchNum}`);
      
      chrome.runtime.sendMessage({
        action: 'batchComplete',
        success: false
      }).catch(err => console.error('Error notifying batch failed:', err));
      
      isProcessing = false;
    }
  } catch (error) {
    console.error(`❌ Error processing batch ${batchNum}:`, error);
    
    chrome.runtime.sendMessage({
      action: 'batchComplete',
      success: false
    }).catch(err => console.error('Error notifying batch failed:', err));
    
    isProcessing = false;
  }
}

// Wait for page to load
function waitForPageLoad() {
  return new Promise((resolve) => {
    if (document.readyState === 'complete') {
      resolve();
    } else {
      window.addEventListener('load', resolve, { once: true });
      // Fallback timeout
      setTimeout(resolve, 5000);
    }
  });
}

// Switch to Max tab
async function switchToMaxTab() {
  // Check if URL already has max parameter
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('max') === '1') {
    console.log('✅ Already on Max tab (URL parameter)');
    return true;
  }
  
  // Try to find and click Max tab button
  return new Promise((resolve) => {
    console.log('🔍 Looking for Max tab button...');
    
    // Wait for page to be interactive
    setTimeout(() => {
      // Look for tab buttons - SteamDB might use different selectors
      // Try common patterns: buttons with text "Max", links with href containing "max", etc.
      const possibleSelectors = [
        'button:contains("Max")',
        'a:contains("Max")',
        '[data-tab="max"]',
        '[data-tab="Max"]',
        '.tab-max',
        '.tab-Max'
      ];
      
      // Try to find by text content
      const allButtons = document.querySelectorAll('button, a, [role="tab"]');
      let maxTab = null;
      
      for (const btn of allButtons) {
        const text = (btn.textContent || btn.innerText || '').trim().toLowerCase();
        if (text === 'max' || text.includes('max')) {
          maxTab = btn;
          break;
        }
      }
      
      if (maxTab) {
        console.log('✅ Found Max tab button, clicking...');
        maxTab.click();
        
        // Wait for tab to switch
        setTimeout(() => {
          resolve(true);
        }, 1000);
      } else {
        console.log('⚠️ Max tab button not found, trying URL parameter...');
        // Try adding URL parameter
        const currentUrl = new URL(window.location.href);
        currentUrl.searchParams.set('max', '1');
        window.location.href = currentUrl.toString();
        
        // Wait a bit
        setTimeout(() => {
          resolve(true); // Assume success
        }, 2000);
      }
    }, 2000);
  });
}

// Wait for chart to load
function waitForChartLoad() {
  return new Promise((resolve) => {
    console.log('⏳ Waiting for chart to load...');
    
    // Check if Highcharts is loaded
    const checkChart = () => {
      if (typeof Highcharts !== 'undefined' && Highcharts.charts) {
        const charts = Highcharts.charts.filter(c => c !== null && c !== undefined);
        if (charts.length > 0) {
          console.log(`✅ Chart loaded: ${charts.length} chart(s) found`);
          resolve();
          return;
        }
      }
      
      // Check for download button as indicator
      const downloadBtn = document.querySelector('g.highcharts-contextbutton, .highcharts-contextbutton');
      if (downloadBtn) {
        console.log('✅ Download button found, chart should be ready');
        resolve();
        return;
      }
      
      // Continue checking
      setTimeout(checkChart, 500);
    };
    
    // Start checking after initial delay
    setTimeout(checkChart, 1000);
    
    // Fallback timeout
    setTimeout(() => {
      console.log('⚠️ Chart load timeout, proceeding anyway...');
      resolve();
    }, 10000);
  });
}

// Download CSV
function downloadCSV() {
  return new Promise((resolve) => {
    console.log('📥 Starting CSV download...');
    
    // Request background script to execute download in page context
    chrome.runtime.sendMessage({
      action: 'executeInPage'
    }).catch(err => {
      console.error('Error requesting CSV download:', err);
      resolve(false);
    });
    
    // Listen for download confirmation
    let resolved = false;
    const listener = (event) => {
      if (event.data && event.data.type === 'CSV_DOWNLOAD_STARTED') {
        if (!resolved) {
          resolved = true;
          window.removeEventListener('message', listener);
          console.log('✅ CSV download started');
          resolve(true);
        }
      } else if (event.data && event.data.type === 'CSV_DOWNLOAD_ERROR') {
        if (!resolved) {
          resolved = true;
          window.removeEventListener('message', listener);
          console.error('❌ CSV download error:', event.data.error);
          resolve(false);
        }
      }
    };
    
    window.addEventListener('message', listener);
    
    // Timeout after 10 seconds
    setTimeout(() => {
      if (!resolved) {
        resolved = true;
        window.removeEventListener('message', listener);
        console.log('⚠️ CSV download timeout');
        resolve(false);
      }
    }, 10000);
  });
}

// Handle page load - check if we need to process a batch
(async function() {
  const urlParams = new URLSearchParams(window.location.search);
  const compareParam = urlParams.get('compare');
  
  if (compareParam) {
    console.log(`📊 On Compare page: ${compareParam}`);
    // Wait a bit for background script to send processBatch message
    // If it doesn't come, we might be resuming from saved state
  }
})();
