// Script to check what data is available on the Compare page
console.log('=== Проверка данных на странице ===');

// Check for chart data in global variables
console.log('1. Глобальные переменные:');
console.log('window.chartData:', typeof window.chartData !== 'undefined' ? window.chartData : 'не найдено');
console.log('window.appData:', typeof window.appData !== 'undefined' ? window.appData : 'не найдено');
console.log('window.data:', typeof window.data !== 'undefined' ? window.data : 'не найдено');

// Check for script tags with data
console.log('\n2. Script tags с данными:');
const scripts = document.querySelectorAll('script');
scripts.forEach((script, index) => {
    const content = script.textContent || script.innerHTML;
    if (content.includes('appid') || content.includes('GetGraphMax') || content.includes('chart') || content.includes('data')) {
        console.log(`Script ${index}:`, content.substring(0, 200));
    }
});

// Check for data attributes
console.log('\n3. Элементы с data-атрибутами:');
const elementsWithData = document.querySelectorAll('[data-appid], [data-chart], [data-id]');
console.log('Найдено элементов:', elementsWithData.length);
elementsWithData.forEach(el => {
    console.log('Element:', el.tagName, el.getAttribute('data-appid') || el.getAttribute('data-chart') || el.getAttribute('data-id'));
});

// Check for canvas or SVG elements (charts)
console.log('\n4. Графики (canvas/SVG):');
const canvases = document.querySelectorAll('canvas');
const svgs = document.querySelectorAll('svg');
console.log('Canvas элементов:', canvases.length);
console.log('SVG элементов:', svgs.length);

// Check for chart libraries
console.log('\n5. Библиотеки графиков:');
console.log('Chart.js:', typeof Chart !== 'undefined' ? 'найдено' : 'не найдено');
console.log('Highcharts:', typeof Highcharts !== 'undefined' ? 'найдено' : 'не найдено');
console.log('Plotly:', typeof Plotly !== 'undefined' ? 'найдено' : 'не найдено');

// Try to find chart data in Chart.js instances
if (typeof Chart !== 'undefined') {
    console.log('\n6. Chart.js instances:');
    // Chart instances might be stored somewhere
}

// Check network requests that were made
console.log('\n7. Проверка выполненных запросов:');
// This would need Performance API

// Check for inline data in HTML
console.log('\n8. Поиск данных в HTML:');
const bodyText = document.body.innerText;
if (bodyText.includes('364770') || bodyText.includes('364790')) {
    console.log('Найдены APP IDs в тексте страницы');
}

// Check for JSON-LD or other structured data
console.log('\n9. Структурированные данные:');
const jsonLd = document.querySelectorAll('script[type="application/ld+json"]');
console.log('JSON-LD элементов:', jsonLd.length);

// Return summary
return {
    hasChartData: typeof window.chartData !== 'undefined',
    scriptsFound: scripts.length,
    elementsWithData: elementsWithData.length,
    chartsFound: canvases.length + svgs.length
};



