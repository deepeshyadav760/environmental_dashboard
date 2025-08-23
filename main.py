# main.py - Open Source Environmental Analysis Dashboard (No Authentication)

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import ee
import json
import os
import logging
from datetime import datetime
import os
import uvicorn

# Import API modules
from api.wetland_api import WetlandAPI
from api.forest_api import ForestAPI
from api.ocean_api import OceanAPI
from api.grassland_api import GrasslandAPI
from api.tundra_api import TundraAPI
from api.algal_blooms_api import AlgalBloomsAPI
from api.soil_api import SoilAPI
from legends.legend_configs import LEGEND_CONFIGS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Earth Engine
def initialize_earth_engine():
    try:
        # For cloud hosting with service account
        credentials_json = os.environ.get('EE_SERVICE_ACCOUNT_CREDENTIALS')
        if credentials_json:
            credentials_info = json.loads(credentials_json)
            credentials = ee.ServiceAccountCredentials(
                credentials_info['client_email'],
                key_data=credentials_json
            )
            ee.Initialize(credentials)
        else:
            # Fallback to default initialization
            ee.Initialize(project=os.environ.get('EE_PROJECT', 'ee-deepeshy'))
        
        logger.info("Earth Engine initialized successfully")
    except Exception as e:
        logger.error(f"Earth Engine initialization failed: {e}")

# Initialize Earth Engine
initialize_earth_engine()

app = FastAPI(
    title="Environmental Analysis Dashboard", 
    version="1.0.0",
    description="Open Source Environmental Analysis Platform"
)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# Initialize API modules
wetland_api = WetlandAPI()
ocean_api = OceanAPI()
tundra_api = TundraAPI()
forest_api = ForestAPI()
grassland_api = GrasslandAPI()
algal_blooms_api = AlgalBloomsAPI()
soil_api = SoilAPI()

# Simplified Pydantic models
class AnalysisRequest(BaseModel):
    coordinates: List[List[float]]
    start_date: str = "2021-01-01"
    end_date: str = "2023-01-01"
    resolution: Optional[int] = 10

class LayerAnalysisRequest(BaseModel):
    layer_type: str
    start_date: Optional[str] = "2021-01-01"
    end_date: Optional[str] = "2023-01-01"
    resolution: Optional[int] = 10



# Global variables to store analysis results
current_analysis = {
    "forest": {
        "classification": None,
        "statistics": None,
        "roi": None,
        "area_km2": None,
        "analyzed": False
    },
    "wetland": {
        "classified": None,
        "roi": None,
        "s2_image": None,
        "area_km2": None,
        "analyzed": False
    },
    "tundra": {
        "classification": None,
        "statistics": None,
        "roi": None,
        "area_km2": None,
        "analyzed": False
    },
    "grassland": {
        "classification": None,
        "statistics": None,
        "roi": None,
        "area_km2": None,
        "analyzed": False
    },
    "algal_blooms": {
        "classification": None,
        "statistics": None,
        "roi": None,
        "area_km2": None,
        "analyzed": False
    },
    "soil": {
        "classification": None,
        "statistics": None,
        "roi": None,
        "area_km2": None,
        "analyzed": False
    },
    "chlorophyll": {
        "classification": None,
        "statistics": None,
        "roi": None,
        "area_km2": None,
        "analyzed": False
    }
}

# Store current ROI
current_roi = {
    "coordinates": None,
    "geometry": None,
    "area_km2": None
}

# Main dashboard route
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main dashboard"""
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        logger.error("index.html not found in static directory")
        return HTMLResponse(content="<h1>Application Error: Please ensure index.html is in the static directory</h1>")

# ROI setup endpoint
@app.post("/api/setup-roi")
async def setup_roi(analysis_request: AnalysisRequest):
    """Set up ROI and perform initial forest analysis"""
    global current_roi, current_analysis
    
    try:
        coordinates = [[float(coord[0]), float(coord[1])] for coord in analysis_request.coordinates]
        roi = ee.Geometry.Polygon([coordinates])
        
        # Calculate area
        area_km2 = roi.area(maxError=100).divide(1e6).getInfo()
        
        # Store ROI for future use
        current_roi = {
            "coordinates": coordinates,
            "geometry": roi,
            "area_km2": area_km2
        }
        
        # Reset all analysis states
        for layer in current_analysis:
            current_analysis[layer]["analyzed"] = False
            current_analysis[layer]["classification"] = None
            current_analysis[layer]["statistics"] = None
        
        resolution = analysis_request.resolution or 10
        
        # Analyze forest by default
        forest_result = forest_api.classify_forest_and_estimate_biomass(
            coordinates, analysis_request.start_date, analysis_request.end_date, resolution
        )
        
        if forest_result["status"] == "success":
            current_analysis["forest"] = {
                "classification": forest_result["classification_image"],
                "statistics": forest_result["statistics"],
                "roi": roi,
                "area_km2": area_km2,
                "analyzed": True
            }
            logger.info("Forest analysis completed successfully")
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Forest analysis failed: {forest_result.get('error', 'Unknown error')}"
            )
        
        return {
            "status": "success",
            "area_km2": area_km2,
            "analysis_period": f"{analysis_request.start_date} to {analysis_request.end_date}",
            "resolution": f"{resolution}m",
            "message": "ROI setup complete. Forest analysis ready."
        }
        
    except Exception as e:
        logger.error(f"ROI setup error: {e}")
        raise HTTPException(status_code=500, detail=f"ROI setup failed: {str(e)}")

# Layer analysis endpoint
@app.post("/api/analyze-layer")
async def analyze_layer(layer_request: LayerAnalysisRequest):
    """Analyze a specific layer on demand"""
    global current_roi, current_analysis

    if not current_roi["coordinates"]:
        raise HTTPException(status_code=400, detail="No ROI defined. Please draw a polygon first.")

    layer_type = layer_request.layer_type.lower()
    if layer_type not in current_analysis:
        raise HTTPException(status_code=400, detail=f"Invalid layer type: {layer_type}")

    try:
        coordinates = current_roi["coordinates"]
        roi = current_roi["geometry"]
        area_km2 = current_roi["area_km2"]
        resolution = layer_request.resolution or 10

        logger.info(f"Analyzing {layer_type} layer...")

        if layer_type == "forest":
            forest_result = forest_api.classify_forest_and_estimate_biomass(
                coordinates, layer_request.start_date, layer_request.end_date, resolution
            )
            if forest_result["status"] == "success":
                current_analysis["forest"] = {
                    "classification": forest_result["classification_image"],
                    "statistics": forest_result["statistics"],
                    "roi": roi,
                    "area_km2": area_km2,
                    "analyzed": True
                }
                logger.info("Forest analysis completed successfully")
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Forest analysis failed: {forest_result.get('error', 'Data not available')}"
                )

        elif layer_type == "wetland":
            wetland_result = wetland_api.analyze_wetland(
                coordinates, layer_request.start_date, layer_request.end_date, resolution
            )
            if wetland_result["status"] == "success":
                current_analysis["wetland"] = {
                    "classified": wetland_result["classification_image"],
                    "roi": roi,
                    "area_km2": area_km2,
                    "analyzed": True,
                    "statistics": wetland_result["statistics"]
                }
                logger.info("Wetland analysis completed successfully")
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Wetland analysis failed: {wetland_result.get('error', 'Data not available')}"
                )

        elif layer_type == "tundra":
            tundra_result = tundra_api.analyze_tundra(
                coordinates, layer_request.start_date, layer_request.end_date, 250
            )
            if tundra_result["status"] == "success":
                current_analysis["tundra"] = {
                    "classification": tundra_result["classification_image"],
                    "statistics": tundra_result["statistics"],
                    "roi": roi,
                    "area_km2": area_km2,
                    "analyzed": True
                }
                logger.info("Tundra analysis completed successfully")
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Tundra analysis failed: {tundra_result.get('error', 'Data not available')}"
                )

        elif layer_type == "grassland":
            grassland_result = grassland_api.analyze_grassland(
                coordinates, layer_request.start_date, layer_request.end_date, resolution
            )
            if grassland_result["status"] == "success":
                current_analysis["grassland"] = {
                    "classification": grassland_result["classification_image"].clip(roi),
                    "statistics": grassland_result["statistics"],
                    "roi": roi,
                    "area_km2": area_km2,
                    "analyzed": True
                }
                logger.info("Grassland analysis completed successfully")
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Grassland analysis failed: {grassland_result.get('error', 'Data not available')}"
                )

        elif layer_type == "algal_blooms":
            algal_result = algal_blooms_api.detect_algal_bloom(
                coordinates, layer_request.start_date, layer_request.end_date, 300
            )
            if algal_result["status"] == "success":
                current_analysis["algal_blooms"] = {
                    "classification": algal_result["classification_image"],
                    "statistics": algal_result["statistics"],
                    "roi": roi,
                    "area_km2": area_km2,
                    "analyzed": True
                }
                logger.info("Algal blooms analysis completed successfully")
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Algal blooms analysis failed: {algal_result.get('error', 'Data not available')}"
                )

        elif layer_type == "soil":
            soil_result = soil_api.analyze_soil_moisture(
                coordinates, layer_request.start_date, layer_request.end_date, 500
            )
            if soil_result["status"] == "success":
                current_analysis["soil"] = {
                    "classification": soil_result["classification_image"],
                    "statistics": soil_result["statistics"],
                    "roi": roi,
                    "area_km2": area_km2,
                    "analyzed": True
                }
                logger.info("Soil analysis completed successfully")
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Soil analysis failed: {soil_result.get('error', 'Data not available')}"
                )

        elif layer_type == "chlorophyll":
            chlorophyll_result = ocean_api.analyze_chlorophyll(
                coordinates, layer_request.start_date, layer_request.end_date, 4638
            )
            if chlorophyll_result["status"] == "success":
                current_analysis["chlorophyll"] = {
                    "classification": chlorophyll_result["classification_image"],
                    "statistics": chlorophyll_result["statistics"],
                    "roi": roi,
                    "area_km2": area_km2,
                    "analyzed": True
                }
                logger.info("Ocean chlorophyll analysis completed successfully")
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Chlorophyll analysis failed: {chlorophyll_result.get('error', 'Data not available')}"
                )

        return {
            "status": "success",
            "layer": layer_type,
            "message": f"{layer_type.title()} analysis completed successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Layer analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"{layer_type} analysis failed: {str(e)}")

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# MAP LAYER ENDPOINTS

@app.get("/api/forest/map-url")
async def get_forest_map_url():
    """Get map tile URL for forest classification"""
    global current_analysis
    
    if not current_analysis["forest"]["analyzed"] or not current_analysis["forest"]["classification"]:
        raise HTTPException(status_code=404, detail="Forest classification not available. Please run analysis first.")
    
    vis_params = {
        'min': 1, 'max': 3,
        'palette': ['#FFFF00', '#90EE90', '#006400'],
        'format': 'png'
    }
    
    try:
        map_id = current_analysis["forest"]["classification"].getMapId(vis_params)
        logger.info("Forest map tiles generated")
        return {
            "tile_url": map_id['tile_fetcher'].url_format,
            "map_id": map_id['mapid']
        }
    except Exception as e:
        logger.error(f"Forest map generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Forest map tile generation failed: {str(e)}")

@app.get("/api/wetland/map-url")
async def get_wetland_map_url():
    """Get map tile URL for wetland classification"""
    global current_analysis
    
    if not current_analysis["wetland"]["analyzed"] or not current_analysis["wetland"]["classified"]:
        raise HTTPException(status_code=404, detail="Wetland classification not available. Please run analysis first.")
    
    vis_params = {
        'min': 1, 'max': 5,
        'palette': ['#8B4513', '#FFFF00', '#00FF00', '#00FFFF', '#0000FF'],
        'format': 'png'
    }
    
    try:
        map_id = current_analysis["wetland"]["classified"].getMapId(vis_params)
        logger.info("Wetland map tiles generated")
        return {
            "tile_url": map_id['tile_fetcher'].url_format,
            "map_id": map_id['mapid']
        }
    except Exception as e:
        logger.error(f"Wetland map generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Wetland map tile generation failed: {str(e)}")

@app.get("/api/tundra/map-url")
async def get_tundra_map_url():
    """Get map tile URL for tundra classification"""
    global current_analysis
    
    if not current_analysis["tundra"]["analyzed"] or not current_analysis["tundra"]["classification"]:
        raise HTTPException(status_code=404, detail="Tundra classification not available. Please run analysis first.")
    
    vis_params = {
        'min': 0, 'max': 4,
        'palette': [
            '#ffffff',  # Class 0: No Tundra
            '#1f78b4',  # Class 1: Arctic Tundra
            '#a6cee3',  # Class 2: Alpine Tundra
            '#33a02c',  # Class 3: Wet Tundra
            '#ff7f00'   # Class 4: Shrub/Dry Tundra
        ],
        'format': 'png'
    }
    
    try:
        map_id = current_analysis["tundra"]["classification"].getMapId(vis_params)
        logger.info("Tundra map tiles generated")
        return {
            "tile_url": map_id['tile_fetcher'].url_format,
            "map_id": map_id['mapid']
        }
    except Exception as e:
        logger.error(f"Tundra map generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Tundra map tile generation failed: {str(e)}")

@app.get("/api/grassland/map-url")
async def get_grassland_map_url():
    """Get map tile URL for grassland classification"""
    global current_analysis
    
    if not current_analysis["grassland"]["analyzed"] or not current_analysis["grassland"]["classification"]:
        raise HTTPException(status_code=404, detail="Grassland classification not available. Please run analysis first.")
    
    vis_params = {
        'min': 0, 'max': 3,
        'palette': ['#8B4513', '#FFFF00', '#90EE90', '#006400'],
        'format': 'png'
    }
    
    try:
        map_id = current_analysis["grassland"]["classification"].getMapId(vis_params)
        logger.info("Grassland map tiles generated")
        return {
            "tile_url": map_id['tile_fetcher'].url_format,
            "map_id": map_id['mapid']
        }
    except Exception as e:
        logger.error(f"Grassland map generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Grassland map tile generation failed: {str(e)}")

@app.get("/api/algal_blooms/map-url")
async def get_algal_blooms_map_url():
    """Get map tile URL for algal blooms classification"""
    global current_analysis
    
    if not current_analysis["algal_blooms"]["analyzed"] or not current_analysis["algal_blooms"]["classification"]:
        raise HTTPException(status_code=404, detail="Algal blooms classification not available. Please run analysis first.")
    
    vis_params = {
        'min': 1, 'max': 4,
        'palette': ['#87CEEB', '#FFFF00', '#FFA500', '#FF0000'],
        'format': 'png'
    }
    
    try:
        map_id = current_analysis["algal_blooms"]["classification"].getMapId(vis_params)
        logger.info("Algal blooms map tiles generated")
        return {
            "tile_url": map_id['tile_fetcher'].url_format,
            "map_id": map_id['mapid']
        }
    except Exception as e:
        logger.error(f"Algal blooms map generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Algal blooms map tile generation failed: {str(e)}")

@app.get("/api/soil/map-url")
async def get_soil_map_url():
    """Get map tile URL for soil moisture classification"""
    global current_analysis
    
    if not current_analysis["soil"]["analyzed"] or not current_analysis["soil"]["classification"]:
        raise HTTPException(status_code=404, detail="Soil classification not available. Please run analysis first.")
    
    vis_params = {
        'min': 1, 'max': 3,
        'palette': ['#D2691E', '#DEB887', '#8B4513'],
        'format': 'png'
    }
    
    try:
        map_id = current_analysis["soil"]["classification"].getMapId(vis_params)
        logger.info("Soil map tiles generated")
        return {
            "tile_url": map_id['tile_fetcher'].url_format,
            "map_id": map_id['mapid']
        }
    except Exception as e:
        logger.error(f"Soil map generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Soil map tile generation failed: {str(e)}")

@app.get("/api/chlorophyll/map-url")
async def get_chlorophyll_map_url():
    """Get map tile URL for chlorophyll classification"""
    global current_analysis
    
    if not current_analysis["chlorophyll"]["analyzed"] or not current_analysis["chlorophyll"]["classification"]:
        raise HTTPException(status_code=404, detail="Chlorophyll classification not available. Please run analysis first.")
    
    vis_params = {
        'min': 0, 'max': 4,
        'palette': [
            '#081d58',  # Class 0: Oligotrophic
            '#225ea8',  # Class 1: Mesotrophic
            '#41b6c4',  # Class 2: Moderately Eutrophic
            '#a1dab4',  # Class 3: Eutrophic
            '#e31a1c'   # Class 4: Hypereutrophic
        ],
        'format': 'png'
    }
    
    try:
        map_id = current_analysis["chlorophyll"]["classification"].getMapId(vis_params)
        logger.info("Chlorophyll map tiles generated")
        return {
            "tile_url": map_id['tile_fetcher'].url_format,
            "map_id": map_id['mapid']
        }
    except Exception as e:
        logger.error(f"Chlorophyll map generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Chlorophyll map tile generation failed: {str(e)}")

# STATISTICS ENDPOINTS

@app.get("/api/forest/statistics")
async def get_forest_statistics():
    """Get forest analysis statistics"""
    global current_analysis
    
    if not current_analysis["forest"]["analyzed"] or not current_analysis["forest"]["statistics"]:
        raise HTTPException(status_code=404, detail="Forest statistics not available.")
    
    logger.info("Forest statistics provided")
    return current_analysis["forest"]["statistics"]

@app.get("/api/wetland/statistics")
async def get_wetland_statistics():
    """Get wetland analysis statistics"""
    global current_analysis
    
    if not current_analysis["wetland"]["analyzed"] or not current_analysis["wetland"]["statistics"]:
        raise HTTPException(status_code=404, detail="Wetland statistics not available.")
    
    logger.info("Wetland statistics provided")
    formatted_stats = wetland_api.format_statistics(current_analysis["wetland"]["statistics"])
    return formatted_stats

@app.get("/api/tundra/statistics")
async def get_tundra_statistics():
    """Get tundra analysis statistics"""
    global current_analysis
    
    if not current_analysis["tundra"]["analyzed"] or not current_analysis["tundra"]["statistics"]:
        raise HTTPException(status_code=404, detail="Tundra statistics not available.")
    
    logger.info("Tundra statistics provided")
    return current_analysis["tundra"]["statistics"]

@app.get("/api/grassland/statistics")
async def get_grassland_statistics():
    """Get grassland analysis statistics"""
    global current_analysis
    
    if not current_analysis["grassland"]["analyzed"] or not current_analysis["grassland"]["statistics"]:
        raise HTTPException(status_code=404, detail="Grassland statistics not available.")
    
    logger.info("Grassland statistics provided")
    formatted_stats = grassland_api.format_statistics(current_analysis["grassland"]["statistics"])
    return formatted_stats

@app.get("/api/algal_blooms/statistics")
async def get_algal_blooms_statistics():
    """Get algal blooms analysis statistics"""
    global current_analysis
    
    if not current_analysis["algal_blooms"]["analyzed"] or not current_analysis["algal_blooms"]["statistics"]:
        raise HTTPException(status_code=404, detail="Algal blooms statistics not available.")
    
    logger.info("Algal blooms statistics provided")
    return current_analysis["algal_blooms"]["statistics"]

@app.get("/api/soil/statistics")
async def get_soil_statistics():
    """Get soil moisture analysis statistics"""
    global current_analysis
    
    if not current_analysis["soil"]["analyzed"] or not current_analysis["soil"]["statistics"]:
        raise HTTPException(status_code=404, detail="Soil statistics not available.")
    
    logger.info("Soil statistics provided")
    return current_analysis["soil"]["statistics"]

@app.get("/api/chlorophyll/statistics")
async def get_chlorophyll_statistics():
    """Get chlorophyll analysis statistics"""
    global current_analysis
    
    if not current_analysis["chlorophyll"]["analyzed"] or not current_analysis["chlorophyll"]["statistics"]:
        raise HTTPException(status_code=404, detail="Chlorophyll statistics not available.")
    
    logger.info("Chlorophyll statistics provided")
    return current_analysis["chlorophyll"]["statistics"]

# LEGEND ENDPOINTS

@app.get("/api/legends/{analysis_type}")
async def get_legends(analysis_type: str):
    """Get legend information for the specified analysis type"""
    
    valid_types = ['forest', 'wetland', 'tundra', 'grassland', 'algal_blooms', 'soil', 'chlorophyll']
    if analysis_type not in valid_types:
        logger.warning(f"Invalid legend request for type '{analysis_type}'")
        raise HTTPException(status_code=400, detail=f"Invalid analysis type: {analysis_type}")
    
    if analysis_type in LEGEND_CONFIGS:
        logger.info(f"Legend provided for {analysis_type}")
        return LEGEND_CONFIGS[analysis_type]
    else:
        logger.error(f"Legend not found for {analysis_type}")
        raise HTTPException(status_code=404, detail=f"Legends for {analysis_type} not found")

# Reset analysis endpoint
@app.delete("/api/analysis/reset")
async def reset_analysis():
    """Reset all analysis data"""
    global current_analysis, current_roi
    
    try:
        # Reset all analysis states
        for layer in current_analysis:
            current_analysis[layer] = {
                "classification": None,
                "statistics": None,
                "roi": None,
                "area_km2": None,
                "analyzed": False
            }
        
        # Reset ROI
        current_roi = {
            "coordinates": None,
            "geometry": None,
            "area_km2": None
        }
        
        logger.info("Analysis data reset")
        return {
            "status": "success",
            "message": "All analysis data has been reset",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Analysis reset error: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset analysis data")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        app,
        host="localhost",
        port=port,
        reload=False
    )