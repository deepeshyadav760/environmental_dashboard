// apis_statistics.js - Statistics Loading and Display Functions
// Handles all statistics-related functionality for the Environmental Analysis Dashboard

// Statistics loading and display manager
const StatisticsManager = {
    
    // Load statistics for a specific layer
    async loadStatistics(layerType, layersAnalyzed) {
        console.log("Loading statistics for:", layerType);
        
        if (layersAnalyzed[layerType]) {
            try {
                const response = await fetch(`/api/${layerType}/statistics`);
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                
                const data = await response.json();
                console.log("Statistics data received for " + layerType + ":", data);
                
                if (data && Object.keys(data).length > 0) {
                    this.displayStatistics(layerType, data);
                } else {
                    document.getElementById(`${layerType}StatsContent`).innerHTML = 
                        '<div class="stat-item">No statistics available</div>';
                    this.showStatus(`⚠️ No statistics available for ${layerType}`, 'warning');
                }
            } catch (error) {
                console.error('Error loading ' + layerType + ' statistics:', error);
                document.getElementById(`${layerType}StatsContent`).innerHTML = 
                    '<div class="stat-item">Error loading data</div>';
                this.showStatus(`⚠️ Could not load ${layerType} statistics`, 'error');
            }
        }
    },

    // Route statistics to appropriate display function
    displayStatistics(layerType, data) {
        console.log("Displaying statistics for:", layerType, "with data:", data);
        
        const displayFunctions = {
            'forest': this.displayForestStatistics,
            'wetland': this.displayWetlandStatistics,
            'tundra': this.displayTundraStatistics,
            'grassland': this.displayGrasslandStatistics,
            'algal_blooms': this.displayAlgalBloomsStatistics,
            'soil': this.displaySoilStatistics,
            'chlorophyll': this.displayChlorophyllStatistics
        };
        
        const displayFunc = displayFunctions[layerType];
        if (displayFunc && data) {
            displayFunc.call(this, data);
        } else {
            console.error("No display function or data for layer:", layerType);
            document.getElementById(`${layerType}StatsContent`).innerHTML = 
                '<div class="stat-item">No display function or data available</div>';
        }
    },

    // Forest statistics display
    displayForestStatistics(data) {
        console.log("DisplayForestStatistics data:", data);
        
        if (!data || Object.keys(data).length === 0) {
            document.getElementById('forestStatsContent').innerHTML = 
                '<div class="stat-item">No statistics data available</div>';
            return;
        }
        
        var content = '';
        content += '<div class="stat-section-header">🌲 Forest Analysis</div>';
        
        if (data.roi_area_km2) {
            content += '<div class="stat-item"><span class="stat-label">ROI Area (km²):</span><span class="stat-value">' + 
                       data.roi_area_km2.toFixed(2) + ' km²</span></div>';
        }
        if (data.roi_area_ha) {
            content += '<div class="stat-item"><span class="stat-label">ROI Area (ha):</span><span class="stat-value">' + 
                       data.roi_area_ha.toFixed(2) + ' ha</span></div>';
        }
        if (data.mean_NDVI) {
            content += '<div class="stat-item"><span class="stat-label">Mean NDVI:</span><span class="stat-value">' + 
                       data.mean_NDVI.toFixed(4) + '</span></div>';
        }
        if (data.mean_NBR) {
            content += '<div class="stat-item"><span class="stat-label">Mean NBR:</span><span class="stat-value">' + 
                       data.mean_NBR.toFixed(4) + '</span></div>';
        }
        if (data.forest_classification) {
            content += '<div class="stat-item"><span class="stat-label">Forest Classification:</span><span class="stat-value">' + 
                       data.forest_classification + '</span></div>';
        }
        
        if (data.biomass_partitioning) {
            content += '<div class="stat-section-header">📏 Biomass Partitioning</div>';
            const biomassPart = data.biomass_partitioning;
            if (biomassPart.aboveground_biomass_Mg_per_ha !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Aboveground Biomass:</span><span class="stat-value">' + 
                           biomassPart.aboveground_biomass_Mg_per_ha.toFixed(2) + ' Mg/ha</span></div>';
            }
            if (biomassPart.belowground_biomass_Mg_per_ha !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Belowground Biomass:</span><span class="stat-value">' + 
                           biomassPart.belowground_biomass_Mg_per_ha.toFixed(2) + ' Mg/ha</span></div>';
            }
            if (biomassPart.total_biomass_Mg_per_ha !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Total Biomass per Hectare:</span><span class="stat-value">' + 
                           biomassPart.total_biomass_Mg_per_ha.toFixed(2) + ' Mg/ha</span></div>';
            }
        }
        
        if (data.biomass_estimation) {
            content += '<div class="stat-section-header">🌱 Biomass Estimation</div>';
            const biomassEst = data.biomass_estimation;
            if (biomassEst.average_biomass_Mg_per_ha !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Average Biomass per Hectare:</span><span class="stat-value">' + 
                           biomassEst.average_biomass_Mg_per_ha.toFixed(2) + ' Mg/ha</span></div>';
            }
            if (biomassEst.total_biomass_Mg !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Total Biomass:</span><span class="stat-value">' + 
                           biomassEst.total_biomass_Mg.toFixed(2) + ' Mg</span></div>';
            }
        }
        
        if (data.carbon_stock_estimation) {
            content += '<div class="stat-section-header">🌍 Carbon Stock</div>';
            const carbonStock = data.carbon_stock_estimation;
            if (carbonStock.conversion_factor !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Conversion Factor:</span><span class="stat-value">' + 
                           carbonStock.conversion_factor.toFixed(2) + '</span></div>';
            }
            if (carbonStock.average_carbon_stock_MgC_per_ha !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Average Carbon Stock per Hectare:</span><span class="stat-value">' + 
                           carbonStock.average_carbon_stock_MgC_per_ha.toFixed(2) + ' MgC/ha</span></div>';
            }
            if (carbonStock.total_carbon_stock_MgC !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Total Carbon Stock:</span><span class="stat-value">' + 
                           carbonStock.total_carbon_stock_MgC.toFixed(2) + ' MgC</span></div>';
            }
        }
        
        if (data.co2_equivalent_estimation) {
            content += '<div class="stat-section-header">☁️ CO₂ Equivalent</div>';
            const co2Eq = data.co2_equivalent_estimation;
            if (co2Eq.conversion_factor !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Conversion Factor:</span><span class="stat-value">' + 
                           co2Eq.conversion_factor.toFixed(2) + '</span></div>';
            }
            if (co2Eq.total_co2_eq_Mg !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Total CO₂ Equivalent:</span><span class="stat-value">' + 
                           co2Eq.total_co2_eq_Mg.toFixed(2) + ' Mg</span></div>';
            }
        }
        
        document.getElementById('forestStatsContent').innerHTML = content;
    },

    // Wetland statistics display
    displayWetlandStatistics(data) {
        console.log("DisplayWetlandStatistics data:", data);
        
        if (!data || Object.keys(data).length === 0) {
            document.getElementById('wetlandStatsContent').innerHTML = 
                '<div class="stat-item">No statistics data available</div>';
            return;
        }
        
        var content = '';
        content += '<div class="stat-section-header">🌊 Wetland Overview</div>';
        
        if (data.roi_area_km2 || data.area_km2) {
            content += '<div class="stat-item"><span class="stat-label">ROI Area (km²):</span><span class="stat-value">' + 
                       (data.roi_area_km2 || data.area_km2).toFixed(2) + ' km²</span></div>';
        }
        if (data.roi_area_ha) {
            content += '<div class="stat-item"><span class="stat-label">ROI Area (ha):</span><span class="stat-value">' + 
                       data.roi_area_ha.toFixed(2) + ' ha</span></div>';
        }
        if (data.mean_ndwi) {
            content += '<div class="stat-item"><span class="stat-label">Mean NDWI:</span><span class="stat-value">' + 
                       data.mean_ndwi.toFixed(3) + '</span></div>';
        }
        if (data.mean_mndwi) {
            content += '<div class="stat-item"><span class="stat-label">Mean MNDWI:</span><span class="stat-value">' + 
                       data.mean_mndwi.toFixed(3) + '</span></div>';
        }
        if (data.wetland_class) {
            content += '<div class="stat-item"><span class="stat-label">Wetland Class:</span><span class="stat-value">' + 
                       data.wetland_class + '</span></div>';
        }
        if (data.water_frequency_index) {
            content += '<div class="stat-item"><span class="stat-label">Water Frequency Index:</span><span class="stat-value">' + 
                       data.water_frequency_index.toFixed(2) + ' (' + (data.water_frequency_index * 100).toFixed(0) + '% waterlogged)</span></div>';
        }
        
        if (data.change_over_time) {
            content += '<div class="stat-section-header">📈 Wetland Change Over Time</div>';
            const changeData = data.change_over_time;
            if (changeData.start_year && changeData.end_year && changeData.wetland_area_ha) {
                const startArea = changeData.wetland_area_ha[0];
                const endArea = changeData.wetland_area_ha[1];
                const changeHa = endArea - startArea;
                const changePercent = ((changeHa / startArea) * 100).toFixed(1);
                content += '<div class="stat-item"><span class="stat-label">Wetland Area (ha):</span><span class="stat-value">' + 
                           startArea.toFixed(2) + ' ha (' + changeData.start_year + ') → ' + 
                           endArea.toFixed(2) + ' ha (' + changeData.end_year + ') → ' + 
                           changeHa.toFixed(2) + ' ha (' + changePercent + '%)</span></div>';
            }
        }
        
        if (data.biomass_carbon) {
            content += '<div class="stat-section-header">🪵 Biomass & Carbon Sequestration</div>';
            const bioCarbon = data.biomass_carbon;
            if (bioCarbon.aboveground_biomass_Mg_per_ha !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Aboveground Biomass:</span><span class="stat-value">' + 
                           bioCarbon.aboveground_biomass_Mg_per_ha.toFixed(2) + ' Mg/ha</span></div>';
            }
            if (bioCarbon.total_carbon_stock_MgC !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Total Carbon Stock (MgC):</span><span class="stat-value">' + 
                           bioCarbon.total_carbon_stock_MgC.toFixed(2) + ' MgC</span></div>';
            }
            if (bioCarbon.co2_equivalent_MgCO2e !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">CO₂ Equivalent:</span><span class="stat-value">' + 
                           bioCarbon.co2_equivalent_MgCO2e.toFixed(2) + ' MgCO₂e</span></div>';
            }
        }
        
        document.getElementById('wetlandStatsContent').innerHTML = content;
    },

    // Tundra statistics display
    displayTundraStatistics(data) {
        var content = '';
        content += '<div class="stat-section-header">🏔️ Tundra Analysis</div>';
        
        if (data.roi_area_km2) {
            content += '<div class="stat-item"><span class="stat-label">Total ROI Area:</span><span class="stat-value">' + 
                       data.roi_area_km2.toFixed(2) + ' km²</span></div>';
        }
        if (data.analysis_method) {
            content += '<div class="stat-item"><span class="stat-label">Analysis Method:</span><span class="stat-value">' + 
                       data.analysis_method + '</span></div>';
        }
        
        if (data.total_tundra_area_km2 !== undefined && data.tundra_coverage_percent !== undefined) {
            content += '<div class="stat-section-header">🌡️ Tundra Coverage</div>';
            content += '<div class="stat-item"><span class="stat-label">Total Tundra Area:</span><span class="stat-value">' + 
                       data.total_tundra_area_km2.toFixed(2) + ' km²</span></div>';
            content += '<div class="stat-item"><span class="stat-label">Tundra Coverage:</span><span class="stat-value">' + 
                       data.tundra_coverage_percent.toFixed(1) + '%</span></div>';
            if (data.dominant_tundra_type) {
                content += '<div class="stat-item"><span class="stat-label">Dominant Type:</span><span class="stat-value">' + 
                           data.dominant_tundra_type + '</span></div>';
            }
        }
        
        if (data.class_areas_km2) {
            content += '<div class="stat-section-header">📊 Class Distribution</div>';
            const classAreas = data.class_areas_km2;
            if (classAreas.arctic_tundra !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Arctic Tundra:</span><span class="stat-value">' + 
                           classAreas.arctic_tundra.toFixed(2) + ' km²</span></div>';
            }
            if (classAreas.alpine_tundra !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Alpine Tundra:</span><span class="stat-value">' + 
                           classAreas.alpine_tundra.toFixed(2) + ' km²</span></div>';
            }
            if (classAreas.wet_tundra !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Wet Tundra:</span><span class="stat-value">' + 
                           classAreas.wet_tundra.toFixed(2) + ' km²</span></div>';
            }
            if (classAreas.shrub_dry_tundra !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Shrub/Dry Tundra:</span><span class="stat-value">' + 
                           classAreas.shrub_dry_tundra.toFixed(2) + ' km²</span></div>';
            }
        }
        
        if (data.environmental_indicators) {
            content += '<div class="stat-section-header">🌍 Environmental Indicators</div>';
            if (data.environmental_indicators.mean_temperature_celsius !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Mean Temperature:</span><span class="stat-value">' + 
                           data.environmental_indicators.mean_temperature_celsius.toFixed(1) + ' °C</span></div>';
            }
            if (data.environmental_indicators.mean_ndvi !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Mean NDVI:</span><span class="stat-value">' + 
                           data.environmental_indicators.mean_ndvi.toFixed(2) + '</span></div>';
            }
            if (data.environmental_indicators.permafrost_probability !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Permafrost Probability:</span><span class="stat-value">' + 
                           data.environmental_indicators.permafrost_probability.toFixed(2) + '</span></div>';
            }
        }
        
        document.getElementById('tundraStatsContent').innerHTML = content;
    },

    // Grassland statistics display
    displayGrasslandStatistics(data) {
        var content = '';
        content += '<div class="stat-section-header">🌾 Grassland Analysis</div>';
        
        if (data.grassland_analysis && data.grassland_analysis.roi_area_km2) {
            content += '<div class="stat-item"><span class="stat-label">ROI Area (km²):</span><span class="stat-value">' + 
                       data.grassland_analysis.roi_area_km2.toFixed(2) + ' km²</span></div>';
        }
        if (data.grassland_analysis && data.grassland_analysis.roi_area_hectares) {
            content += '<div class="stat-item"><span class="stat-label">ROI Area (ha):</span><span class="stat-value">' + 
                       data.grassland_analysis.roi_area_hectares.toFixed(2) + ' ha</span></div>';
        }
        if (data.grassland_analysis && data.grassland_analysis.mean_ndvi) {
            content += '<div class="stat-item"><span class="stat-label">Mean NDVI:</span><span class="stat-value">' + 
                       data.grassland_analysis.mean_ndvi.toFixed(3) + '</span></div>';
        }
        
        if (data.grassland_analysis && data.grassland_analysis.vegetation_classification) {
            content += '<div class="stat-section-header">📊 Vegetation Classification</div>';
            const vegClass = data.grassland_analysis.vegetation_classification;
            if (vegClass.non_vegetation_area_ha !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Non-Vegetation Area:</span><span class="stat-value">' + 
                           vegClass.non_vegetation_area_ha.toFixed(2) + ' ha</span></div>';
            }
            if (vegClass.grassland_area_ha !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Grassland Area:</span><span class="stat-value">' + 
                           vegClass.grassland_area_ha.toFixed(2) + ' ha</span></div>';
            }
            if (vegClass.savanna_area_ha !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Savanna Area:</span><span class="stat-value">' + 
                           vegClass.savanna_area_ha.toFixed(2) + ' ha</span></div>';
            }
            if (vegClass.dense_vegetation_area_ha !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Dense Vegetation Area:</span><span class="stat-value">' + 
                           vegClass.dense_vegetation_area_ha.toFixed(2) + ' ha</span></div>';
            }
        }
        
        if (data.grassland_analysis && data.grassland_analysis.carbon_estimation) {
            content += '<div class="stat-section-header">🌍 Carbon Estimation</div>';
            const carbonEst = data.grassland_analysis.carbon_estimation;
            if (carbonEst.total_biomass_Mg !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Total Biomass:</span><span class="stat-value">' + 
                           carbonEst.total_biomass_Mg.toFixed(2) + ' Mg</span></div>';
            }
            if (carbonEst.total_carbon_stock_MgC !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Total Carbon Stock:</span><span class="stat-value">' + 
                           carbonEst.total_carbon_stock_MgC.toFixed(2) + ' MgC</span></div>';
            }
            if (carbonEst.co2_equivalent_MgCO2e !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">CO₂ Equivalent:</span><span class="stat-value">' + 
                           carbonEst.co2_equivalent_MgCO2e.toFixed(2) + ' MgCO₂e</span></div>';
            }
        }
        
        if (data.methodology) {
            content += '<div class="stat-section-header">⚙️ Methodology</div>';
            if (data.methodology.approach) {
                content += '<div class="stat-item"><span class="stat-label">Approach:</span><span class="stat-value">' + 
                           data.methodology.approach + '</span></div>';
            }
            if (data.methodology.data_source) {
                content += '<div class="stat-item"><span class="stat-label">Data Source:</span><span class="stat-value">' + 
                           data.methodology.data_source + '</span></div>';
            }
        }
        
        document.getElementById('grasslandStatsContent').innerHTML = content;
    },

    // Algal blooms statistics display
    displayAlgalBloomsStatistics(data) {
        var content = '';
        content += '<div class="stat-section-header">🌊 Algal Blooms Analysis</div>';
        
        if (data.roi_area_sq_km) {
            content += '<div class="stat-item"><span class="stat-label">ROI Area:</span><span class="stat-value">' + 
                       data.roi_area_sq_km.toFixed(2) + ' km²</span></div>';
        }
        if (data.mean_ndci) {
            content += '<div class="stat-item"><span class="stat-label">Mean NDCI:</span><span class="stat-value">' + 
                       data.mean_ndci.toFixed(2) + '</span></div>';
        }
        if (data.bloom_detected !== undefined) {
            content += '<div class="stat-item"><span class="stat-label">Bloom Detected:</span><span class="stat-value">' + 
                       data.bloom_detected.toString() + '</span></div>';
        }
        if (data.severity_level) {
            content += '<div class="stat-item"><span class="stat-label">Severity Level:</span><span class="stat-value">' + 
                       data.severity_level + '</span></div>';
        }
        if (data.bloom_extent_sq_km) {
            content += '<div class="stat-item"><span class="stat-label">Bloom Extent:</span><span class="stat-value">' + 
                       data.bloom_extent_sq_km.toFixed(2) + ' km²</span></div>';
        }
        
        if (data.classification_by_area_ha) {
            content += '<div class="stat-section-header">📊 Classification by Area</div>';
            const classData = data.classification_by_area_ha;
            if (classData.no_bloom_ha !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">No Bloom:</span><span class="stat-value">' + 
                           classData.no_bloom_ha.toFixed(2) + ' ha</span></div>';
            }
            if (classData.low_bloom_ha !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Low Bloom:</span><span class="stat-value">' + 
                           classData.low_bloom_ha.toFixed(2) + ' ha</span></div>';
            }
            if (classData.moderate_bloom_ha !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Moderate Bloom:</span><span class="stat-value">' + 
                           classData.moderate_bloom_ha.toFixed(2) + ' ha</span></div>';
            }
            if (classData.severe_bloom_ha !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Severe Bloom:</span><span class="stat-value">' + 
                           classData.severe_bloom_ha.toFixed(2) + ' ha</span></div>';
            }
        }
        
        if (data.water_quality_indicators) {
            content += '<div class="stat-section-header">💧 Water Quality Indicators</div>';
            if (data.water_quality_indicators.chlorophyll_indicator) {
                content += '<div class="stat-item"><span class="stat-label">Chlorophyll Indicator:</span><span class="stat-value">' + 
                           data.water_quality_indicators.chlorophyll_indicator + '</span></div>';
            }
            if (data.water_quality_indicators.turbidity_level) {
                content += '<div class="stat-item"><span class="stat-label">Turbidity Level:</span><span class="stat-value">' + 
                           data.water_quality_indicators.turbidity_level + '</span></div>';
            }
        }
        
        document.getElementById('algalBloomsStatsContent').innerHTML = content;
    },

    // Soil statistics display
    displaySoilStatistics(data) {
        var content = '';
        content += '<div class="stat-section-header">🌍 Soil Moisture Analysis</div>';
        
        if (data.roi_area_km2) {
            content += '<div class="stat-item"><span class="stat-label">ROI Area:</span><span class="stat-value">' + 
                       data.roi_area_km2.toFixed(2) + ' km²</span></div>';
        }
        if (data.soil_moisture_index) {
            content += '<div class="stat-item"><span class="stat-label">Soil Moisture Index:</span><span class="stat-value">' + 
                       data.soil_moisture_index.toFixed(2) + '</span></div>';
        }
        if (data.soil_moisture_level) {
            content += '<div class="stat-item"><span class="stat-label">Moisture Level:</span><span class="stat-value">' + 
                       data.soil_moisture_level + '</span></div>';
        }
        if (data.vegetation_index_ndvi) {
            content += '<div class="stat-item"><span class="stat-label">Vegetation Index (NDVI):</span><span class="stat-value">' + 
                       data.vegetation_index_ndvi.toFixed(3) + '</span></div>';
        }
        if (data.water_index_ndwi) {
            content += '<div class="stat-item"><span class="stat-label">Water Index (NDWI):</span><span class="stat-value">' + 
                       data.water_index_ndwi.toFixed(3) + '</span></div>';
        }
        if (data.land_surface_temperature_c) {
            content += '<div class="stat-item"><span class="stat-label">Land Surface Temperature:</span><span class="stat-value">' + 
                       data.land_surface_temperature_c.toFixed(1) + ' °C</span></div>';
        }
        
        if (data.data_availability) {
            content += '<div class="stat-section-header">📊 Data Availability</div>';
            if (data.data_availability.sentinel2_available !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">Sentinel-2 Available:</span><span class="stat-value">' + 
                           data.data_availability.sentinel2_available.toString() + '</span></div>';
            }
            if (data.data_availability.modis_lst_available !== undefined) {
                content += '<div class="stat-item"><span class="stat-label">MODIS LST Available:</span><span class="stat-value">' + 
                           data.data_availability.modis_lst_available.toString() + '</span></div>';
            }
        }
        
        document.getElementById('soilStatsContent').innerHTML = content;
    },

    // Chlorophyll statistics display
    displayChlorophyllStatistics(data) {
        var content = '';
        content += '<div class="stat-section-header">🌊 Chlorophyll Analysis</div>';
        
        if (data.roi_area_km2) {
            content += '<div class="stat-item"><span class="stat-label">Total ROI Area:</span><span class="stat-value">' + 
                       data.roi_area_km2.toFixed(2) + ' km²</span></div>';
        }
        if (data.land_area_km2) {
            content += '<div class="stat-item"><span class="stat-label">Land Area:</span><span class="stat-value">' + 
                       data.land_area_km2.toFixed(2) + ' km²</span></div>';
        }
        if (data.ocean_area_km2) {
            content += '<div class="stat-item"><span class="stat-label">Ocean Area:</span><span class="stat-value">' + 
                       data.ocean_area_km2.toFixed(2) + ' km²</span></div>';
        }
        if (data.ocean_coverage_percent) {
            content += '<div class="stat-item"><span class="stat-label">Ocean Coverage:</span><span class="stat-value">' + 
                       data.ocean_coverage_percent.toFixed(1) + '%</span></div>';
        }
        if (data.mean_chlorophyll_mg_m3) {
            content += '<div class="stat-item"><span class="stat-label">Mean Chlorophyll-a:</span><span class="stat-value">' + 
                       data.mean_chlorophyll_mg_m3.toFixed(2) + ' mg/m³</span></div>';
        }
        if (data.trophic_status) {
            content += '<div class="stat-item"><span class="stat-label">Trophic Status:</span><span class="stat-value">' + 
                       data.trophic_status + '</span></div>';
        }
        if (data.water_quality_assessment) {
            content += '<div class="stat-item"><span class="stat-label">Water Quality:</span><span class="stat-value">' + 
                       data.water_quality_assessment + '</span></div>';
        }
        if (data.bloom_risk) {
            content += '<div class="stat-item"><span class="stat-label">Bloom Risk:</span><span class="stat-value">' + 
                       data.bloom_risk + '</span></div>';
        }
        if (data.analysis_applicable !== undefined) {
            content += '<div class="stat-item"><span class="stat-label">Analysis Applicable:</span><span class="stat-value">' + 
                       data.analysis_applicable.toString() + '</span></div>';
        }
        if (data.recommendation) {
            content += '<div class="stat-item"><span class="stat-label">Recommendation:</span><span class="stat-value">' + 
                       data.recommendation + '</span></div>';
        }
        
        if (data.data_source) {
            content += '<div class="stat-section-header">📊 Data Source</div>';
            content += '<div class="stat-item"><span class="stat-label">Satellite Source:</span><span class="stat-value">' + 
                       data.data_source + '</span></div>';
            if (data.images_processed) {
                content += '<div class="stat-item"><span class="stat-label">Images Processed:</span><span class="stat-value">' + 
                           data.images_processed + '</span></div>';
            }
        }
        
        document.getElementById('chlorophyllStatsContent').innerHTML = content;
    },

    // Status display helper
    showStatus(message, type) {
        if (!type) type = 'loading';
        var container = document.getElementById('statusContainer');
        const validTypes = ['success', 'error', 'loading', 'warning'];
        const safeType = validTypes.includes(type) ? type : 'loading';
        container.innerHTML = '<div class="status ' + safeType + '">' + message + '</div>';
    }
};

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StatisticsManager;
}