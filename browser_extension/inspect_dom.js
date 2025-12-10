// Script to inject into page to inspect DOM and find data storage
(function() {
  console.log('=== DOM Inspection Script ===');
  
  // Wait for page to fully load
  setTimeout(() => {
    // 1. Check window object for data
    console.log('=== 1. Window Object ===');
    const windowKeys = Object.keys(window).filter(k => 
      k.toLowerCase().includes('chart') || 
      k.toLowerCase().includes('data') || 
      k.toLowerCase().includes('app') ||
      k.toLowerCase().includes('graph')
    );
    console.log('Relevant window keys:', windowKeys);
    windowKeys.forEach(key => {
      try {
        const value = window[key];
        console.log(`window.${key}:`, typeof value, Array.isArray(value) ? `[${value.length} items]` : '');
      } catch(e) {}
    });
    
    // 2. Check for chart libraries and their data
    console.log('\n=== 2. Chart Libraries ===');
    if (typeof Chart !== 'undefined') {
      console.log('Chart.js found');
      const charts = Chart.instances || [];
      charts.forEach((chart, i) => {
        console.log(`Chart ${i}:`, chart.data);
      });
    }
    if (typeof Highcharts !== 'undefined') {
      console.log('Highcharts found');
      const charts = Highcharts.charts || [];
      charts.forEach((chart, i) => {
        if (chart && chart.series) {
          console.log(`Highchart ${i}:`, chart.series.map(s => ({ name: s.name, data: s.data.length })));
        }
      });
    }
    if (typeof google !== 'undefined' && google.charts) {
      console.log('Google Charts found');
    }
    
    // 3. Check script tags for embedded data
    console.log('\n=== 3. Script Tags ===');
    const scripts = Array.from(document.querySelectorAll('script'));
    let dataScripts = 0;
    scripts.forEach((script, i) => {
      const content = script.textContent || script.innerHTML;
      if (content && (
        content.includes('GetGraphMax') || 
        content.includes('appid') ||
        content.includes('chart') ||
        content.includes('data') && content.length > 1000
      )) {
        dataScripts++;
        console.log(`Script ${i} contains potential data (${content.length} chars)`);
        // Try to extract JSON data
        const jsonMatch = content.match(/\[[\s\S]*?\]/);
        if (jsonMatch && jsonMatch[0].length > 50) {
          try {
            const parsed = JSON.parse(jsonMatch[0]);
            if (Array.isArray(parsed) && parsed.length > 0) {
              console.log(`  Found JSON array with ${parsed.length} items`);
            }
          } catch(e) {}
        }
      }
    });
    console.log(`Total scripts with potential data: ${dataScripts}`);
    
    // 4. Check DOM elements for data attributes
    console.log('\n=== 4. DOM Elements ===');
    const elementsWithData = Array.from(document.querySelectorAll('[data-*]'));
    const relevantElements = elementsWithData.filter(el => {
      const attrs = Array.from(el.attributes).map(a => a.name);
      return attrs.some(a => 
        a.includes('app') || 
        a.includes('chart') || 
        a.includes('data') ||
        a.includes('graph')
      );
    });
    console.log(`Elements with relevant data attributes: ${relevantElements.length}`);
    relevantElements.slice(0, 5).forEach((el, i) => {
      console.log(`Element ${i}:`, el.tagName, Array.from(el.attributes).map(a => `${a.name}="${a.value.substring(0, 50)}"`));
    });
    
    // 5. Check for canvas/SVG elements and try to extract data
    console.log('\n=== 5. Chart Elements ===');
    const canvases = Array.from(document.querySelectorAll('canvas'));
    const svgs = Array.from(document.querySelectorAll('svg'));
    console.log(`Canvas elements: ${canvases.length}`);
    console.log(`SVG elements: ${svgs.length}`);
    
    // 6. Check for chart containers
    console.log('\n=== 6. Chart Containers ===');
    const containers = Array.from(document.querySelectorAll('[id*="chart"], [class*="chart"], [id*="graph"], [class*="graph"]'));
    console.log(`Chart containers: ${containers.length}`);
    containers.slice(0, 10).forEach((el, i) => {
      console.log(`Container ${i}:`, {
        id: el.id,
        className: el.className,
        children: el.children.length,
        innerHTML: el.innerHTML.substring(0, 200)
      });
    });
    
    // 7. Try to find data in global scope by checking common patterns
    console.log('\n=== 7. Global Scope Search ===');
    const globalVars = [];
    for (let key in window) {
      try {
        if (key.startsWith('_') || key.includes('chart') || key.includes('data') || key.includes('app')) {
          const value = window[key];
          if (value && (Array.isArray(value) || typeof value === 'object')) {
            globalVars.push({ key, type: typeof value, isArray: Array.isArray(value) });
          }
        }
      } catch(e) {}
    }
    console.log('Potential global variables:', globalVars.slice(0, 10));
    
    // 8. Check network requests that were made
    console.log('\n=== 8. Performance API ===');
    if (window.performance && window.performance.getEntriesByType) {
      const networkEntries = window.performance.getEntriesByType('resource');
      const apiEntries = networkEntries.filter(e => 
        e.name.includes('GetGraphMax') || 
        e.name.includes('api')
      );
      console.log(`API requests found: ${apiEntries.length}`);
      apiEntries.forEach((entry, i) => {
        console.log(`Request ${i}:`, entry.name, `Status: ${entry.responseStatus || 'unknown'}`);
      });
    }
    
    console.log('\n=== Inspection Complete ===');
  }, 5000); // Wait 5 seconds for page to fully load
})();

