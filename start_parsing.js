// Script to start parsing via extension
// This will be injected into SteamDB page

async function loadAppIdsAndStartParsing() {
  // Load APP IDs from file (first 100 for testing)
  const appIds = [
    364770,364790,364800,364810,364820,364830,364850,1606000,1606030,1818320,
    1818340,1818370,1818450,796140,796260,1002,3149800,3149810,3149820,3149840,
    3149850,3149860,3149870,3149880,3149890,3149900,3149910,3149920,3149930,3149940,
    3149950,3149960,3149970,3149980,3149990,3150000,3150010,3150020,3150030,3150040,
    3150050,3150060,3150070,3150080,3150090,3150100,3150110,3150120,3150130,3150140,
    3150150,3150160,3150170,3150180,3150190,3150200,3150210,3150220,3150230,3150240,
    3150250,3150260,3150270,3150280,3150290,3150300,3150310,3150320,3150330,3150340,
    3150350,3150360,3150370,3150380,3150390,3150400,3150410,3150420,3150430,3150440,
    3150450,3150460,3150470,3150480,3150490,3150500,3150510,3150520,3150530,3150540,
    3150550,3150560,3150570,3150580,3150590,3150600,3150610,3150620,3150630,3150640
  ];
  
  console.log(`🚀 Starting parsing for ${appIds.length} APP IDs...`);
  
  // Send message to extension to start parsing
  if (typeof chrome !== 'undefined' && chrome.runtime) {
    chrome.runtime.sendMessage({
      action: 'startBatchParsing',
      appIds: appIds,
      batchSize: 10
    }, (response) => {
      console.log('Response from extension:', response);
    });
  } else {
    // Fallback: direct parsing if extension not available
    console.log('Extension not available, starting direct parsing...');
    startDirectParsing(appIds);
  }
}

function startDirectParsing(appIds) {
  // Direct parsing without extension
  const batchSize = 10;
  let currentIndex = 0;
  
  async function processNextBatch() {
    if (currentIndex >= appIds.length) {
      console.log('✅ All batches completed!');
      return;
    }
    
    const batch = appIds.slice(currentIndex, currentIndex + batchSize);
    currentIndex += batchSize;
    
    console.log(`📊 Processing batch ${Math.floor(currentIndex / batchSize)}/${Math.ceil(appIds.length / batchSize)}: ${batch.length} APP IDs`);
    
    // Create Compare URL
    const compareUrl = `https://steamdb.info/charts/?compare=${batch.join(',')}`;
    console.log(`Opening: ${compareUrl}`);
    
    // Open in new tab or navigate
    window.open(compareUrl, '_blank');
    
    // Wait and process next batch
    setTimeout(processNextBatch, 5000);
  }
  
  processNextBatch();
}

// Start parsing
loadAppIdsAndStartParsing();

