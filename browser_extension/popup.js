// Popup script for SteamDB CSV Downloader extension

let appIdsInput = null;
let startBtn = null;
let loadFileBtn = null;
let exportMappingBtn = null;
let statusDiv = null;
let progressDiv = null;
let isDownloading = false;

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
  appIdsInput = document.getElementById('appIdsInput');
  startBtn = document.getElementById('startBtn');
  loadFileBtn = document.getElementById('loadFileBtn');
  exportMappingBtn = document.getElementById('exportMappingBtn');
  statusDiv = document.getElementById('status');
  progressDiv = document.getElementById('progress');
  
  // Load file button
  loadFileBtn.addEventListener('click', loadAppIdsFromFile);
  
  // Start download button
  startBtn.addEventListener('click', startDownload);
  
  // Export mapping button
  if (exportMappingBtn) {
    exportMappingBtn.addEventListener('click', exportMapping);
    // Check if mapping exists
    checkMappingExists();
  }
  
  // Check if download is in progress
  checkDownloadStatus();
  
  // Listen for progress updates from background
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'downloadProgress') {
      updateProgress(request.completed, request.total, request.currentBatch);
    } else if (request.action === 'downloadComplete') {
      isDownloading = false;
      updateStatus(`✅ Download complete! ${request.completed} batches processed. batch_mapping.json exported.`);
      updateProgress(request.completed, request.total, null);
      startBtn.disabled = false;
      startBtn.textContent = 'Start Download';
      // Show export button
      if (exportMappingBtn) {
        exportMappingBtn.style.display = 'block';
      }
    } else if (request.action === 'downloadError') {
      updateStatus(`❌ Error: ${request.error}`);
    }
  });
  });
  
// Parse APP IDs from text
function parseAppIds(text) {
  if (!text || !text.trim()) {
    return [];
  }
  
  // Split by commas, spaces, or newlines
  const ids = text
    .split(/[,\s\n]+/)
    .map(id => id.trim())
    .filter(id => id && /^\d+$/.test(id))
    .map(id => parseInt(id));
  
  // Remove duplicates
  return [...new Set(ids)];
}

// Create batches from APP IDs
function createBatches(appIds, batchSize = 10) {
  const batches = [];
  for (let i = 0; i < appIds.length; i += batchSize) {
    batches.push(appIds.slice(i, i + batchSize));
  }
  return batches;
}

// Load APP IDs from file
function loadAppIdsFromFile() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.txt,.csv';
  input.onchange = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target.result;
        const appIds = parseAppIds(content);
        if (appIds.length > 0) {
          appIdsInput.value = appIds.join(', ');
        updateStatus(`✅ Loaded ${appIds.length} APP IDs from file`);
        } else {
          updateStatus('⚠️ No valid APP IDs found in file');
        }
      };
      reader.readAsText(file);
    }
  };
  input.click();
}

// Start download process
function startDownload() {
  const appIdsText = appIdsInput.value.trim();
  
  if (!appIdsText) {
    updateStatus('⚠️ Please enter APP IDs');
    return;
  }
  
  const appIds = parseAppIds(appIdsText);
  
  if (appIds.length === 0) {
    updateStatus('⚠️ No valid APP IDs found');
    return;
  }
  
  // Create batches
  const batches = createBatches(appIds, 10);
  
  updateStatus(`🚀 Starting download for ${appIds.length} APP IDs (${batches.length} batches)...`);
  updateProgress(0, batches.length, null);
  
  isDownloading = true;
  startBtn.disabled = true;
  startBtn.textContent = 'Downloading...';
  
  // Send to background script
  chrome.runtime.sendMessage({
    action: 'startDownload',
    appIds: appIds,
    batches: batches
  }, (response) => {
    if (chrome.runtime.lastError) {
      updateStatus(`❌ Error: ${chrome.runtime.lastError.message}`);
      isDownloading = false;
      startBtn.disabled = false;
      startBtn.textContent = 'Start Download';
    } else if (response && response.success) {
      updateStatus(`✅ Download started. Processing ${batches.length} batches...`);
    } else {
      updateStatus(`❌ Failed to start download`);
      isDownloading = false;
      startBtn.disabled = false;
      startBtn.textContent = 'Start Download';
    }
  });
}

// Check download status on load
function checkDownloadStatus() {
  chrome.runtime.sendMessage({ action: 'getDownloadStatus' }, (response) => {
    if (response && response.isDownloading) {
      isDownloading = true;
      startBtn.disabled = true;
      startBtn.textContent = 'Downloading...';
      updateStatus(`📥 Download in progress...`);
      updateProgress(response.completed || 0, response.total || 0, response.currentBatch || null);
    }
  });
}

// Update status message
function updateStatus(message) {
  if (statusDiv) {
    statusDiv.textContent = message;
  }
}

// Update progress
function updateProgress(completed, total, currentBatch) {
  if (progressDiv) {
    if (total > 0) {
      const percent = Math.round((completed / total) * 100);
      let progressText = `Progress: ${completed}/${total} batches (${percent}%)`;
      if (currentBatch) {
        progressText += `\nCurrent batch: ${currentBatch.join(', ')}`;
      }
      progressDiv.textContent = progressText;
    } else {
      progressDiv.textContent = '';
    }
  }
}

// Check if mapping exists
function checkMappingExists() {
  chrome.storage.local.get(['batchMapping'], (result) => {
    if (result.batchMapping && Object.keys(result.batchMapping).length > 0) {
      if (exportMappingBtn) {
        exportMappingBtn.style.display = 'block';
      }
    }
  });
}

// Export batch mapping
function exportMapping() {
  chrome.runtime.sendMessage({ action: 'exportMapping' }, (response) => {
    if (chrome.runtime.lastError) {
      updateStatus(`❌ Error: ${chrome.runtime.lastError.message}`);
    } else if (response && response.success) {
      updateStatus('✅ batch_mapping.json exported successfully!');
    } else {
      updateStatus('⚠️ Failed to export mapping');
    }
  });
}
