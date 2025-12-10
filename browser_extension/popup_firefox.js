// Popup script for Firefox (Manifest V2)

let appIdsInput = null;

// Add input field for APP IDs
document.addEventListener('DOMContentLoaded', () => {
  const statusDiv = document.getElementById('status');
  const parseBtn = document.getElementById('parseBtn');
  const exportBtn = document.getElementById('exportBtn');
  
  // Create input for APP IDs
  const inputContainer = document.createElement('div');
  inputContainer.style.marginBottom = '10px';
  inputContainer.innerHTML = `
    <label style="display: block; margin-bottom: 5px; font-size: 12px;">APP IDs (comma-separated or from file):</label>
    <textarea id="appIdsInput" rows="5" style="width: 100%; font-size: 11px; padding: 5px;" placeholder="570,730,578080 or paste from app_ids.txt"></textarea>
  `;
  statusDiv.parentNode.insertBefore(inputContainer, statusDiv);
  appIdsInput = document.getElementById('appIdsInput');
  
  // Load APP IDs from file button
  const loadFileBtn = document.createElement('button');
  loadFileBtn.textContent = 'Load from app_ids.txt';
  loadFileBtn.style.cssText = 'width: 100%; padding: 8px; margin: 5px 0; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 11px;';
  loadFileBtn.addEventListener('click', loadAppIdsFromFile);
  inputContainer.appendChild(loadFileBtn);
  
  parseBtn.addEventListener('click', () => {
    const appIdsText = appIdsInput.value.trim();
    if (!appIdsText) {
      updateStatus('⚠️ Please enter APP IDs');
      return;
    }
    
    const appIds = appIdsText.split(/[,\s\n]+/).filter(id => id.trim() && /^\d+$/.test(id.trim())).map(id => parseInt(id.trim()));
    if (appIds.length === 0) {
      updateStatus('⚠️ No valid APP IDs found');
      return;
    }
    
    updateStatus(`🚀 Starting parsing for ${appIds.length} APP IDs...`);
    browser.tabs.query({ active: true, currentWindow: true }).then((tabs) => {
      if (tabs[0] && tabs[0].url.includes('steamdb.info')) {
        browser.tabs.sendMessage(tabs[0].id, {
          action: 'startBatchParsing',
          appIds: appIds,
          batchSize: 10
        });
      } else {
        // Open SteamDB first
        browser.tabs.create({ url: 'https://steamdb.info' }).then((tab) => {
          setTimeout(() => {
            browser.tabs.sendMessage(tab.id, {
              action: 'startBatchParsing',
              appIds: appIds,
              batchSize: 10
            });
          }, 3000);
        });
      }
    });
  });
  
  exportBtn.addEventListener('click', () => {
    browser.storage.local.get(null).then((items) => {
      const data = {};
      for (const key in items) {
        if (key.startsWith('ccu_data_')) {
          const appId = key.replace('ccu_data_', '');
          data[appId] = items[key];
        }
      }
      
      if (Object.keys(data).length === 0) {
        updateStatus('⚠️ No data to export');
        return;
      }
      
      // Download as JSON
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `steamdb_data_${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      
      updateStatus(`✅ Exported ${Object.keys(data).length} APP IDs`);
    });
  });
  
  // Check current page status
  browser.tabs.query({ active: true, currentWindow: true }).then((tabs) => {
    if (tabs[0] && tabs[0].url.includes('steamdb.info')) {
      updateStatus('✅ Ready to parse SteamDB');
    } else {
      updateStatus('ℹ️ Navigate to steamdb.info or extension will open it');
    }
  });
});

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
        // Extract APP IDs (one per line or comma-separated)
        const appIds = content.split(/[,\s\n]+/).filter(id => id.trim() && /^\d+$/.test(id.trim()));
        appIdsInput.value = appIds.join(',');
        updateStatus(`✅ Loaded ${appIds.length} APP IDs from file`);
      };
      reader.readAsText(file);
    }
  };
  input.click();
}

function updateStatus(message) {
  document.getElementById('status').textContent = message;
}


