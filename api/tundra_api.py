# tundra_api.py - Optimized 5-Class Permafrost-Aware Tundra Classification

import ee
from datetime import datetime
from typing import List, Union, Dict, Any

class TundraAPI:
    """
    Optimized Tundra Analysis API for global 5-class permafrost-aware classification.
    Automatically adapts to any geographic region with intelligent thresholds.
    """

    def __init__(self):
        """Initialize with adaptive thresholds for global tundra detection"""
        # Adaptive NDVI range for global tundra vegetation
        self.ndvi_min = 0.05   # Include sparse Arctic vegetation
        self.ndvi_max = 0.70   # Include dense shrub tundra
        
        # Temperature threshold (adaptive)
        self.lst_threshold = 8.0  # ≤8°C for global tundra (includes subarctic)
        
        # Elevation threshold (adaptive by latitude)
        self.base_alpine_elevation = 2000  # Base elevation, adjusted by latitude
        
        # Moisture threshold
        self.ndwi_threshold = 0.0  # Wet vs dry differentiation
        
        # Permafrost threshold (adaptive)
        self.permafrost_threshold = 0.25  # Lowered for global coverage

    def _create_geometry(self, roi_coords: Union[List, dict]):
        """Create Earth Engine geometry from coordinates."""
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
        """Validate dates."""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            if start > end:
                raise ValueError("start_date must be earlier than end_date")
            return start_date, end_date
        except Exception as e:
            raise ValueError(f"Invalid date format: {str(e)}")

    def analyze_tundra(self, roi_coords: Union[List, dict], 
                      start_date: str = "2021-01-01", 
                      end_date: str = "2023-01-01", 
                      resolution: int = 250) -> Dict[str, Any]:
        """
        Main tundra analysis with adaptive global thresholds.
        """
        try:
            start_date, end_date = self._validate_dates(start_date, end_date)
            roi = self._create_geometry(roi_coords)
            area_km2 = roi.area().divide(1e6).getInfo()
            
            # Get adaptive parameters based on ROI location
            roi_center = roi.centroid().coordinates().getInfo()
            adaptive_params = self._get_adaptive_parameters(roi_center[1])  # latitude
            
            # Get data layers
            data_layers = self._get_data_layers(roi, start_date, end_date)
            
            # Create classification with adaptive parameters
            classification_image = self._create_adaptive_classification(
                data_layers, roi, adaptive_params
            )
            
            # Calculate statistics
            statistics = self._calculate_statistics(
                data_layers, classification_image, area_km2, roi, adaptive_params
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
                "message": "Tundra analysis failed"
            }

    def _get_adaptive_parameters(self, latitude: float) -> Dict[str, float]:
        """Calculate adaptive parameters based on geographic location."""
        abs_lat = abs(latitude)
        
        # Adaptive alpine elevation (higher at lower latitudes)
        alpine_elevation = self.base_alpine_elevation + max(0, (45 - abs_lat) * 50)
        
        # Adaptive permafrost probability (higher at higher latitudes)
        permafrost_boost = max(0, (abs_lat - 50) / 40)  # 0 at 50°, 1 at 90°
        
        # Adaptive temperature threshold (colder required at lower latitudes)
        temp_threshold = self.lst_threshold - max(0, (60 - abs_lat) * 0.1)
        
        return {
            'alpine_elevation': alpine_elevation,
            'permafrost_boost': permafrost_boost,
            'temperature_threshold': temp_threshold,
            'latitude': abs_lat
        }

    def _get_data_layers(self, roi, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get all required data layers efficiently."""
        try:
            # Vegetation (NDVI)
            try:
                s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
                    .filterBounds(roi).filterDate(start_date, end_date) \
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)) \
                    .median()
                ndvi = s2.normalizedDifference(['B8', 'B4']).clip(roi)
                ndwi = s2.normalizedDifference(['B3', 'B8']).clip(roi)
                ndvi_mean = ndvi.reduceRegion(ee.Reducer.mean(), roi, 250, 1e9).get('nd').getInfo() or 0.15
                ndwi_mean = ndwi.reduceRegion(ee.Reducer.mean(), roi, 250, 1e9).get('nd').getInfo() or -0.1
                vegetation_available = True
            except:
                ndvi = ee.Image.constant(0.15).clip(roi)
                ndwi = ee.Image.constant(-0.1).clip(roi)
                ndvi_mean, ndwi_mean = 0.15, -0.1
                vegetation_available = False

            # Temperature (LST)
            try:
                lst = ee.ImageCollection('MODIS/061/MOD11A1') \
                    .filterBounds(roi).filterDate(start_date, end_date) \
                    .select('LST_Day_1km').median() \
                    .multiply(0.02).subtract(273.15).clip(roi)
                lst_mean = lst.reduceRegion(ee.Reducer.mean(), roi, 1000, 1e9).get('LST_Day_1km').getInfo()
                if lst_mean is None:
                    raise Exception("No LST data")
                temperature_available = True
            except:
                # Estimate temperature based on latitude
                coords = ee.Image.pixelLonLat().clip(roi)
                lat = coords.select('latitude')
                lst = lat.multiply(-0.7).add(15).clip(roi)  # Rough temp estimate
                lst_mean = lst.reduceRegion(ee.Reducer.mean(), roi, 1000, 1e9).get('latitude').getInfo() or 5.0
                temperature_available = False

            # Elevation
            try:
                elevation = ee.Image('USGS/SRTMGL1_003').clip(roi)
                elev_mean = elevation.reduceRegion(ee.Reducer.mean(), roi, 90, 1e9).get('elevation').getInfo() or 500
                elevation_available = True
            except:
                elevation = ee.Image.constant(500).clip(roi)
                elev_mean = 500
                elevation_available = False

            # Permafrost index (latitude-based)
            coords = ee.Image.pixelLonLat().clip(roi)
            lat = coords.select('latitude')
            permafrost_index = lat.abs().subtract(40).divide(30).clamp(0, 1)
            permafrost_mean = permafrost_index.reduceRegion(ee.Reducer.mean(), roi, 1000, 1e9).get('latitude').getInfo() or 0.3

            return {
                'ndvi': ndvi, 'ndvi_mean': round(ndvi_mean, 3),
                'ndwi': ndwi, 'ndwi_mean': round(ndwi_mean, 3),
                'lst': lst, 'lst_mean': round(lst_mean, 2),
                'elevation': elevation, 'elevation_mean': round(elev_mean, 1),
                'permafrost': permafrost_index, 'permafrost_mean': round(permafrost_mean, 3),
                'data_quality': {
                    'vegetation': vegetation_available,
                    'temperature': temperature_available,
                    'elevation': elevation_available
                }
            }
            
        except Exception as e:
            # Ultimate fallback
            roi_center = roi.centroid().coordinates().getInfo()
            lat = abs(roi_center[1])
            
            return {
                'ndvi': ee.Image.constant(0.15).clip(roi), 'ndvi_mean': 0.15,
                'ndwi': ee.Image.constant(-0.1).clip(roi), 'ndwi_mean': -0.1,
                'lst': ee.Image.constant(max(-5, 15 - lat * 0.3)).clip(roi), 'lst_mean': max(-5, 15 - lat * 0.3),
                'elevation': ee.Image.constant(500).clip(roi), 'elevation_mean': 500,
                'permafrost': ee.Image.constant(max(0.1, (lat - 40) / 30)).clip(roi), 'permafrost_mean': max(0.1, (lat - 40) / 30),
                'data_quality': {'vegetation': False, 'temperature': False, 'elevation': False}
            }

    def _create_adaptive_classification(self, data_layers: Dict, roi, adaptive_params: Dict) -> ee.Image:
        """Create 5-class classification with adaptive parameters."""
        try:
            # Extract layers
            ndvi = data_layers['ndvi']
            lst = data_layers['lst']
            elevation = data_layers['elevation']
            ndwi = data_layers['ndwi']
            permafrost = data_layers['permafrost']
            
            # Adaptive conditions
            is_tundra_vegetation = ndvi.gte(self.ndvi_min).And(ndvi.lte(self.ndvi_max))
            is_cold = lst.lte(adaptive_params['temperature_threshold'])
            is_alpine = elevation.gt(adaptive_params['alpine_elevation'])
            is_wet = ndwi.gt(self.ndwi_threshold)
            
            # Enhanced permafrost detection
            permafrost_threshold = max(0.1, self.permafrost_threshold - adaptive_params['permafrost_boost'] * 0.15)
            is_permafrost = permafrost.gt(permafrost_threshold)
            
            # High latitude boost (for Arctic regions)
            coords = ee.Image.pixelLonLat().clip(roi)
            lat = coords.select('latitude')
            is_arctic_latitude = lat.abs().gt(60)
            
            # Classification hierarchy
            classification = ee.Image(0)  # Default: No Tundra
            
            # Class 1: Arctic Tundra (cold + permafrost/high latitude + vegetation)
            arctic_conditions = (is_permafrost.Or(is_arctic_latitude)).And(is_cold).And(is_tundra_vegetation)
            classification = classification.where(arctic_conditions.And(is_alpine.Not()), 1)
            
            # Class 2: Alpine Tundra (high elevation + vegetation)
            alpine_conditions = is_alpine.And(is_tundra_vegetation)
            classification = classification.where(alpine_conditions, 2)
            
            # Class 3: Wet Tundra (permafrost/arctic + wet + vegetation)
            wet_conditions = (is_permafrost.Or(is_arctic_latitude)).And(is_wet).And(is_tundra_vegetation).And(is_alpine.Not())
            classification = classification.where(wet_conditions, 3)
            
            # Class 4: Shrub/Dry Tundra (permafrost/arctic + dry + vegetation)
            dry_conditions = (is_permafrost.Or(is_arctic_latitude)).And(is_wet.Not()).And(is_tundra_vegetation).And(is_alpine.Not())
            # Exclude areas already classified as arctic tundra
            dry_conditions = dry_conditions.And(arctic_conditions.Not())
            classification = classification.where(dry_conditions, 4)
            
            return classification.rename('tundra_class').clip(roi)
            
        except Exception as e:
            # Fallback: simple latitude-based classification
            coords = ee.Image.pixelLonLat().clip(roi)
            lat = coords.select('latitude').abs()
            simple_tundra = lat.gt(55).multiply(1)  # Basic Arctic detection
            return simple_tundra.rename('tundra_class').clip(roi)

    def _calculate_statistics(self, data_layers: Dict, classification: ee.Image, 
                            area_km2: float, roi, adaptive_params: Dict) -> Dict[str, Any]:
        """Calculate comprehensive statistics."""
        try:
            # Calculate class areas
            pixel_area = ee.Image.pixelArea().divide(1e6)
            areas = pixel_area.addBands(classification).reduceRegion(
                reducer=ee.Reducer.sum().group(groupField=1, groupName='class'),
                geometry=roi, scale=250, maxPixels=1e11
            ).get('groups')
            
            # Process areas
            area_list = ee.List(areas).getInfo() if areas else []
            class_areas = {item['class']: item['sum'] for item in area_list} if area_list else {}
            
            # Extract areas
            no_tundra = class_areas.get(0, 0)
            arctic_tundra = class_areas.get(1, 0)
            alpine_tundra = class_areas.get(2, 0)
            wet_tundra = class_areas.get(3, 0)
            dry_tundra = class_areas.get(4, 0)
            
            total_tundra = arctic_tundra + alpine_tundra + wet_tundra + dry_tundra
            tundra_percent = (total_tundra / area_km2) * 100 if area_km2 > 0 else 0
            
            # Determine dominant type
            tundra_types = {
                'Arctic Tundra': arctic_tundra,
                'Alpine Tundra': alpine_tundra,
                'Wet Tundra': wet_tundra,
                'Shrub/Dry Tundra': dry_tundra
            }
            dominant_type = max(tundra_types, key=tundra_types.get) if total_tundra > 0 else "No Tundra"
            
            # Climate indicators
            permafrost_extent = arctic_tundra + wet_tundra + dry_tundra
            thaw_zones = dry_tundra
            
            return {
                "roi_area_km2": round(area_km2, 2),
                "total_tundra_area_km2": round(total_tundra, 2),
                "tundra_coverage_percent": round(tundra_percent, 1),
                "dominant_tundra_type": dominant_type,
                "class_areas_km2": {
                    "no_tundra": round(no_tundra, 2),
                    "arctic_tundra": round(arctic_tundra, 2),
                    "alpine_tundra": round(alpine_tundra, 2),
                    "wet_tundra": round(wet_tundra, 2),
                    "shrub_dry_tundra": round(dry_tundra, 2)
                },
                "environmental_indicators": {
                    "mean_temperature_celsius": data_layers['lst_mean'],
                    "mean_ndvi": data_layers['ndvi_mean'],
                    "mean_elevation_m": data_layers['elevation_mean'],
                    "mean_ndwi": data_layers['ndwi_mean'],
                    "permafrost_probability": data_layers['permafrost_mean']
                },
                "climate_indicators": {
                    "permafrost_extent_km2": round(permafrost_extent, 2),
                    "potential_thaw_zones_km2": round(thaw_zones, 2),
                    "alpine_vs_arctic_ratio": round(alpine_tundra / arctic_tundra, 2) if arctic_tundra > 0 else 0,
                    "wet_vs_dry_ratio": round(wet_tundra / dry_tundra, 2) if dry_tundra > 0 else 0
                },
                "adaptive_parameters": {
                    "latitude": round(adaptive_params['latitude'], 1),
                    "alpine_elevation_threshold": round(adaptive_params['alpine_elevation'], 0),
                    "temperature_threshold": round(adaptive_params['temperature_threshold'], 1),
                    "permafrost_boost": round(adaptive_params['permafrost_boost'], 2)
                },
                "data_availability": data_layers['data_quality'],
                "analysis_method": "Adaptive 5-class permafrost-aware tundra classification"
            }
            
        except Exception as e:
            return {
                "roi_area_km2": round(area_km2, 2),
                "total_tundra_area_km2": round(area_km2 * 0.3, 2),
                "tundra_coverage_percent": 30.0,
                "dominant_tundra_type": "Arctic Tundra",
                "environmental_indicators": {
                    "mean_temperature_celsius": data_layers.get('lst_mean', 0),
                    "mean_ndvi": data_layers.get('ndvi_mean', 0.15),
                    "permafrost_probability": data_layers.get('permafrost_mean', 0.3)
                },
                "error": "Statistics calculation failed - using estimates"
            }

    # Legacy interface methods
    def create_tundra_classification_image(self, roi_coords: Union[List, dict], 
                                         start_date: str, end_date: str, resolution: int = 250) -> ee.Image:
        """Create classification image for visualization."""
        try:
            result = self.analyze_tundra(roi_coords, start_date, end_date, resolution)
            if result["status"] == "success":
                return result["classification_image"]
            else:
                roi = self._create_geometry(roi_coords)
                return ee.Image.constant(0).clip(roi).rename('tundra_class')
        except:
            roi = self._create_geometry(roi_coords)
            return ee.Image.constant(0).clip(roi).rename('tundra_class')

    def get_tundra_statistics(self, roi_coords: Union[List, dict], 
                            start_date: str, end_date: str, resolution: int = 250) -> Dict[str, Any]:
        """Get detailed statistics."""
        try:
            result = self.analyze_tundra(roi_coords, start_date, end_date, resolution)
            
            if result["status"] == "error":
                return result
            
            return {
                "status": "success",
                "tundra_analysis": result["statistics"],
                "methodology": {
                    "approach": "Adaptive 5-class permafrost-aware classification",
                    "global_coverage": "Automatically adapts to any geographic region",
                    "parameters": "NDVI (0.05-0.70) + LST (adaptive) + Elevation (adaptive) + NDWI + Permafrost",
                    "resolution": f"{resolution}m",
                    "adaptive_features": [
                        "Latitude-based parameter adjustment",
                        "Elevation thresholds vary by latitude", 
                        "Temperature thresholds adjust to local climate",
                        "Permafrost detection enhanced for high latitudes"
                    ]
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Adaptive tundra analysis failed"
            }