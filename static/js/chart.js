// ECharts visualization for price histogram
document.addEventListener('DOMContentLoaded', function() {
  const chartContainer = document.getElementById('chart-container');
  
  if (!chartContainer) return;

  // Initialize ECharts instance
  const chart = echarts.init(chartContainer);
  
  // Get data from the data attributes
  const priceData = JSON.parse(chartContainer.dataset.prices || '[]');
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

  // Generate histogram data
  const histogramData = generateHistogramData(priceData);

  // Determine if we're using MercadoLibre or MercadoLivre based on country
  const marketplaceName = countryCode === 'br' ? 'MercadoLivre' : 'MercadoLibre';
  
  // Chart options
  const option = {
    title: {
      text: `Histogram of ${item.replace('-', ' ').toUpperCase()} prices in ${marketplaceName} ${countryName} (${currentDate})`,
      subtext: `Number of items indexed: ${priceData.length} (${numberOfPages} pages)\nURL: ${url}\nFailed to parse ${failedPages} pages.`,
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
      createMarkLine('Median', medianPrice, '#ff4d4f'),  // Red
      createMarkLine('Average', avgPrice, '#9254de'),    // Purple
      createMarkLine('Maximum', maxPrice, '#1890ff'),    // Blue
      createMarkLine('Minimum', minPrice, '#1890ff', 'dashed'),    // Blue dashed
      createMarkLine('Std Dev', avgPrice + stdDev, '#000000', 'dotted'),  // Black dotted
      createMarkLine('25th Percentile', percentile(priceData, 0.25), '#52c41a', 'dashed')  // Green dashed
    ]
  };

  // Apply the chart options
  chart.setOption(option);
  
  // Make chart responsive
  window.addEventListener('resize', function() {
    chart.resize();
  });
  
  // Add chart to window for potential external access
  window.priceHistogramChart = chart;
});

// Function to generate histogram data from raw prices
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
  
  // Get currency from data attributes
  const currency = document.getElementById('chart-container').dataset.currency || 'ARS';
  
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

// Function to create a mark line for statistics
function createMarkLine(name, value, color, lineType = 'solid') {
  const currency = document.getElementById('chart-container').dataset.currency || 'ARS';
  
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

// Function to calculate percentile
function percentile(data, p) {
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