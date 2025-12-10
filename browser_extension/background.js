// Background service worker for SteamDB CSV Downloader extension

// Block resources for faster loading (images, CSS, fonts)
chrome.webRequest.onBeforeRequest.addListener(
  (details) => {
    // Block images, CSS, fonts, but allow JavaScript and HTML
    const url = details.url.toLowerCase();
    if (url.match(/\.(jpg|jpeg|png|gif|svg|webp|ico|css|woff|woff2|ttf|eot)(\?|$)/i)) {
      return { cancel: true };
    }
    return {};
  },
  { urls: ["<all_urls>"] },
  ["blocking"]
);

// Tab Manager - manages parallel tabs for batch processing
class TabManager {
  constructor(maxParallelTabs = 2) {
    this.maxParallelTabs = maxParallelTabs;
    this.activeTabs = []; // Array of { tabId, batch, batchNumber }
    this.queue = []; // Queue of batches to process
    this.completedBatches = 0;
    this.totalBatches = 0;
    this.currentBatchNumbers = new Map(); // Map tabId -> batchNumber
    this.batchCounter = 0;
    this.isDownloading = false;
    this.errorCount = 0;
    this.maxErrors = 3; // Reduce parallelism after 3 errors
  }
  
  // Start download process
  async startDownload(batches) {
    if (this.isDownloading) {
      console.log('⚠️ Download already in progress');
      return { success: false, error: 'Download already in progress' };
    }
    
    this.isDownloading = true;
    this.queue = batches.map((batch, index) => ({
      batch: batch,
      batchNumber: index + 1
    }));
    this.totalBatches = batches.length;
    this.completedBatches = 0;
    this.batchCounter = 0;
    this.errorCount = 0;
    
    // Save state
    await this.saveState();
    
    // Start processing batches
    this.processNextBatches();
    
    return { success: true };
  }
  
  // Process next batches (up to maxParallelTabs)
  async processNextBatches() {
    // Check if we should reduce parallelism due to errors
    const currentMaxTabs = this.errorCount >= this.maxErrors ? 1 : this.maxParallelTabs;
    
    // Smart delay between batches (increase on errors)
    const delayBetweenBatches = Math.min(2000, 1000 + (this.errorCount * 300));
    
    // Fill up to maxParallelTabs
    while (this.activeTabs.length < currentMaxTabs && this.queue.length > 0) {
      const batchItem = this.queue.shift();
      await this.createTabForBatch(batchItem.batch, batchItem.batchNumber);
      
      // Smart delay between creating tabs (reduce delay if no errors)
      if (this.queue.length > 0) {
        await new Promise(resolve => setTimeout(resolve, delayBetweenBatches));
      }
    }
    
    // If queue is empty and no active tabs, we're done
    if (this.queue.length === 0 && this.activeTabs.length === 0) {
      await this.completeDownload();
    }
  }
  
  // Create tab for a batch
  async createTabForBatch(batch, batchNumber) {
    try {
      // Create Compare URL with Max tab parameter
      const compareUrl = `https://steamdb.info/charts/?compare=${batch.join(',')}&max=1`;
      
      console.log(`📊 Creating tab for batch ${batchNumber}: ${batch.join(', ')}`);
      
      const tab = await chrome.tabs.create({
        url: compareUrl,
        active: false // Open in background
      });
      
      this.activeTabs.push({
        tabId: tab.id,
        batch: batch,
        batchNumber: batchNumber
      });
      
      this.currentBatchNumbers.set(tab.id, batchNumber);
      
      // Wait for tab to load, then inject content script
      let messageSent = false; // Prevent double sending
      
      const onTabUpdated = (tabId, changeInfo) => {
        if (tabId === tab.id && changeInfo.status === 'complete' && !messageSent) {
          chrome.tabs.onUpdated.removeListener(onTabUpdated);
          messageSent = true;
          
          // Wait a bit for page to fully load (smart delay: 1-2 seconds)
          const delay = Math.min(2000, 1000 + (this.errorCount * 500)); // Increase delay on errors
          setTimeout(() => {
            chrome.tabs.sendMessage(tabId, {
              action: 'processBatch',
              batch: batch,
              batchNumber: batchNumber
            }).catch(err => {
              console.error(`Error sending message to tab ${tabId}:`, err);
              this.handleBatchComplete(tabId, false);
            });
          }, delay);
        }
      };
      
      chrome.tabs.onUpdated.addListener(onTabUpdated);
      
      // Fallback timeout
      setTimeout(() => {
        chrome.tabs.onUpdated.removeListener(onTabUpdated);
        if (!messageSent) {
          messageSent = true;
          // Try to send message anyway
          chrome.tabs.sendMessage(tab.id, {
            action: 'processBatch',
            batch: batch,
            batchNumber: batchNumber
          }).catch(err => {
            console.error(`Error sending message to tab ${tab.id} (timeout):`, err);
            this.handleBatchComplete(tab.id, false);
          });
        }
      }, 10000);
      
    } catch (error) {
      console.error(`Error creating tab for batch ${batchNumber}:`, error);
      this.errorCount++;
      this.completedBatches++;
      await this.notifyProgress();
      await this.saveState();
      this.processNextBatches();
    }
  }
  
  // Close tab after batch completion
  async closeTab(tabId) {
    try {
      const tabIndex = this.activeTabs.findIndex(t => t.tabId === tabId);
      if (tabIndex !== -1) {
        this.activeTabs.splice(tabIndex, 1);
      }
      this.currentBatchNumbers.delete(tabId);
      
      await chrome.tabs.remove(tabId);
      
      // Process next batches
      this.processNextBatches();
      
    } catch (error) {
      console.error(`Error closing tab ${tabId}:`, error);
    }
  }
  
  // Handle batch completion
  async handleBatchComplete(tabId, success) {
    if (success) {
      this.completedBatches++;
      this.errorCount = Math.max(0, this.errorCount - 1); // Reset error count on success
    } else {
      this.errorCount++;
    }
    
    await this.notifyProgress();
    await this.closeTab(tabId);
  }
  
  // Notify popup about progress
  async notifyProgress() {
    const activeBatch = this.activeTabs.length > 0 ? this.activeTabs[0].batch : null;
    
    chrome.runtime.sendMessage({
      action: 'downloadProgress',
      completed: this.completedBatches,
      total: this.totalBatches,
      currentBatch: activeBatch
    }).catch(() => {}); // Ignore errors if popup is closed
  }
  
  // Complete download
  async completeDownload() {
    this.isDownloading = false;
    this.completedBatches = this.totalBatches;
    
    await this.saveState();
    
    chrome.runtime.sendMessage({
      action: 'downloadComplete',
      completed: this.completedBatches,
      total: this.totalBatches
    }).catch(() => {});
    
    console.log(`✅ All batches completed! ${this.completedBatches}/${this.totalBatches}`);
    
    // Export batch mapping JSON file
    try {
      await batchMappingManager.exportMapping();
    } catch (error) {
      console.error('Error exporting batch mapping:', error);
    }
  }
  
  // Save state to storage
  async saveState() {
    const state = {
      isDownloading: this.isDownloading,
      queue: this.queue,
      activeTabs: this.activeTabs.map(t => ({
        tabId: t.tabId,
        batch: t.batch,
        batchNumber: t.batchNumber
      })),
      completedBatches: this.completedBatches,
      totalBatches: this.totalBatches,
      errorCount: this.errorCount
    };
    
    await chrome.storage.local.set({ downloadState: state });
  }
  
  // Load state from storage
  async loadState() {
    const result = await chrome.storage.local.get(['downloadState']);
    if (result.downloadState) {
      const state = result.downloadState;
      this.isDownloading = state.isDownloading || false;
      this.queue = state.queue || [];
      this.completedBatches = state.completedBatches || 0;
      this.totalBatches = state.totalBatches || 0;
      this.errorCount = state.errorCount || 0;
      
      // Restore batch numbers map and verify tabs still exist
      this.currentBatchNumbers.clear();
      if (state.activeTabs && state.activeTabs.length > 0) {
        const existingTabs = await chrome.tabs.query({});
        const existingTabIds = new Set(existingTabs.map(t => t.id));
        
        // Only restore tabs that still exist
        this.activeTabs = state.activeTabs.filter(t => existingTabIds.has(t.tabId));
        
        this.activeTabs.forEach(t => {
          this.currentBatchNumbers.set(t.tabId, t.batchNumber);
        });
        
        // If some tabs were closed, mark them as failed
        const closedTabs = state.activeTabs.filter(t => !existingTabIds.has(t.tabId));
        if (closedTabs.length > 0) {
          console.log(`⚠️ Found ${closedTabs.length} closed tabs, marking as failed`);
          this.completedBatches += closedTabs.length;
          this.errorCount += closedTabs.length;
        }
      } else {
        this.activeTabs = [];
      }
      
      return true;
    }
    return false;
  }
  
  // Get download status
  getStatus() {
    return {
      isDownloading: this.isDownloading,
      completed: this.completedBatches,
      total: this.totalBatches,
      currentBatch: this.activeTabs.length > 0 ? this.activeTabs[0].batch : null
    };
  }
}

// Download Manager - manages CSV file downloads and renaming
class DownloadManager {
  constructor(tabManager) {
    this.tabManager = tabManager;
    this.pendingDownloads = new Map(); // Map downloadId -> batchNumber
    this.tabToBatch = new Map(); // Map tabId -> batchNumber (for tracking)
    this.downloadCounter = 0;
    this.setupListeners();
  }
  
  // Register tab -> batch mapping when CSV download is initiated
  registerTabBatch(tabId, batchNumber) {
    this.tabToBatch.set(tabId, batchNumber);
    console.log(`📋 Registered tab ${tabId} -> batch ${batchNumber}`);
  }
  
  // Setup download listeners
  setupListeners() {
    // Listen for download creation
    chrome.downloads.onCreated.addListener((downloadItem) => {
      this.handleDownloadCreated(downloadItem);
    });
    
    // Listen for download filename determination
    chrome.downloads.onDeterminingFilename.addListener((downloadItem, suggest) => {
      this.handleDownloadFilename(downloadItem, suggest);
    });
  }
  
  // Handle download creation
  handleDownloadCreated(downloadItem) {
    // Check if it's a CSV file from SteamDB
    if (downloadItem.filename && downloadItem.filename.endsWith('.csv') &&
        downloadItem.url && downloadItem.url.includes('steamdb.info')) {
      console.log(`📥 CSV download started: ${downloadItem.filename}`);
      
      // Try to find batch number from active tabs
      this.findBatchNumberForDownload(downloadItem).then(batchNumber => {
        if (batchNumber) {
          this.pendingDownloads.set(downloadItem.id, batchNumber);
          console.log(`📋 Tracking download ${downloadItem.id} for batch ${batchNumber}`);
        } else {
          // Use counter as fallback
          this.downloadCounter++;
          const fallbackBatchNumber = this.downloadCounter;
          this.pendingDownloads.set(downloadItem.id, fallbackBatchNumber);
          console.log(`📋 Using fallback batch number ${fallbackBatchNumber} for download ${downloadItem.id}`);
                    }
                  });
                }
  }
  
  // Handle download filename - rename to batch_XXX.csv
  async handleDownloadFilename(downloadItem, suggest) {
    // Check if it's a CSV file from SteamDB
    if (downloadItem.filename && downloadItem.filename.endsWith('.csv') &&
        downloadItem.url && downloadItem.url.includes('steamdb.info')) {
      
      const batchNumber = this.pendingDownloads.get(downloadItem.id);
      
      if (batchNumber) {
        const newFilename = `batch_${String(batchNumber).padStart(3, '0')}.csv`;
        console.log(`📝 Renaming download ${downloadItem.id} to: ${newFilename}`);
        suggest({ filename: newFilename });
        
        // Get batch APP IDs from tab manager and save mapping
        const activeTab = Array.from(this.tabManager.activeTabs).find(t => 
          this.tabManager.currentBatchNumbers.get(t.tabId) === batchNumber
        );
        if (activeTab && activeTab.batch) {
          batchMappingManager.registerBatch(batchNumber, activeTab.batch);
        }
        
        this.pendingDownloads.delete(downloadItem.id);
      } else {
        // Fallback: use counter
        this.downloadCounter++;
        const fallbackBatchNumber = this.downloadCounter;
        const newFilename = `batch_${String(fallbackBatchNumber).padStart(3, '0')}.csv`;
        console.log(`📝 Renaming download ${downloadItem.id} to: ${newFilename} (fallback)`);
        suggest({ filename: newFilename });
      }
    }
  }
  
  // Find batch number for download (by matching tab)
  async findBatchNumberForDownload(downloadItem) {
    // First check if we already have it in pending downloads
    const pendingBatchNumber = this.pendingDownloads.get(downloadItem.id);
    if (pendingBatchNumber) {
      return pendingBatchNumber;
    }
    
    // Try to find by referrer URL (most reliable)
    if (downloadItem.referrer) {
      try {
        const referrerUrl = new URL(downloadItem.referrer);
        if (referrerUrl.hostname === 'steamdb.info' && referrerUrl.pathname === '/charts/') {
          // Get all SteamDB tabs
          const tabs = await chrome.tabs.query({ url: 'https://steamdb.info/charts/*' });
          
          // Find tab matching referrer URL
          for (const tab of tabs) {
            if (tab.url === downloadItem.referrer) {
              const batchNumber = this.tabToBatch.get(tab.id) || 
                                 this.tabManager.currentBatchNumbers.get(tab.id);
              if (batchNumber) {
                this.pendingDownloads.set(downloadItem.id, batchNumber);
                return batchNumber;
              }
            }
          }
        }
      } catch (e) {
        // Ignore URL parsing errors
      }
    }
    
    // Fallback: Get all SteamDB tabs and find the most recent one
    const tabs = await chrome.tabs.query({ url: 'https://steamdb.info/charts/*' });
    
    // Sort by last accessed time (most recent first)
    tabs.sort((a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0));
    
    // Find the tab that matches this download
    for (const tab of tabs) {
      if (tab.url && tab.url.includes('compare=')) {
        const batchNumber = this.tabToBatch.get(tab.id) || 
                           this.tabManager.currentBatchNumbers.get(tab.id);
        if (batchNumber) {
          this.pendingDownloads.set(downloadItem.id, batchNumber);
          return batchNumber;
        }
      }
    }
    
    return null;
  }
}

// Batch Mapping Manager - saves mapping of batch numbers to APP IDs
class BatchMappingManager {
  constructor() {
    this.mapping = {}; // Map batchNumber -> [appIds]
  }
  
  // Register batch mapping
  registerBatch(batchNumber, appIds) {
    const batchKey = `batch_${String(batchNumber).padStart(3, '0')}`;
    this.mapping[batchKey] = appIds;
    console.log(`📋 Registered mapping for ${batchKey}: ${appIds.length} APP IDs`);
    this.saveMapping();
  }
  
  // Save mapping to storage
  async saveMapping() {
    await chrome.storage.local.set({ batchMapping: this.mapping });
  }
  
  // Load mapping from storage
  async loadMapping() {
    const result = await chrome.storage.local.get(['batchMapping']);
    if (result.batchMapping) {
      this.mapping = result.batchMapping;
      console.log(`📋 Loaded batch mapping: ${Object.keys(this.mapping).length} batches`);
    }
  }
  
  // Export mapping to JSON file
  async exportMapping() {
    const jsonContent = JSON.stringify(this.mapping, null, 2);
    
    // Create data URL (service worker can't use Blob)
    const dataUrl = 'data:application/json;charset=utf-8,' + encodeURIComponent(jsonContent);
    
    // Download JSON file
    try {
      const downloadId = await chrome.downloads.download({
        url: dataUrl,
        filename: 'batch_mapping.json',
        saveAs: false
      });
      
      console.log(`📁 Exported batch mapping to batch_mapping.json (${Object.keys(this.mapping).length} batches)`);
      return downloadId;
    } catch (error) {
      console.error('Error exporting batch mapping:', error);
      throw error;
    }
  }
  
  // Get mapping
  getMapping() {
    return this.mapping;
  }
}

// Initialize managers
const tabManager = new TabManager(2); // 2 parallel tabs
const downloadManager = new DownloadManager(tabManager);
const batchMappingManager = new BatchMappingManager();

// Load state on startup
chrome.runtime.onStartup.addListener(() => {
  tabManager.loadState();
});

chrome.runtime.onInstalled.addListener(() => {
  tabManager.loadState();
});

// Load state and mapping immediately
Promise.all([
  tabManager.loadState(),
  batchMappingManager.loadMapping()
]).then(([loaded]) => {
  if (loaded && tabManager.isDownloading) {
    console.log('📥 Resuming download from saved state...');
    tabManager.processNextBatches();
  }
});

// Message handlers
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // Start download
  if (request.action === 'startDownload') {
    tabManager.startDownload(request.batches)
      .then(result => sendResponse(result))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true; // Keep channel open
  }
  
  // Get download status
  if (request.action === 'getDownloadStatus') {
    sendResponse(tabManager.getStatus());
    return true;
  }
  
  // Export batch mapping
  if (request.action === 'exportMapping') {
    batchMappingManager.exportMapping()
      .then(() => sendResponse({ success: true }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }
  
  // Batch completed
  if (request.action === 'batchComplete') {
    const tabId = sender.tab ? sender.tab.id : null;
    if (tabId) {
      tabManager.handleBatchComplete(tabId, request.success !== false);
    }
    sendResponse({ success: true });
    return true;
  }
  
  // CSV downloaded - register batch number for download tracking and save mapping
  if (request.action === 'csvDownloaded') {
    const tabId = sender.tab ? sender.tab.id : null;
    if (tabId) {
      const batchNumber = tabManager.currentBatchNumbers.get(tabId);
      if (batchNumber) {
        console.log(`✅ CSV download initiated for batch ${batchNumber}, tab ${tabId}`);
        // Register tabId -> batchNumber mapping for download manager
        downloadManager.registerTabBatch(tabId, batchNumber);
        
        // Register batch mapping (batchNumber -> APP IDs)
        if (request.batch && Array.isArray(request.batch)) {
          batchMappingManager.registerBatch(batchNumber, request.batch);
        }
      }
    }
    sendResponse({ success: true });
    return true;
  }
  
  // Execute in page context (for CSV download)
  if (request.action === 'executeInPage') {
    if (sender.tab && sender.tab.id) {
      chrome.scripting.executeScript({
        target: { tabId: sender.tab.id },
        world: 'MAIN',
        func: function() {
          console.log('[Injected] Looking for Highcharts Download button...');
          
          // Find Highcharts context button - exact selector from SteamDB
          // <g class="highcharts-contextbutton" ...><title>Chart context menu</title>
          let downloadBtn = null;
          
          // Method 1: Find by exact class (most reliable)
          const contextButtons = document.querySelectorAll('g.highcharts-contextbutton');
          if (contextButtons.length > 0) {
            downloadBtn = contextButtons[0];
            console.log('[Injected] Found Highcharts context button by class');
          }
          
          // Method 2: Find by title "Chart context menu" (fallback)
          if (!downloadBtn) {
            const allGroups = document.querySelectorAll('svg g');
            for (const group of allGroups) {
              const title = group.querySelector('title');
              if (title && title.textContent.trim() === 'Chart context menu') {
                downloadBtn = group;
                console.log('[Injected] Found button by title');
                  break;
              }
            }
          }
          
          if (downloadBtn) {
            console.log('[Injected] Clicking Download button...');
            
            // SVG <g> element doesn't have click() method, use MouseEvent
            const clickEvent = new MouseEvent('click', {
              view: window,
              bubbles: true,
              cancelable: true,
              buttons: 1
            });
            downloadBtn.dispatchEvent(clickEvent);
            
            // Also try clicking on the rect or image inside if available
            const rect = downloadBtn.querySelector('rect');
            if (rect) {
              rect.dispatchEvent(clickEvent);
            }
            
            // Menu appears almost immediately, so use fast polling with MutationObserver
            let menuFound = false;
            let attempts = 0;
            const maxAttempts = 10; // 1 second total (100ms * 10)
            
            const checkForMenu = () => {
              attempts++;
              
              // Look for menu item with exact class and text
              const menuItems = Array.from(document.querySelectorAll('li.highcharts-menu-item'));
              
              if (menuItems.length > 0) {
                // Find "Download CSV" option
              for (const item of menuItems) {
                const text = (item.textContent || item.innerText || '').trim();
                  if (text === 'Download CSV') {
                    console.log('[Injected] Found "Download CSV" option, clicking...');
                    
                    // Use MouseEvent for reliable click
                    const clickEvent = new MouseEvent('click', {
                      view: window,
                      bubbles: true,
                      cancelable: true,
                      buttons: 1
                    });
                    item.dispatchEvent(clickEvent);
                    
                    // Also try direct click if available
                    if (typeof item.click === 'function') {
                  item.click();
                    }
                    
                    menuFound = true;
                  window.postMessage({ type: 'CSV_DOWNLOAD_STARTED' }, '*');
                  return;
                  }
                }
              }
              
              if (!menuFound && attempts < maxAttempts) {
                setTimeout(checkForMenu, 100); // Fast polling: 100ms
              } else if (!menuFound) {
                console.log('[Injected] CSV option not found in menu after timeout');
                window.postMessage({ type: 'CSV_DOWNLOAD_ERROR', error: 'CSV option not found' }, '*');
              }
            };
            
            // Start checking immediately (menu appears almost instantly)
            setTimeout(checkForMenu, 200); // Initial 200ms delay
            
            // Also use MutationObserver for instant detection
            const observer = new MutationObserver(() => {
              if (!menuFound) {
                checkForMenu();
              }
            });
            
            observer.observe(document.body, {
              childList: true,
              subtree: true
            });
            
            // Stop observer after timeout
            setTimeout(() => {
              observer.disconnect();
            }, 1500);
            
          } else {
            console.log('[Injected] Download button not found');
            window.postMessage({ type: 'CSV_DOWNLOAD_ERROR', error: 'Download button not found' }, '*');
          }
        }
      }).catch(err => {
        console.error('Error executing script in page:', err);
      });
    }
    sendResponse({ success: true });
    return true;
  }
  
  return false;
});

// Handle tab removal (cleanup)
chrome.tabs.onRemoved.addListener((tabId) => {
  // Check if this was an active download tab
  const tabIndex = tabManager.activeTabs.findIndex(t => t.tabId === tabId);
  if (tabIndex !== -1) {
    console.log(`⚠️ Tab ${tabId} was closed, marking batch as failed`);
    tabManager.handleBatchComplete(tabId, false);
  }
});
