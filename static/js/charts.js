// === CARGA Y RENDERIZADO DE GRÁFICOS ===


async function loadCategoryCharts(category) {
    try {
        if (category === 'artists') {
            await loadChart('artists', 'countries', 'chart-artists-countries');
            await loadChart('artists', 'top', 'chart-artists-top');
        } else if (category === 'albums') {
            await loadChart('albums', 'decades', 'chart-albums-decades');
            await loadChart('albums', 'genres', 'chart-albums-genres');
            await loadChart('albums', 'labels', 'chart-albums-labels');
        } else if (category === 'songs') {
            await loadChart('songs', 'genres', 'chart-songs-genres');
        }
    } catch (error) {
        console.error('Error cargando gráficos:', error);
    }
}

async function loadChart(category, chartType, containerId) {
    try {
        const response = await fetch(`/api/stats/charts/${category}/${chartType}`);
        const data = await response.json();
        
        if (data.error) {
            console.error(`Error cargando gráfico ${category}/${chartType}:`, data.error);
            return;
        }
        
        const chartDiv = document.getElementById(containerId);
        if (!chartDiv) {
            console.error(`Contenedor ${containerId} no encontrado`);
            return;
        }
        
        // Parsear el JSON del gráfico de Plotly
        const plotlyData = JSON.parse(data.chart);
        
        // Renderizar con Plotly
        Plotly.newPlot(containerId, plotlyData.data, plotlyData.layout, {
            responsive: true,
            displayModeBar: false
        });
        
    } catch (error) {
        console.error(`Error renderizando gráfico ${category}/${chartType}:`, error);
    }
}


// === RENDERIZADO ESPECÍFICO DE GRÁFICOS ===

function renderChart(chartId, chartData) {
    const container = document.getElementById(chartId);
    if (!container) {
        console.error(`❌ Contenedor ${chartId} no encontrado`);
        return;
    }
    
    try {
        if (typeof chartData === 'string') {
            chartData = JSON.parse(chartData);
        }
        
        renderPlotlyChart(chartId, chartData);
    } catch (error) {
        console.error(`❌ Error renderizando gráfico ${chartId}:`, error);
        handleChartError(chartId, error);
    }
}

function renderPlotlyChart(containerId, plotData) {
    try {
        const chartContainer = document.getElementById(containerId);
        if (!chartContainer) {
            console.error(`❌ Contenedor ${containerId} no encontrado`);
            return;
        }
        
        console.log(`📈 Renderizando gráfico: ${containerId}`);
        
        const data = typeof plotData === 'string' ? JSON.parse(plotData) : plotData;
        
        if (window.Plotly && data.data && data.layout) {
            Plotly.newPlot(containerId, data.data, data.layout, {
                responsive: true,
                displayModeBar: false
            });
            console.log(`✅ Gráfico ${containerId} renderizado correctamente`);
        } else {
            console.error(`❌ Datos de gráfico inválidos para ${containerId}:`, data);
            handleChartError(containerId, new Error('Datos de gráfico inválidos'));
        }
    } catch (error) {
        console.error(`💥 Error renderizando gráfico ${containerId}:`, error);
        handleChartError(containerId, error);
    }
}

// === UTILIDADES DE GRÁFICOS ===
function createChartConfig(type, data, title) {
    const baseConfig = {
        responsive: true,
        displayModeBar: false
    };
    
    const baseLayout = {
        title: title,
        font: { color: '#ffffff' },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        margin: { t: 50, r: 50, b: 50, l: 50 }
    };
    
    switch (type) {
        case 'pie':
            return {
                data: [{
                    type: 'pie',
                    values: data.map(d => d.value || d.count),
                    labels: data.map(d => d.label || d.name),
                    textinfo: 'label+percent',
                    textposition: 'outside'
                }],
                layout: baseLayout,
                config: baseConfig
            };
        
        case 'bar':
            return {
                data: [{
                    type: 'bar',
                    x: data.map(d => d.x || d.name),
                    y: data.map(d => d.y || d.value || d.count),
                    marker: { color: '#a8e6cf' }
                }],
                layout: {
                    ...baseLayout,
                    xaxis: { color: '#ffffff' },
                    yaxis: { color: '#ffffff' }
                },
                config: baseConfig
            };
        
        case 'line':
            return {
                data: [{
                    type: 'scatter',
                    mode: 'lines+markers',
                    x: data.map(d => d.x || d.date),
                    y: data.map(d => d.y || d.value || d.count),
                    line: { color: '#a8e6cf' },
                    marker: { color: '#a8e6cf' }
                }],
                layout: {
                    ...baseLayout,
                    xaxis: { color: '#ffffff' },
                    yaxis: { color: '#ffffff' }
                },
                config: baseConfig
            };
        
        default:
            return { data: [], layout: baseLayout, config: baseConfig };
    }
}

function handleChartError(chartId, error) {
    const container = document.getElementById(chartId);
    if (container) {
        container.innerHTML = `
            <div style="text-align: center; color: #ff6b6b; padding: 20px; background: rgba(220, 53, 69, 0.1); border-radius: 10px;">
                <i class="fas fa-exclamation-triangle" style="font-size: 2rem; margin-bottom: 10px; display: block;"></i>
                <p>Error renderizando gráfico</p>
                <small>${error.message}</small>
            </div>
        `;
    }
}