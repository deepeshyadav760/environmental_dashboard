// app.js - Open Source Environmental Analysis Dashboard
// Main JavaScript file (No Authentication Required)

// Global variables
var map;
var drawnItems;
var currentPolygon = null;
var analysisLayers = {};
var legendData = {};
var roiSetup = false;
var layersAnalyzed = {};
var currentActiveLayer = 'forest';

// Initialize map
function initMap() {
    map = L.map('map').setView([28.6, 77.2], 6);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);
    
    drawnItems = new L.FeatureGroup();
    map.addLayer(drawnItems);
    
    var drawControl = new L.Control.Draw({
        position: 'topright',
        draw: {
            polygon: {
                allowIntersection: false,
                drawError: {
                    color: '#e1e100',
                    message: '<strong>Error:</strong> shape edges cannot cross!'
                },
                shapeOptions: {
                    color: '#ff0000',
                    weight: 2,
                    fillOpacity: 0.1
                }
            },
            rectangle: {
                shapeOptions: {
                    color: '#ff0000',
                    weight: 2,
                    fillOpacity: 0.1
                }
            },
            circle: false,
            circlemarker: false,
            marker: false,
            polyline: false
        },
        edit: {
            featureGroup: drawnItems,
            remove: true
        }
    });
    
    map.addControl(drawControl);
    
    map.on(L.Draw.Event.CREATED, function(e) {
        var layer = e.layer;
        drawnItems.clearLayers();
        drawnItems.addLayer(layer);
        currentPolygon = layer;
        updateCoordinatesDisplay(layer);
        setupROI();
    });
    
    map.on(L.Draw.Event.EDITED, function(e) {
        e.layers.eachLayer(function(layer) {
            updateCoordinatesDisplay(layer);
            setupROI();
        });
    });
    
    map.on(L.Draw.Event.DELETED, function() {
        currentPolygon = null;
        roiSetup = false;
        clearAllLayers();
        resetLayerStates();
        document.getElementById('coordinatesDisplay').innerHTML = 
            'Draw a polygon on the map to see coordinates here...';
    });
}

function updateCoordinatesDisplay(layer) {
    var coordinates = [];
    if (layer instanceof L.Polygon || layer instanceof L.Rectangle) {
        coordinates = layer.getLatLngs()[0].map(function(latlng) {
            return [latlng.lng, latlng.lat];
        });
    }
    
    if (coordinates.length > 0) {
        coordinates.push(coordinates[0]);
        var coordText = coordinates
            .map(function(coord, i) {
                return (i + 1) + ': [' + coord[0].toFixed(6) + ', ' + coord[1].toFixed(6) + ']';
            })
            .join('\n');
        document.getElementById('coordinatesDisplay').innerHTML = '<pre>' + coordText + '</pre>';
    }
}

async function setupROI() {
    if (!currentPolygon) return;
    
    showStatus('🔄 Setting up ROI and analyzing forest layer...', 'loading');
    
    try {
        var coordinates = currentPolygon.getLatLngs()[0].map(function(latlng) {
            return [latlng.lng, latlng.lat];
        });
        
        const startDate = document.getElementById('startDate').value || '2021-01-01';
        const endDate = document.getElementById('endDate').value || '2023-01-01';
        const resolution = parseInt(document.getElementById('resolutionSelect').value || 10);
        
        var requestData = {
            coordinates: coordinates,
            start_date: startDate,
            end_date: endDate,
            resolution: resolution
        };
        
        const response = await fetch('/api/setup-roi', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.status === 'success') {
            roiSetup = true;
            layersAnalyzed = {
                forest: true,
                wetland: false,
                tundra: false,
                grassland: false,
                algal_blooms: false,
                soil: false,
                chlorophyll: false
            };
            
            showStatus(`ROI setup complete! Forest analysis ready. Area: ${result.area_km2.toFixed(2)} km²`, 'success');
            enableAllLayerToggles();
            await loadLayerData('forest');
            updateLayerVisibility('forest', true);
            updateLayerStatus('forest', 'Analyzed');
            
            var forestToggle = document.getElementById('forestToggle');
            forestToggle.checked = true;
            forestToggle.disabled = false;
        } else {
            showStatus(`ROI setup failed: ${result.detail || 'Unknown error'}`, 'error');
            roiSetup = false;
            resetLayerStates();
        }
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
        roiSetup = false;
        resetLayerStates();
    }
}

function enableAllLayerToggles() {
    var layers = ['forest', 'wetland', 'tundra', 'grassland', 'algal_blooms', 'soil', 'chlorophyll'];
    for (var i = 0; i < layers.length; i++) {
        var toggle = getToggleForLayer(layers[i]);
        if (toggle) {
            toggle.disabled = false;
            if (layers[i] === 'forest') {
                toggle.checked = true;
                updateLayerStatus(layers[i], 'Analyzed');
            } else {
                toggle.checked = false;
                updateLayerStatus(layers[i], 'Click toggle to analyze');
            }
        }
    }
}

async function analyzeLayer(layerType, isReanalysis) {
    if (!roiSetup) {
        showStatus('Please draw a ROI first!', 'error');
        return;
    }
    
    if (layersAnalyzed[layerType] && !isReanalysis) {
        var toggle = getToggleForLayer(layerType);
        if (toggle && toggle.checked) {
            updateLayerVisibility(layerType, true);
        }
        return;
    }
    
    var statusMessage = isReanalysis ? 'Re-analyzing...' : 'Analyzing...';
    updateLayerStatus(layerType, statusMessage);
    
    var layerItem = document.querySelector('.layer-item[data-layer="' + layerType + '"]');
    if (layerItem) {
        layerItem.classList.add('analyzing');
    }
    
    var analysisMessage = isReanalysis ? 
        `🔄 Re-analyzing ${layerType} layer...` : 
        `🔄 Analyzing ${layerType} layer...`;
    showStatus(analysisMessage, 'loading');
    
    try {
        const startDate = document.getElementById('startDate').value || '2021-01-01';
        const endDate = document.getElementById('endDate').value || '2023-01-01';
        const defaultResolution = {
            'forest': 10,
            'wetland': 10,
            'tundra': 250,
            'grassland': 10,
            'algal_blooms': 300,
            'soil': 500,
            'chlorophyll': 4638
        };
        const resolution = parseInt(document.getElementById('resolutionSelect').value || defaultResolution[layerType]);
        
        var requestData = {
            layer_type: layerType,
            start_date: startDate,
            end_date: endDate,
            resolution: resolution
        };
        
        const response = await fetch('/api/analyze-layer', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.status === 'success') {
            layersAnalyzed[layerType] = true;
            var successMessage = isReanalysis ? 
                `${layerType} re-analysis completed!` : 
                `${layerType} analysis completed!`;
            showStatus(successMessage, 'success');
            
            await loadLayerData(layerType);
            updateLayerStatus(layerType, 'Analyzed');
            
            var layerItem = document.querySelector('.layer-item[data-layer="' + layerType + '"]');
            if (layerItem) {
                layerItem.classList.remove('analyzing');
                layerItem.classList.add('active');
            }
            
            var toggle = getToggleForLayer(layerType);
            if (toggle && toggle.checked) {
                updateLayerVisibility(layerType, true);
                setActiveLayer(layerType);
            }
        } else {
            var errorMessage = 'Failed - Click toggle to retry';
            showStatus(`${layerType} analysis failed: ${result.detail || 'Unknown error'}`, 'error');
            updateLayerStatus(layerType, errorMessage);
            
            var layerItem = document.querySelector('.layer-item[data-layer="' + layerType + '"]');
            if (layerItem) {
                layerItem.classList.remove('analyzing');
            }
            
            if (!isReanalysis) {
                var toggle = getToggleForLayer(layerType);
                if (toggle) {
                    toggle.checked = false;
                }
            }
        }
    } catch (error) {
        var errorMessage = 'Error - Click toggle to retry';
        showStatus(`Error analyzing ${layerType}: ${error.message}`, 'error');
        updateLayerStatus(layerType, errorMessage);
        
        var layerItem = document.querySelector('.layer-item[data-layer="' + layerType + '"]');
        if (layerItem) {
            layerItem.classList.remove('analyzing');
        }
        
        if (!isReanalysis) {
            var toggle = getToggleForLayer(layerType);
            if (toggle) {
                toggle.checked = false;
            }
        }
    }
}

async function handleDateChange() {
    if (!roiSetup) {
        return;
    }
    
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    
    var layersToReanalyze = [];
    for (var layerType in layersAnalyzed) {
        if (layersAnalyzed[layerType]) {
            var toggle = getToggleForLayer(layerType);
            if (toggle && toggle.checked) {
                layersToReanalyze.push(layerType);
            }
        }
    }
    
    if (layersToReanalyze.length === 0) {
        return;
    }
    
    showStatus(`🔄 Date range changed to ${startDate} - ${endDate}. Re-analyzing active layers...`, 'loading');
    
    for (let i = 0; i < layersToReanalyze.length; i++) {
        const layerType = layersToReanalyze[i];
        updateLayerStatus(layerType, 'Re-analyzing with new dates...');
        
        setTimeout(function() {
            analyzeLayer(layerType, true);
        }, i * 500);
    }
}

async function handleResolutionChange() {
    if (!roiSetup) {
        return;
    }
    
    const newResolution = document.getElementById('resolutionSelect').value;
    
    var layersToReanalyze = [];
    for (var layerType in layersAnalyzed) {
        if (layersAnalyzed[layerType]) {
            var toggle = getToggleForLayer(layerType);
            if (toggle && toggle.checked) {
                layersToReanalyze.push(layerType);
            }
        }
    }
    
    if (layersToReanalyze.length === 0) {
        return;
    }
    
    showStatus(`🔄 Resolution changed to ${newResolution}m. Re-analyzing active layers...`, 'loading');
    
    for (let i = 0; i < layersToReanalyze.length; i++) {
        const layerType = layersToReanalyze[i];
        updateLayerStatus(layerType, 'Re-analyzing with new resolution...');
        
        setTimeout(function() {
            analyzeLayer(layerType, true);
        }, i * 500);
    }
}

function setActiveLayer(layerType) {
    var allStatsPanels = document.querySelectorAll('.statistics-panel');
    for (var i = 0; i < allStatsPanels.length; i++) {
        allStatsPanels[i].classList.remove('active');
    }
    
    var statsPanel = document.getElementById(layerType + 'Stats');
    if (statsPanel && layersAnalyzed[layerType]) {
        statsPanel.classList.add('active');
        StatisticsManager.loadStatistics(layerType, layersAnalyzed);
    }
    
    currentActiveLayer = layerType;
}

function getToggleForLayer(layerType) {
    const layerTypeMap = {
        'algal_blooms': 'algalBloomsToggle',
        'soil': 'soilToggle',
        'chlorophyll': 'chlorophyllToggle',
        'forest': 'forestToggle',
        'wetland': 'wetlandToggle',
        'tundra': 'tundraToggle',
        'grassland': 'grasslandToggle'
    };
    
    const toggleId = layerTypeMap[layerType];
    if (!toggleId) {
        console.error('Unknown layer type:', layerType);
        return null;
    }
    
    var toggle = document.getElementById(toggleId);
    if (!toggle) {
        console.error('Could not find toggle element with ID:', toggleId);
    }
    return toggle;
}

function updateLayerStatus(layerType, status) {
    var layerItem = document.querySelector('.layer-item[data-layer="' + layerType + '"] .layer-status');
    if (layerItem) {
        layerItem.textContent = status;
    }
}

function resetLayerStates() {
    layersAnalyzed = {
        forest: false,
        wetland: false,
        tundra: false,
        grassland: false,
        algal_blooms: false,
        soil: false,
        chlorophyll: false
    };
    
    var layers = ['forest', 'wetland', 'tundra', 'grassland', 'algal_blooms', 'soil', 'chlorophyll'];
    for (var i = 0; i < layers.length; i++) {
        var toggle = getToggleForLayer(layers[i]);
        if (toggle) {
            toggle.disabled = true;
            toggle.checked = false;
        }
        updateLayerStatus(layers[i], 'Draw ROI to enable');
        
        var layerItem = document.querySelector('.layer-item[data-layer="' + layers[i] + '"]');
        if (layerItem) {
            layerItem.classList.remove('active', 'analyzing');
        }
    }
    
    updateLayerStatus('forest', 'Ready (Default)');
    var forestItem = document.querySelector('.layer-item[data-layer="forest"]');
    if (forestItem) {
        forestItem.classList.add('active');
    }
}

async function loadLayerData(layerType) {
    var promises = [];
    
    // Load map layer
    var mapPromise = fetch(`/api/${layerType}/map-url`)
        .then(async function(response) {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            if (data && data.tile_url && data.tile_url.includes('earthengine.googleapis.com')) {
                analysisLayers[layerType] = L.tileLayer(data.tile_url, {
                    attribution: `Google Earth Engine - ${layerType.charAt(0).toUpperCase() + layerType.slice(1)} Analysis`
                });
                console.log(layerType + ' layer loaded successfully');
            } else {
                console.error('Invalid tile URL for', layerType);
            }
        })
        .catch(function(error) {
            console.error('Error loading ' + layerType + ' layer:', error);
        });
    promises.push(mapPromise);
    
    // Load legend
    var legendPromise = fetch(`/api/legends/${layerType}`)
        .then(async function(response) {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            if (data) {
                legendData[layerType] = data;
                console.log('Loaded legend for', layerType, ':', data);
            }
        })
        .catch(function(error) {
            console.error('Error loading legends for ' + layerType + ':', error);
        });
    promises.push(legendPromise);
    
    return Promise.all(promises);
}

function updateLayerVisibility(layerType, isVisible) {
    console.log('Updating layer visibility for:', layerType, 'visible:', isVisible);
    
    // Remove only the specific layer being toggled
    if (analysisLayers[layerType] && map.hasLayer(analysisLayers[layerType])) {
        map.removeLayer(analysisLayers[layerType]);
    }
    
    // Remove active class from the specific layer item
    var layerItem = document.querySelector('.layer-item[data-layer="' + layerType + '"]');
    if (layerItem) {
        layerItem.classList.remove('active');
    }
    
    if (isVisible && analysisLayers[layerType] && layersAnalyzed[layerType]) {
        // Add the layer back to map
        analysisLayers[layerType].addTo(map);
        console.log('Added layer to map:', layerType);
        
        // Add active class to the layer item
        if (layerItem) {
            layerItem.classList.add('active');
        }
        
        // Show legend for this layer
        if (legendData[layerType]) {
            var legendKey = layerType === 'algal_blooms' ? 'algal_blooms_classification' :
                          layerType === 'soil' ? 'soil_classification' :
                          layerType === 'chlorophyll' ? 'chlorophyll_classification' :
                          layerType + '_classification';
            var legendInfo = legendData[layerType][legendKey];
            console.log('Legend info for', layerType, ':', legendInfo);
            if (legendInfo) {
                showMapLegend(legendInfo);
            }
        }
        
        // Set as active layer for statistics
        setActiveLayer(layerType);
    } else {
        // If turning off this layer, check if any other layers are visible
        var anyLayerVisible = false;
        var lastVisibleLayer = null;
        var validLayers = ['forest', 'wetland', 'tundra', 'grassland', 'algal_blooms', 'soil', 'chlorophyll'];
        
        for (var layer of validLayers) {
            var toggle = getToggleForLayer(layer);
            if (toggle && toggle.checked && layersAnalyzed[layer]) {
                anyLayerVisible = true;
                lastVisibleLayer = layer;
            }
        }
        
        if (anyLayerVisible && lastVisibleLayer) {
            // Show the last visible layer's legend and set it as active
            if (legendData[lastVisibleLayer]) {
                var legendKey = lastVisibleLayer === 'algal_blooms' ? 'algal_blooms_classification' :
                              lastVisibleLayer === 'soil' ? 'soil_classification' :
                              lastVisibleLayer === 'chlorophyll' ? 'chlorophyll_classification' :
                              lastVisibleLayer + '_classification';
                var legendInfo = legendData[lastVisibleLayer][legendKey];
                if (legendInfo) {
                    showMapLegend(legendInfo);
                } else {
                    document.getElementById('mapLegend').style.display = 'none';
                }
            }
            var lastVisibleLayerItem = document.querySelector('.layer-item[data-layer="' + lastVisibleLayer + '"]');
            if (lastVisibleLayerItem) {
                lastVisibleLayerItem.classList.add('active');
            }
            setActiveLayer(lastVisibleLayer);
        } else {
            // No layers visible, hide legend and clear active stats
            document.getElementById('mapLegend').style.display = 'none';
            var allStatsPanels = document.querySelectorAll('.statistics-panel');
            for (var i = 0; i < allStatsPanels.length; i++) {
                allStatsPanels[i].classList.remove('active');
            }
        }
    }
    
    // Keep forest toggle enabled if forest is analyzed
    if (layersAnalyzed['forest']) {
        var forestToggle = document.getElementById('forestToggle');
        if (forestToggle) {
            forestToggle.disabled = false;
        }
    }
}

function showMapLegend(legendInfo) {
    var mapLegend = document.getElementById('mapLegend');
    var html = '<div class="legend-title">' + legendInfo.title + '</div>';
    
    if (legendInfo.type === 'classification') {
        for (var i = 0; i < legendInfo.items.length; i++) {
            var item = legendInfo.items[i];
            var colorPattern = /^#[0-9A-F]{6}$/i;
            var safeColor = colorPattern.test(item.color) ? item.color : '#cccccc';
            html += '<div class="legend-item">' +
                   '<div class="legend-color" style="background-color: ' + safeColor + ';"></div>' +
                   '<span class="legend-label">' + item.label + '</span>' +
                   '</div>';
        }
    }
    
    if (legendInfo.methodology) {
        html += '<div class="legend-description">' + legendInfo.methodology + '</div>';
    }
    
    mapLegend.innerHTML = html;
    mapLegend.style.display = 'block';
}

function showStatus(message, type) {
    if (!type) type = 'loading';
    var container = document.getElementById('statusContainer');
    const validTypes = ['success', 'error', 'loading', 'warning'];
    const safeType = validTypes.includes(type) ? type : 'loading';
    container.innerHTML = '<div class="status ' + safeType + '">' + message + '</div>';
}

function clearStatus() {
    document.getElementById('statusContainer').innerHTML = '';
}

function clearAllLayers() {
    for (var layerType in analysisLayers) {
        if (map.hasLayer(analysisLayers[layerType])) {
            map.removeLayer(analysisLayers[layerType]);
        }
    }
    document.getElementById('mapLegend').style.display = 'none';
    var statsPanels = document.querySelectorAll('.statistics-panel');
    for (var i = 0; i < statsPanels.length; i++) {
        statsPanels[i].classList.remove('active');
    }
    clearStatus();
}

function setupSidebarResize() {
    var sidebar = document.querySelector('.sidebar');
    var resizeHandle = document.querySelector('.resize-handle');
    var isResizing = false;
    
    resizeHandle.addEventListener('mousedown', function(e) {
        isResizing = true;
        document.addEventListener('mousemove', handleResize);
        document.addEventListener('mouseup', stopResize);
        e.preventDefault();
    });
    
    function handleResize(e) {
        if (!isResizing) return;
        var newWidth = e.clientX;
        if (newWidth >= 280 && newWidth <= 800) {
            sidebar.style.width = newWidth + 'px';
        }
    }
    
    function stopResize() {
        isResizing = false;
        document.removeEventListener('mousemove', handleResize);
        document.removeEventListener('mouseup', stopResize);
    }
}

function setupEventListeners() {
    // Layer toggle event listeners
    document.getElementById('forestToggle').addEventListener('change', function(e) {
        if (e.target.checked) {
            if (layersAnalyzed['forest']) {
                updateLayerVisibility('forest', true);
            }
        } else {
            updateLayerVisibility('forest', false);
        }
    });
    
    document.getElementById('wetlandToggle').addEventListener('change', function(e) {
        if (e.target.checked) {
            if (!layersAnalyzed['wetland']) {
                analyzeLayer('wetland');
            } else {
                updateLayerVisibility('wetland', true);
            }
        } else {
            updateLayerVisibility('wetland', false);
        }
    });
    
    document.getElementById('tundraToggle').addEventListener('change', function(e) {
        if (e.target.checked) {
            if (!layersAnalyzed['tundra']) {
                analyzeLayer('tundra');
            } else {
                updateLayerVisibility('tundra', true);
            }
        } else {
            updateLayerVisibility('tundra', false);
        }
    });
    
    document.getElementById('grasslandToggle').addEventListener('change', function(e) {
        if (e.target.checked) {
            if (!layersAnalyzed['grassland']) {
                analyzeLayer('grassland');
            } else {
                updateLayerVisibility('grassland', true);
            }
        } else {
            updateLayerVisibility('grassland', false);
        }
    });
    
    document.getElementById('algalBloomsToggle').addEventListener('change', function(e) {
        if (e.target.checked) {
            if (!layersAnalyzed['algal_blooms']) {
                analyzeLayer('algal_blooms');
            } else {
                updateLayerVisibility('algal_blooms', true);
            }
        } else {
            updateLayerVisibility('algal_blooms', false);
        }
    });
    
    document.getElementById('soilToggle').addEventListener('change', function(e) {
        if (e.target.checked) {
            if (!layersAnalyzed['soil']) {
                analyzeLayer('soil');
            } else {
                updateLayerVisibility('soil', true);
            }
        } else {
            updateLayerVisibility('soil', false);
        }
    });
    
    document.getElementById('chlorophyllToggle').addEventListener('change', function(e) {
        if (e.target.checked) {
            if (!layersAnalyzed['chlorophyll']) {
                analyzeLayer('chlorophyll');
            } else {
                updateLayerVisibility('chlorophyll', true);
            }
        } else {
            updateLayerVisibility('chlorophyll', false);
        }
    });
    
    // Settings panel toggle
    document.getElementById('settingsBtn').addEventListener('click', function(e) {
        e.preventDefault();
        var panel = document.getElementById('settingsPanel');
        panel.classList.toggle('active');
    });
    
    // Click outside to close settings
    document.addEventListener('click', function(e) {
        var settingsBtn = document.getElementById('settingsBtn');
        var settingsPanel = document.getElementById('settingsPanel');
        if (settingsBtn && settingsPanel && 
            !settingsBtn.contains(e.target) && 
            !settingsPanel.contains(e.target)) {
            settingsPanel.classList.remove('active');
        }
    });
    
    // Date and resolution change handlers
    document.getElementById('resolutionSelect').addEventListener('change', handleResolutionChange);
    document.getElementById('startDate').addEventListener('change', handleDateChange);
    document.getElementById('endDate').addEventListener('change', handleDateChange);
}

// Initialize everything when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Wait for Leaflet to load
    if (typeof L === 'undefined') {
        var loadAttempts = 0;
        var maxAttempts = 10;
        
        function tryInitialize() {
            loadAttempts++;
            if (typeof L !== 'undefined') {
                initializeApp();
            } else if (loadAttempts < maxAttempts) {
                setTimeout(tryInitialize, 500);
            } else {
                showStatus('Failed to load map library. Please refresh the page.', 'error');
            }
        }
        
        tryInitialize();
    } else {
        initializeApp();
    }
});

function initializeApp() {
    try {
        initMap();
        setupSidebarResize();
        setupEventListeners();
        
        // Set default values
        document.getElementById('startDate').value = '2021-01-01';
        document.getElementById('endDate').value = '2023-01-01';
        document.getElementById('resolutionSelect').value = '10';
        
        // Initialize layer states
        resetLayerStates();
        
        // Show initial status
        showStatus('🌍 Environmental Analysis Dashboard loaded. Draw a polygon to begin analysis.', 'success');
        
        console.log('Environmental Analysis Dashboard initialized successfully');
        
    } catch (error) {
        console.error('Initialization error:', error);
        showStatus('Application initialization failed. Please refresh the page.', 'error');
    }
}