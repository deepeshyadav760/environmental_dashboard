# legends/legend_configs.py - Updated Legend Configurations

LEGEND_CONFIGS = {
    "forest": {
        "forest_classification": {
            "title": "Forest Classification",
            "type": "classification",
            "items": [
                {
                    "value": 1,
                    "label": "Sparse/Non-Forest",
                    "color": "#FFFF00",
                    "description": "NDVI < 0.3 - Sparse vegetation or non-forest areas"
                },
                {
                    "value": 2,
                    "label": "Moderate Forest",
                    "color": "#90EE90",
                    "description": "NDVI 0.3-0.6 - Moderate forest density"
                },
                {
                    "value": 3,
                    "label": "Dense Forest",
                    "color": "#006400",
                    "description": "NDVI > 0.6 - Dense forest canopy"
                }
            ],
            "methodology": "Multi-satellite NDVI analysis using Sentinel-2 and Landsat data",
            "data_sources": "Sentinel-2 SR Harmonized, Landsat 8 Surface Reflectance"
        }
    },
    
    "wetland": {
        "wetland_classification": {
            "title": "Wetland Classification",
            "type": "classification",
            "items": [
                {
                    "value": 1,
                    "label": "Dry Upland",
                    "color": "#8B4513",
                    "description": "Non-wetland terrestrial areas"
                },
                {
                    "value": 2,
                    "label": "Transitional Wetland",
                    "color": "#FFFF00",
                    "description": "Wetland transition zones with seasonal variation"
                },
                {
                    "value": 3,
                    "label": "Swamp Forest",
                    "color": "#00FF00",
                    "description": "Forested wetlands with standing water"
                },
                {
                    "value": 4,
                    "label": "Marsh/Fen",
                    "color": "#00FFFF",
                    "description": "Herbaceous wetlands and peatlands"
                },
                {
                    "value": 5,
                    "label": "Open Water",
                    "color": "#0000FF",
                    "description": "Permanent water bodies and lakes"
                }
            ],
            "methodology": "Multi-spectral analysis using NDVI, MNDWI, and NDMI indices",
            "data_sources": "Sentinel-2 SR Harmonized"
        }
    },
    
    "tundra": {
        "tundra_classification": {
            "title": "Tundra Classification",
            "type": "classification",
            "items": [
                {
                    "value": 0,
                    "label": "No Tundra",
                    "color": "#ffffff",
                    "description": "Areas not meeting tundra criteria"
                },
                {
                    "value": 1,
                    "label": "Arctic Tundra",
                    "color": "#1f78b4",
                    "description": "Cold lowland tundra with permafrost indicators"
                },
                {
                    "value": 2,
                    "label": "Alpine Tundra",
                    "color": "#a6cee3",
                    "description": "High-altitude tundra above treeline"
                },
                {
                    "value": 3,
                    "label": "Wet Tundra",
                    "color": "#33a02c",
                    "description": "Waterlogged tundra with high soil moisture"
                },
                {
                    "value": 4,
                    "label": "Shrub/Dry Tundra",
                    "color": "#ff7f00",
                    "description": "Drier tundra with shrub vegetation"
                }
            ],
            "methodology": "Multi-parameter analysis: NDVI + LST + Elevation + NDWI + Permafrost probability",
            "data_sources": "Sentinel-2 SR Harmonized, MODIS Land Surface Temperature"
        }
    },
    
    "grassland": {
        "grassland_classification": {
            "title": "Grassland & Savanna Classification",
            "type": "classification",
            "items": [
                {
                    "value": 0,
                    "label": "Non-Vegetation",
                    "color": "#8B4513",
                    "description": "NDVI < 0.2 - Bare soil, rocks, urban areas"
                },
                {
                    "value": 1,
                    "label": "Grassland",
                    "color": "#FFFF00",
                    "description": "NDVI 0.2-0.45 - Herbaceous grassland"
                },
                {
                    "value": 2,
                    "label": "Savanna",
                    "color": "#90EE90",
                    "description": "NDVI 0.45-0.7 - Mixed grass-tree savanna"
                },
                {
                    "value": 3,
                    "label": "Dense Vegetation",
                    "color": "#006400",
                    "description": "NDVI > 0.7 - Dense vegetation/forest"
                }
            ],
            "methodology": "NDVI-based classification with biomass estimation",
            "data_sources": "Sentinel-2 SR Harmonized, Landsat 8 (backup)"
        }
    },
    
    "algal_blooms": {
        "algal_blooms_classification": {
            "title": "Algal Blooms Detection",
            "type": "classification",
            "items": [
                {
                    "value": 1,
                    "label": "No Bloom / Clear Water",
                    "color": "#87CEEB",
                    "description": "NDCI ≤ 0.05 - Clear water conditions"
                },
                {
                    "value": 2,
                    "label": "Low Bloom Risk",
                    "color": "#FFFF00",
                    "description": "NDCI 0.05-0.1 - Slight elevation in chlorophyll"
                },
                {
                    "value": 3,
                    "label": "Moderate Bloom",
                    "color": "#FFA500",
                    "description": "NDCI 0.1-0.2 - Visible algal activity"
                },
                {
                    "value": 4,
                    "label": "Severe Bloom",
                    "color": "#FF0000",
                    "description": "NDCI > 0.2 - High bloom concentration"
                }
            ],
            "methodology": "Water-masked NDCI analysis with JRC Global Surface Water masking",
            "data_sources": "Sentinel-3 OLCI Ocean Color Radiometry"
        }
    },
    
    "soil": {
        "soil_classification": {
            "title": "Soil Moisture Classification",
            "type": "classification",
            "items": [
                {
                    "value": 1,
                    "label": "Dry Soil",
                    "color": "#D2691E",
                    "description": "Low moisture: NDVI < 0.25, NDWI < 0.1, LST > 34°C"
                },
                {
                    "value": 2,
                    "label": "Moderate Moisture",
                    "color": "#DEB887",
                    "description": "Moderate conditions: NDVI 0.2-0.4, LST 28-35°C"
                },
                {
                    "value": 3,
                    "label": "High Moisture",
                    "color": "#8B4513",
                    "description": "Wet conditions: NDWI > 0.2, LST < 32°C"
                }
            ],
            "methodology": "Multi-index analysis combining NDVI, NDWI, and Land Surface Temperature",
            "data_sources": "Sentinel-2 SR Harmonized, MODIS Land Surface Temperature"
        }
    },

    "chlorophyll": {
        "chlorophyll_classification": {
            "title": "Ocean Chlorophyll-a Concentration",
            "type": "classification",
            "items": [
                {
                    "value": 0,
                    "label": "Oligotrophic Ocean (0-5 mg/m³)",
                    "color": "#081d58",
                    "description": "0-5 mg/m³ - Nutrient-poor, clear blue water"
                },
                {
                    "value": 1,
                    "label": "Mesotrophic Ocean (5-15 mg/m³)",
                    "color": "#225ea8",
                    "description": "5-15 mg/m³ - Moderately productive waters"
                },
                {
                    "value": 2,
                    "label": "Moderately Eutrophic (15-30 mg/m³)",
                    "color": "#41b6c4",
                    "description": "15-30 mg/m³ - Productive coastal waters"
                },
                {
                    "value": 3,
                    "label": "Eutrophic Ocean (30-90 mg/m³)",
                    "color": "#a1dab4",
                    "description": "30-90 mg/m³ - Highly productive waters"
                },
                {
                    "value": 4,
                    "label": "Hypereutrophic (90+ mg/m³)",
                    "color": "#e31a1c",
                    "description": "90+ mg/m³ - Very high nutrients, bloom risk"
                }
            ],
            "methodology": "Multi-satellite ocean color analysis with trophic classification",
            "data_sources": "MODIS Aqua, VIIRS SNPP, MODIS Terra, Sentinel-3 OLCI",
            "note": "Analysis applies only to ocean/marine areas. Land areas are masked out."
        }
    }
}

# Satellite information for each analysis type
SATELLITE_INFO = {
    "forest": {
        "primary": "Sentinel-2 SR Harmonized",
        "backup": "Landsat 8 Surface Reflectance",
        "resolution": "10-30m",
        "revisit": "5-16 days"
    },
    "wetland": {
        "primary": "Sentinel-2 SR Harmonized", 
        "resolution": "10m",
        "revisit": "5 days"
    },
    "tundra": {
        "primary": "Sentinel-2 SR Harmonized",
        "secondary": "MODIS Land Surface Temperature",
        "resolution": "10-250m",
        "revisit": "5 days (Sentinel-2), Daily (MODIS)"
    },
    "grassland": {
        "primary": "Sentinel-2 SR Harmonized",
        "backup": "Landsat 8 Surface Reflectance", 
        "resolution": "10-30m",
        "revisit": "5-16 days"
    },
    "algal_blooms": {
        "primary": "Sentinel-3 OLCI",
        "resolution": "300m",
        "revisit": "2-3 days"
    },
    "soil": {
        "primary": "Sentinel-2 SR Harmonized",
        "secondary": "MODIS Land Surface Temperature",
        "resolution": "10-500m", 
        "revisit": "5 days (Sentinel-2), Daily (MODIS)"
    },
    "chlorophyll": {
        "primary": "MODIS Aqua L3SMI",
        "alternatives": ["VIIRS SNPP", "MODIS Terra", "Sentinel-3 OLCI"],
        "resolution": "300-4638m",
        "revisit": "Daily (MODIS/VIIRS), 2-3 days (Sentinel-3)"
    }
}