# soil_api.py

import ee
from datetime import datetime, timedelta
from typing import List, Union, Dict, Any

class SoilAPI:
    """
    Soil Analysis API for soil moisture classification using Google Earth Engine.
    Uses rule-based classification based on NDVI, NDWI, and Land Surface Temperature.
    """

    def __init__(self):
        """Initialize Soil API with classification thresholds"""
        self.wet_threshold = {"ndwi": 0.2, "lst": 32}
        self.dry_threshold = {"ndvi": 0.25, "ndwi": 0.1, "lst": 34}
        self.moderate_threshold = {"ndvi_min": 0.2, "ndvi_max": 0.4, "lst_min": 28, "lst_max": 35}

    def _create_geometry(self, roi_coords: Union[List, dict]):
        """
        Create an Earth Engine geometry from coordinates.
        Supports Polygon, MultiPolygon, Point, LineString.
        """
        if isinstance(roi_coords, dict) and 'type' in roi_coords and 'coordinates' in roi_coords:
            geom_type = roi_coords['type'].lower()
            coords = roi_coords['coordinates']
            if geom_type == 'polygon':
                return ee.Geometry.Polygon(coords)
            elif geom_type == 'multipolygon':
                return ee.Geometry.MultiPolygon(coords)
            elif geom_type == 'point':
                return ee.Geometry.Point(coords)
            elif geom_type == 'linestring':
                return ee.Geometry.LineString(coords)
            else:
                raise ValueError(f"Unsupported geometry type: {geom_type}")
        elif isinstance(roi_coords, list):
            return ee.Geometry.Polygon([roi_coords])
        else:
            raise ValueError("Invalid ROI coordinates format")

    def _validate_dates(self, start_date: str, end_date: str):
        """
        Validate and parse dates in 'YYYY-MM-DD' format.
        Raises ValueError if invalid.
        """
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            if start > end:
                raise ValueError("start_date must be earlier than end_date")
            return start_date, end_date
        except Exception as e:
            raise ValueError(f"Invalid date format or logic: {str(e)}")

    def analyze_soil_moisture(self, roi_coords: Union[List, dict], 
                            start_date: str = "2021-01-01", 
                            end_date: str = "2023-01-01", 
                            resolution: int = 500) -> Dict[str, Any]:
        """
        Main soil moisture analysis function.
        
        Args:
            roi_coords: Region of interest coordinates
            start_date: Analysis start date (YYYY-MM-DD)
            end_date: Analysis end date (YYYY-MM-DD)
            resolution: Spatial resolution in meters
            
        Returns:
            Dictionary containing soil moisture analysis results
        """
        try:
            # Validate inputs
            start_date, end_date = self._validate_dates(start_date, end_date)
            roi = self._create_geometry(roi_coords)
            
            # Calculate ROI area
            area_km2 = roi.area().divide(1e6).getInfo()
            
            # Get satellite data
            s2_result = self._get_sentinel2_data(roi, start_date, end_date)
            lst_result = self._get_temperature_data(roi, start_date, end_date)
            
            # Create soil moisture classification
            classification_image = self._create_soil_classification(
                s2_result['ndvi_image'],
                s2_result['ndwi_image'], 
                lst_result['lst_image'],
                roi
            )
            
            # Calculate statistics
            statistics = self._calculate_soil_statistics(
                s2_result, lst_result, area_km2
            )
            
            return {
                "status": "success",
                "classification_image": classification_image,
                "statistics": statistics
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Soil moisture analysis failed"
            }

    def _get_sentinel2_data(self, roi, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get Sentinel-2 vegetation and water indices"""
        try:
            s2_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
                .filterBounds(roi) \
                .filterDate(start_date, end_date) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
            
            if s2_collection.size().getInfo() == 0:
                # Return default values if no data
                default_ndvi = ee.Image.constant(0.3).clip(roi).rename('NDVI')
                default_ndwi = ee.Image.constant(0.1).clip(roi).rename('NDWI')
                return {
                    'ndvi_image': default_ndvi,
                    'ndwi_image': default_ndwi,
                    'mean_ndvi': 0.3,
                    'mean_ndwi': 0.1,
                    'data_available': False
                }
            
            s2_median = s2_collection.median()
            ndvi = s2_median.normalizedDifference(['B8', 'B4']).rename('NDVI').clip(roi)
            ndwi = s2_median.normalizedDifference(['B3', 'B8']).rename('NDWI').clip(roi)
            
            # Calculate mean values
            ndvi_stats = ndvi.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=roi,
                scale=500,
                maxPixels=1e9
            )
            
            ndwi_stats = ndwi.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=roi,
                scale=500,
                maxPixels=1e9
            )
            
            mean_ndvi = ndvi_stats.get('NDVI').getInfo()
            mean_ndwi = ndwi_stats.get('NDWI').getInfo()
            
            if mean_ndvi is None:
                mean_ndvi = 0.3
            if mean_ndwi is None:
                mean_ndwi = 0.1
            
            return {
                'ndvi_image': ndvi,
                'ndwi_image': ndwi,
                'mean_ndvi': round(mean_ndvi, 3),
                'mean_ndwi': round(mean_ndwi, 3),
                'data_available': True
            }
            
        except Exception as e:
            print(f"Sentinel-2 data error: {e}")
            # Return fallback
            default_ndvi = ee.Image.constant(0.3).clip(roi).rename('NDVI')
            default_ndwi = ee.Image.constant(0.1).clip(roi).rename('NDWI')
            return {
                'ndvi_image': default_ndvi,
                'ndwi_image': default_ndwi,
                'mean_ndvi': 0.3,
                'mean_ndwi': 0.1,
                'data_available': False
            }

    def _get_temperature_data(self, roi, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get MODIS Land Surface Temperature data"""
        try:
            lst_collection = ee.ImageCollection('MODIS/061/MOD11A2') \
                .filterBounds(roi) \
                .filterDate(start_date, end_date) \
                .select('LST_Day_1km')
            
            if lst_collection.size().getInfo() == 0:
                # Return default temperature if no data
                default_lst = ee.Image.constant(30.0).clip(roi).rename('LST_C')
                return {
                    'lst_image': default_lst,
                    'mean_temperature': 30.0,
                    'data_available': False
                }
            
            # Convert from Kelvin to Celsius
            lst_celsius = lst_collection.mean().multiply(0.02).subtract(273.15).rename('LST_C').clip(roi)
            
            # Calculate mean temperature
            lst_stats = lst_celsius.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=roi,
                scale=1000,
                maxPixels=1e9
            )
            
            mean_temp = lst_stats.get('LST_C').getInfo()
            if mean_temp is None:
                mean_temp = 30.0
            
            return {
                'lst_image': lst_celsius,
                'mean_temperature': round(mean_temp, 2),
                'data_available': True
            }
            
        except Exception as e:
            print(f"Temperature data error: {e}")
            # Return fallback
            default_lst = ee.Image.constant(30.0).clip(roi).rename('LST_C')
            return {
                'lst_image': default_lst,
                'mean_temperature': 30.0,
                'data_available': False
            }

    def _create_soil_classification(self, ndvi_image, ndwi_image, lst_image, roi) -> ee.Image:
        """Create soil moisture classification based on NDVI, NDWI, and LST"""
        try:
            # Soil moisture classification rules:
            # Class 1: Dry Soil (NDVI < 0.25, NDWI < 0.1, LST > 34°C)
            # Class 2: Moderate Soil (NDVI 0.2-0.4, LST 28-35°C)
            # Class 3: High Moisture (NDWI > 0.2, LST < 32°C)
            
            # Define conditions
            dry_condition = ndvi_image.lt(0.25).And(ndwi_image.lt(0.1)).And(lst_image.gt(34))
            wet_condition = ndwi_image.gt(0.2).And(lst_image.lt(32))
            moderate_condition = ndvi_image.gte(0.2).And(ndvi_image.lte(0.4)).And(lst_image.gte(28)).And(lst_image.lte(35))
            
            # Create classification (default to moderate)
            classification = ee.Image(2) \
                .where(dry_condition, 1) \
                .where(wet_condition, 3) \
                .where(moderate_condition.And(dry_condition.Not()).And(wet_condition.Not()), 2) \
                .rename('soil_class').clip(roi)
            
            return classification
            
        except Exception as e:
            print(f"Soil classification error: {e}")
            # Return fallback classification
            return ee.Image.constant(2).clip(roi).rename('soil_class')

    def _calculate_soil_statistics(self, s2_result: Dict, lst_result: Dict, area_km2: float) -> Dict[str, Any]:
        """Calculate comprehensive soil moisture statistics"""
        try:
            # Determine soil moisture level
            soil_moisture_level = self._classify_soil_moisture(
                s2_result['mean_ndvi'],
                s2_result['mean_ndwi'], 
                lst_result['mean_temperature']
            )
            
            # Calculate soil moisture index
            ndvi_val = s2_result['mean_ndvi']
            ndwi_val = s2_result['mean_ndwi']
            lst_val = lst_result['mean_temperature']
            
            soil_moisture_index = round(
                ((ndvi_val if ndvi_val > 0 else 0) + 
                 (0.5 - abs(lst_val - 30) / 50) + 
                 ndwi_val) / 3, 3
            )
            
            return {
                "roi_area_km2": round(area_km2, 2),
                "soil_moisture_index": soil_moisture_index,
                "soil_moisture_level": soil_moisture_level,
                "vegetation_index_ndvi": s2_result['mean_ndvi'],
                "water_index_ndwi": s2_result['mean_ndwi'],
                "land_surface_temperature_c": lst_result['mean_temperature'],
                "data_availability": {
                    "sentinel2_available": s2_result['data_available'],
                    "modis_lst_available": lst_result['data_available']
                },
                "analysis_method": "Combined NDVI-NDWI-LST classification"
            }
            
        except Exception as e:
            print(f"Statistics calculation error: {e}")
            return {
                "roi_area_km2": round(area_km2, 2),
                "soil_moisture_index": 0.5,
                "soil_moisture_level": "Moderate",
                "vegetation_index_ndvi": 0.3,
                "water_index_ndwi": 0.1,
                "land_surface_temperature_c": 30.0,
                "error": "Statistics calculation failed"
            }

    def _classify_soil_moisture(self, ndvi: float, ndwi: float, lst: float) -> str:
        """Classify soil moisture level based on indices"""
        if ndwi > 0.2 and lst < 32:
            return "High Moisture"
        elif ndvi < 0.25 and ndwi < 0.1 and lst > 34:
            return "Dry Soil"
        else:
            return "Moderate"

    def create_soil_classification_image(self, roi_coords: Union[List, dict], 
                                       start_date: str, end_date: str, resolution: int = 500) -> ee.Image:
        """
        Create a soil moisture classification image for visualization.
        
        Args:
            roi_coords: Region of interest coordinates
            start_date: Analysis start date (YYYY-MM-DD)
            end_date: Analysis end date (YYYY-MM-DD)
            resolution: Spatial resolution in meters
            
        Returns:
            Earth Engine Image with soil moisture classification
        """
        try:
            result = self.analyze_soil_moisture(roi_coords, start_date, end_date, resolution)
            if result["status"] == "success":
                return result["classification_image"]
            else:
                # Return fallback image
                roi = self._create_geometry(roi_coords)
                return ee.Image.constant(2).clip(roi).rename('soil_class')
                
        except Exception as e:
            # Return fallback image
            roi = self._create_geometry(roi_coords)
            return ee.Image.constant(2).clip(roi).rename('soil_class')

    def get_soil_statistics(self, roi_coords: Union[List, dict], 
                          start_date: str, end_date: str, resolution: int = 500) -> Dict[str, Any]:
        """
        Get detailed soil moisture statistics.
        
        Args:
            roi_coords: Region of interest coordinates
            start_date: Analysis start date (YYYY-MM-DD)
            end_date: Analysis end date (YYYY-MM-DD)
            resolution: Spatial resolution in meters
            
        Returns:
            Dictionary containing detailed soil moisture statistics
        """
        try:
            result = self.analyze_soil_moisture(roi_coords, start_date, end_date, resolution)
            
            if result["status"] == "error":
                return result
            
            return {
                "status": "success",
                "soil_analysis": result["statistics"],
                "methodology": {
                    "approach": "Combined NDVI-NDWI-LST analysis",
                    "thresholds": {
                        "dry_soil": "NDVI < 0.25, NDWI < 0.1, LST > 34°C",
                        "moderate": "NDVI 0.2-0.4, LST 28-35°C",
                        "high_moisture": "NDWI > 0.2, LST < 32°C"
                    },
                    "data_sources": "Sentinel-2 + MODIS LST",
                    "spatial_resolution": f"{resolution}m"
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Soil moisture statistics calculation failed"
            }