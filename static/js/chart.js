// ECharts visualization for price histogram
document.addEventListener('DOMContentLoaded', function() {
  const chartContainer = document.getElementById('chart-container');
  
  if (!chartContainer) return;

  // Initialize ECharts instance
  const chart = echarts.init(chartContainer);
  
  // Get data from the data attributes
  const priceData = JSON.parse(chartContainer.dataset.prices || '[]');
  const outlierData = JSON.parse(chartContainer.dataset.outliers || '[]');
  const item = chartContainer.dataset.item || '';
  const url = chartContainer.dataset.url || '';
  const currentDate = chartContainer.dataset.date || '';
  const numberOfPages = chartContainer.dataset.pages || '1';
  const failedPages = chartContainer.dataset.failed || '0';
  const exchangeRate = parseFloat(chartContainer.dataset.exchange || '0');
  const currency = chartContainer.dataset.currency || 'ARS';
  const countryName = chartContainer.dataset.country || 'Argentina';
  const countryCode = chartContainer.dataset.countryCode || 'ar';
  
  // Calculate statistics (already available in the HTML, but recalculated for completeness)
  const medianPrice = parseFloat(chartContainer.dataset.median || '0');
  const avgPrice = parseFloat(chartContainer.dataset.avg || '0');
  const maxPrice = parseFloat(chartContainer.dataset.max || '0');
  const minPrice = parseFloat(chartContainer.dataset.min || '0');
  const stdDev = Math.sqrt(priceData.reduce((sum, price) => sum + Math.pow(price - avgPrice, 2), 0) / priceData.length);
  
  // Store all data including outliers for filtering
  const allData = [...priceData, ...outlierData];
  
  // Create price objects with extra data for the table view
  const priceObjects = allData.map(price => {
    // Calculate if it's a potential accessory (price < 40% of median)
    const isPotentialAccessory = price < (medianPrice * 0.4);
    // Calculate if it's a statistical outlier (more than 3 std devs from mean)
    const isOutlier = Math.abs(price - avgPrice) > (3 * stdDev);
    
    return {
      price: price,
      usdPrice: Math.round(price / exchangeRate),
      isPotentialAccessory,
      isOutlier,
      included: !isOutlier  // Default inclusion based on standard filter
    };
  });
  
  // Filtering state variables
  let currentFilter = 'standard'; // 'standard', 'aggressive', 'all'
  let userExcludedItems = new Set(); // For manual filtering
  let currentData = priceData;
  
  // Add filtering controls to the UI
  addFilteringControls();
  
  // Add data table for manual filtering
  addDataTable();

  // Function to format numbers with commas
  function formatNumber(num) {
    return new Intl.NumberFormat('es-AR').format(Math.round(num));
  }
  
  // Function to format numbers with abbreviations (K, M)
  function abbreviateNumber(num) {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return Math.round(num).toString();
  }

  // Function to add filtering controls to the UI
  function addFilteringControls() {
    // Create a container for the controls
    const controlsContainer = document.createElement('div');
    controlsContainer.id = 'filter-controls';
    controlsContainer.className = 'mb-4 flex flex-wrap gap-2 items-center';
    controlsContainer.innerHTML = `
      <span class="font-medium">Filtrado de productos:</span>
      <div class="flex rounded-md shadow-sm">
        <button id="filter-standard" class="px-3 py-1 bg-blue-600 text-white rounded-l-md">Estándar</button>
        <button id="filter-aggressive" class="px-3 py-1 bg-blue-100 text-blue-800 border-y border-blue-300">Agresivo</button>
        <button id="filter-all" class="px-3 py-1 bg-blue-100 text-blue-800 rounded-r-md border-y border-r border-blue-300">Todos</button>
      </div>
      <span class="text-sm text-gray-500 ml-2">${priceData.length} de ${allData.length} productos mostrados</span>
      <button id="show-data-table" class="ml-auto px-3 py-1 bg-green-600 text-white rounded-md hover:bg-green-700 transition duration-300">
        Filtrar manualmente
      </button>
    `;
    
    // Insert the controls before the chart
    chartContainer.parentNode.insertBefore(controlsContainer, chartContainer);
    
    // Add event listeners
    document.getElementById('filter-standard').addEventListener('click', () => applyFilter('standard'));
    document.getElementById('filter-aggressive').addEventListener('click', () => applyFilter('aggressive'));
    document.getElementById('filter-all').addEventListener('click', () => applyFilter('all'));
    document.getElementById('show-data-table').addEventListener('click', toggleDataTable);
  }
  
  // Function to add data table for manual filtering
  function addDataTable() {
    const dataTableContainer = document.createElement('div');
    dataTableContainer.id = 'data-table-container';
    dataTableContainer.className = 'hidden mb-6 bg-white p-4 rounded-lg shadow-md';
    dataTableContainer.innerHTML = `
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-bold">Filtrado Manual de Productos</h3>
        <button id="close-data-table" class="px-2 py-1 bg-gray-200 text-gray-800 rounded hover:bg-gray-300">Cerrar</button>
      </div>
      <p class="text-sm text-gray-600 mb-2">Seleccione qué productos incluir o excluir del análisis:</p>
      <div class="flex gap-4 mb-4">
        <button id="select-all" class="px-3 py-1 bg-blue-100 text-blue-800 rounded hover:bg-blue-200">Seleccionar todos</button>
        <button id="deselect-all" class="px-3 py-1 bg-red-100 text-red-800 rounded hover:bg-red-200">Deseleccionar todos</button>
        <button id="toggle-outliers" class="px-3 py-1 bg-yellow-100 text-yellow-800 rounded hover:bg-yellow-200">Excluir outliers</button>
        <button id="toggle-accessories" class="px-3 py-1 bg-purple-100 text-purple-800 rounded hover:bg-purple-200">Excluir accesorios</button>
      </div>
      <div class="max-h-96 overflow-y-auto">
        <table class="min-w-full border border-gray-300">
          <thead class="sticky top-0 bg-gray-100">
            <tr>
              <th class="border border-gray-300 px-4 py-2">Incluir</th>
              <th class="border border-gray-300 px-4 py-2">Precio (${currency})</th>
              <th class="border border-gray-300 px-4 py-2">Precio (USD)</th>
              <th class="border border-gray-300 px-4 py-2">Tipo</th>
            </tr>
          </thead>
          <tbody id="price-table-body">
            ${generatePriceTableRows()}
          </tbody>
        </table>
      </div>
      <div class="mt-4 flex justify-end">
        <button id="apply-manual-filter" class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">Aplicar Filtros</button>
      </div>
    `;
    
    // Insert the data table after the chart
    chartContainer.parentNode.insertBefore(dataTableContainer, chartContainer.nextSibling);
    
    // Add event listeners for the data table
    document.getElementById('close-data-table').addEventListener('click', toggleDataTable);
    document.getElementById('select-all').addEventListener('click', () => selectAllProducts(true));
    document.getElementById('deselect-all').addEventListener('click', () => selectAllProducts(false));
    document.getElementById('toggle-outliers').addEventListener('click', toggleOutliers);
    document.getElementById('toggle-accessories').addEventListener('click', toggleAccessories);
    document.getElementById('apply-manual-filter').addEventListener('click', applyManualFilter);
    
    // Add event listeners for individual checkboxes
    document.querySelectorAll('.product-checkbox').forEach(checkbox => {
      checkbox.addEventListener('change', function() {
        const priceId = parseInt(this.getAttribute('data-price'));
        const priceObj = priceObjects.find(item => item.price === priceId);
        if (priceObj) {
          priceObj.included = this.checked;
        }
      });
    });
  }
  
  // Generate table rows for all prices
  function generatePriceTableRows() {
    return priceObjects
      .sort((a, b) => a.price - b.price) // Sort by price ascending
      .map(priceObj => {
        const priceId = priceObj.price;
        const formattedPrice = formatNumber(priceObj.price);
        const formattedUsdPrice = formatNumber(priceObj.usdPrice);
        
        // Determine the product type for display
        let productType = 'Normal';
        let typeClass = 'text-gray-800';
        
        if (priceObj.isOutlier) {
          if (priceObj.price > avgPrice) {
            productType = 'Outlier (alto)';
            typeClass = 'text-red-600 font-medium';
          } else {
            productType = 'Outlier (bajo)';
            typeClass = 'text-orange-600 font-medium';
          }
        }
        
        if (priceObj.isPotentialAccessory) {
          productType = 'Posible accesorio';
          typeClass = 'text-purple-600 font-medium';
        }
        
        return `
          <tr class="hover:bg-gray-50">
            <td class="border border-gray-300 px-4 py-2 text-center">
              <input type="checkbox" class="product-checkbox" data-price="${priceId}" ${priceObj.included ? 'checked' : ''}>
            </td>
            <td class="border border-gray-300 px-4 py-2 text-right">${formattedPrice}</td>
            <td class="border border-gray-300 px-4 py-2 text-right">${formattedUsdPrice}</td>
            <td class="border border-gray-300 px-4 py-2 ${typeClass}">${productType}</td>
          </tr>
        `;
      })
      .join('');
  }
  
  // Function to toggle the data table visibility
  function toggleDataTable() {
    const dataTable = document.getElementById('data-table-container');
    const showDataTableBtn = document.getElementById('show-data-table');
    
    if (dataTable.classList.contains('hidden')) {
      dataTable.classList.remove('hidden');
      showDataTableBtn.textContent = 'Ocultar tabla';
      showDataTableBtn.classList.replace('bg-green-600', 'bg-gray-600');
    } else {
      dataTable.classList.add('hidden');
      showDataTableBtn.textContent = 'Filtrar manualmente';
      showDataTableBtn.classList.replace('bg-gray-600', 'bg-green-600');
    }
  }
  
  // Function to select or deselect all products
  function selectAllProducts(select) {
    priceObjects.forEach(obj => {
      obj.included = select;
    });
    
    // Update checkboxes
    document.querySelectorAll('.product-checkbox').forEach(checkbox => {
      checkbox.checked = select;
    });
  }
  
  // Function to toggle outliers
  function toggleOutliers() {
    priceObjects.forEach(obj => {
      if (obj.isOutlier) {
        obj.included = false;
      }
    });
    
    // Update checkboxes
    document.querySelectorAll('.product-checkbox').forEach(checkbox => {
      const priceId = parseInt(checkbox.getAttribute('data-price'));
      const priceObj = priceObjects.find(item => item.price === priceId);
      if (priceObj && priceObj.isOutlier) {
        checkbox.checked = false;
      }
    });
  }
  
  // Function to toggle accessories
  function toggleAccessories() {
    priceObjects.forEach(obj => {
      if (obj.isPotentialAccessory) {
        obj.included = false;
      }
    });
    
    // Update checkboxes
    document.querySelectorAll('.product-checkbox').forEach(checkbox => {
      const priceId = parseInt(checkbox.getAttribute('data-price'));
      const priceObj = priceObjects.find(item => item.price === priceId);
      if (priceObj && priceObj.isPotentialAccessory) {
        checkbox.checked = false;
      }
    });
  }
  
  // Function to apply manual filter
  function applyManualFilter() {
    // Update current data based on included prices
    currentData = priceObjects
      .filter(obj => obj.included)
      .map(obj => obj.price);
    
    // Update the count display
    const countSpan = document.getElementById('filter-controls').querySelector('span.text-sm');
    countSpan.textContent = `${currentData.length} de ${allData.length} productos mostrados (filtrado manual)`;
    
    // Update the chart
    updateChart();
    
    // Hide the data table
    toggleDataTable();
    
    // Set all filter buttons to inactive state
    document.getElementById('filter-standard').className = 'px-3 py-1 bg-blue-100 text-blue-800 rounded-l-md border-y border-l border-blue-300';
    document.getElementById('filter-aggressive').className = 'px-3 py-1 bg-blue-100 text-blue-800 border-y border-blue-300';
    document.getElementById('filter-all').className = 'px-3 py-1 bg-blue-100 text-blue-800 rounded-r-md border-y border-r border-blue-300';
  }
  
  // Function to apply filter and update the chart
  function applyFilter(filterType) {
    // Update active button styling
    document.getElementById('filter-standard').className = 'px-3 py-1 bg-blue-100 text-blue-800 rounded-l-md border-y border-l border-blue-300';
    document.getElementById('filter-aggressive').className = 'px-3 py-1 bg-blue-100 text-blue-800 border-y border-blue-300';
    document.getElementById('filter-all').className = 'px-3 py-1 bg-blue-100 text-blue-800 rounded-r-md border-y border-r border-blue-300';
    
    document.getElementById(`filter-${filterType}`).className = 'px-3 py-1 bg-blue-600 text-white';
    if (filterType === 'standard') {
      document.getElementById('filter-standard').className = 'px-3 py-1 bg-blue-600 text-white rounded-l-md';
    } else if (filterType === 'aggressive') {
      document.getElementById('filter-aggressive').className = 'px-3 py-1 bg-blue-600 text-white';
    } else {
      document.getElementById('filter-all').className = 'px-3 py-1 bg-blue-600 text-white rounded-r-md';
    }
    
    currentFilter = filterType;
    
    // Apply the selected filter
    if (filterType === 'standard') {
      // Standard filter - use the default outlier detection from backend
      currentData = priceData;
      
      // Update price objects for the table view
      priceObjects.forEach(obj => {
        obj.included = !obj.isOutlier;
      });
    } else if (filterType === 'aggressive') {
      // Aggressive filter - remove anything less than 40% of the median price
      // This targets accessories in product searches (like PS4 controllers when searching for PS4)
      const lowerThreshold = medianPrice * 0.4;
      currentData = allData.filter(price => price >= lowerThreshold);
      
      // Update price objects for the table view
      priceObjects.forEach(obj => {
        obj.included = !obj.isOutlier && !obj.isPotentialAccessory;
      });
    } else {
      // No filter - show all data
      currentData = allData;
      
      // Update price objects for the table view
      priceObjects.forEach(obj => {
        obj.included = true;
      });
    }
    
    // Update the count display
    const countSpan = document.getElementById('filter-controls').querySelector('span.text-sm');
    countSpan.textContent = `${currentData.length} de ${allData.length} productos mostrados`;
    
    // Update checkboxes in table if it exists
    document.querySelectorAll('.product-checkbox').forEach(checkbox => {
      const priceId = parseInt(checkbox.getAttribute('data-price'));
      const priceObj = priceObjects.find(item => item.price === priceId);
      if (priceObj) {
        checkbox.checked = priceObj.included;
      }
    });
    
    // Update the chart
    updateChart();
  }

  // Generate histogram data
  function generateHistogramData(prices) {
    if (!prices || prices.length === 0) {
      return { bins: [], counts: [] };
    }
    
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const range = max - min;
    
    // Calculate appropriate bin size based on data range
    const numberOfBins = 20;
    const binSize = range / numberOfBins;
    
    // Initialize bins and counts
    const bins = [];
    const counts = [];
    
    // Fill bins and initialize counts
    for (let i = 0; i < numberOfBins; i++) {
      const binStart = min + i * binSize;
      const binEnd = min + (i + 1) * binSize;
      bins.push(`${currency} ${formatNumber(binStart)} - ${formatNumber(binEnd)}`);
      counts.push(0);
    }
    
    // Count items in each bin
    prices.forEach(price => {
      const binIndex = Math.min(Math.floor((price - min) / binSize), numberOfBins - 1);
      counts[binIndex]++;
    });
    
    return { bins, counts };
  }

  // Function to update the chart with current data
  function updateChart() {
    // Calculate statistics for the filtered data
    const filteredMedian = currentData.length > 0 ? percentile(currentData, 0.5) : medianPrice;
    const filteredAvg = currentData.length > 0 ? currentData.reduce((a, b) => a + b, 0) / currentData.length : avgPrice;
    const filteredMax = currentData.length > 0 ? Math.max(...currentData) : maxPrice;
    const filteredMin = currentData.length > 0 ? Math.min(...currentData) : minPrice;
    const filteredStdDev = Math.sqrt(currentData.reduce((sum, price) => sum + Math.pow(price - filteredAvg, 2), 0) / Math.max(1, currentData.length));
    
    // Generate histogram data from the filtered data
    const histogramData = generateHistogramData(currentData);
    
    // Determine if we're using MercadoLibre or MercadoLivre based on country
    const marketplaceName = countryCode === 'br' ? 'MercadoLivre' : 'MercadoLibre';
    
    // Update chart options
    const option = {
      title: {
        text: `Histogram of ${item.replace('-', ' ').toUpperCase()} prices in ${marketplaceName} ${countryName} (${currentDate})`,
        subtext: `Number of items indexed: ${currentData.length} of ${allData.length} (${numberOfPages} pages)\nURL: ${url}\nFailed to parse ${failedPages} pages.`,
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        },
        formatter: function(params) {
          const range = params[0].name;
          const count = params[0].value;
          const localCurrency = range.split(' - ')[0].replace(`${currency} `, '');
          
          // Only show USD conversion if exchange rate is valid and country is Argentina
          let usdPart = '';
          if (countryCode === 'ar' && exchangeRate > 0) {
            const usdValue = Math.round(parseInt(localCurrency.replace(/,/g, '')) / exchangeRate);
            if (usdValue > 12) {
              usdPart = `<br><strong>USD:</strong> ~${formatNumber(usdValue)} USD`;
            }
          }
          
          return `<strong>Price Range:</strong> ${range}<br>
                  <strong>Count:</strong> ${count} items${usdPart}`;
        }
      },
      toolbox: {
        feature: {
          saveAsImage: { title: 'Save as Image' },
          dataZoom: { title: 'Zoom' },
          restore: { title: 'Restore' }
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: histogramData.bins,
        name: `Price in ${currency}`,
        nameLocation: 'middle',
        nameGap: 30,
        axisLabel: {
          rotate: 45,
          formatter: function(value) {
            // Extract the price value from the range string
            const priceMatch = value.match(/(\d[\d.,]*)/);
            if (priceMatch && priceMatch[1]) {
              const priceValue = parseFloat(priceMatch[1].replace(/[,.]/g, ''));
              return `${currency} ${abbreviateNumber(priceValue)}`;
            }
            return value;
          }
        }
      },
      yAxis: {
        type: 'value',
        name: 'Frequency',
        nameLocation: 'middle',
        nameGap: 40
      },
      series: [
        {
          name: 'Frequency',
          type: 'bar',
          barWidth: '99%',
          data: histogramData.counts,
          itemStyle: {
            color: '#9fd5f7',
            borderColor: '#1a253a',
            borderWidth: 1
          }
        },
        // Vertical lines for statistics
        createMarkLine('Median', filteredMedian, '#ff4d4f'),  // Red
        createMarkLine('Average', filteredAvg, '#9254de'),    // Purple
        createMarkLine('Maximum', filteredMax, '#1890ff'),    // Blue
        createMarkLine('Minimum', filteredMin, '#1890ff', 'dashed'),    // Blue dashed
        createMarkLine('Std Dev', filteredAvg + filteredStdDev, '#000000', 'dotted'),  // Black dotted
        createMarkLine('25th Percentile', percentile(currentData, 0.25), '#52c41a', 'dashed')  // Green dashed
      ]
    };
    
    // Apply the chart options
    chart.setOption(option);
  }

  // Function to create a mark line for statistics
  function createMarkLine(name, value, color, lineType = 'solid') {
    return {
      name,
      type: 'line',
      markLine: {
        silent: true,
        symbol: 'none',
        label: {
          formatter: `${name}: {c} ${currency}`,
          position: 'insideEndTop',
          fontSize: 12,
          color: color,
          backgroundColor: 'rgba(255, 255, 255, 0.8)',
          padding: [2, 4]
        },
        lineStyle: {
          color: color,
          type: lineType,
          width: name === 'Std Dev' ? 2 : 1
        },
        data: [
          { 
            xAxis: value,
            name: name
          }
        ]
      }
    };
  }

  // Initial chart update with standard filter
  updateChart();
  
  // Make chart responsive
  window.addEventListener('resize', function() {
    chart.resize();
  });
  
  // Add chart to window for potential external access
  window.priceHistogramChart = chart;
});

// Function to calculate percentile
function percentile(data, p) {
  if (!data || data.length === 0) return 0;
  const sorted = [...data].sort((a, b) => a - b);
  const pos = (sorted.length - 1) * p;
  const base = Math.floor(pos);
  const rest = pos - base;
  
  if (sorted[base + 1] !== undefined) {
    return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
  } else {
    return sorted[base];
  }
}

// Function to format numbers with commas
function formatNumber(num) {
  return new Intl.NumberFormat('es-AR').format(Math.round(num));
}