# grassland_api.py - Fixed version with proper statistics formatting

import ee
from datetime import datetime
from typing import List, Union, Dict, Any

class GrasslandAPI:
    """
    Grassland Analysis API for vegetation classification and carbon estimation using Google Earth Engine.
    Uses rule-based classification based on NDVI thresholds to distinguish grassland and savanna.
    """

    def __init__(self):
        """Initialize Grassland API with classification thresholds"""
        self.grassland_threshold_min = 0.2   # NDVI >= 0.2
        self.grassland_threshold_max = 0.45  # NDVI < 0.45
        self.savanna_threshold_min = 0.45    # NDVI >= 0.45
        self.savanna_threshold_max = 0.7     # NDVI <= 0.7
        
        # Biomass estimates (Mg/ha)
        self.biomass_grassland = 5.0
        self.biomass_savanna = 12.0

    def _create_geometry(self, roi_coords: Union[List, dict]):
        """Create an Earth Engine geometry from coordinates."""
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
        """Validate and parse dates in 'YYYY-MM-DD' format."""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            if start > end:
                raise ValueError("start_date must be earlier than end_date")
            return start_date, end_date
        except Exception as e:
            raise ValueError(f"Invalid date format or logic: {str(e)}")

    def get_ndvi_image(self, roi, start_date: str, end_date: str) -> ee.Image:
        """
        Generates a robust NDVI image with multiple data source attempts.
        """
        print(f"🔄 Fetching Sentinel-2 data for grassland analysis...")
        
        # Try different cloud cover thresholds
        cloud_thresholds = [20, 40, 60, 80]
        
        for threshold in cloud_thresholds:
            try:
                print(f"  Trying cloud threshold: {threshold}%")
                collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
                    .filterBounds(roi) \
                    .filterDate(start_date, end_date) \
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', threshold))
                
                # Check if we have any images
                image_count = collection.size().getInfo()
                print(f"  Found {image_count} images with <{threshold}% cloud cover")
                
                if image_count > 0:
                    # Get median composite
                    s2_image = collection.median()
                    
                    # Calculate NDVI
                    ndvi = s2_image.normalizedDifference(['B8', 'B4']).rename('NDVI')
                    
                    # Clip to ROI
                    ndvi_clipped = ndvi.clip(roi)
                    
                    # Verify the image has valid data
                    ndvi_info = ndvi_clipped.reduceRegion(
                        reducer=ee.Reducer.count(),
                        geometry=roi,
                        scale=100,
                        maxPixels=1e6
                    ).get('NDVI').getInfo()
                    
                    if ndvi_info and ndvi_info > 0:
                        print(f"✅ Successfully created NDVI image with {ndvi_info} valid pixels")
                        return ndvi_clipped
                    else:
                        print(f"  ⚠️ NDVI image has no valid pixels, trying next threshold...")
                        continue
                        
            except Exception as e:
                print(f"  ❌ Error with {threshold}% threshold: {e}")
                continue
        
        # If all attempts failed, try Landsat as backup
        print("🔄 Sentinel-2 failed, trying Landsat 8...")
        try:
            landsat = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2') \
                .filterBounds(roi) \
                .filterDate(start_date, end_date) \
                .filter(ee.Filter.lt('CLOUD_COVER', 50))
            
            if landsat.size().getInfo() > 0:
                # Landsat surface reflectance NDVI
                def apply_scale_factors(image):
                    optical_bands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
                    return image.addBands(optical_bands, None, True)
                
                landsat_scaled = landsat.map(apply_scale_factors).median()
                ndvi_landsat = landsat_scaled.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
                ndvi_clipped = ndvi_landsat.clip(roi)
                
                print("✅ Using Landsat 8 NDVI as backup")
                return ndvi_clipped
                
        except Exception as e:
            print(f"❌ Landsat backup also failed: {e}")
        
        # No satellite data available - raise error
        raise Exception("No satellite data available for grassland analysis in the selected area and time period")

    def classify_vegetation(self, ndvi_image, roi) -> ee.Image:
        """
        Classifies vegetation based on NDVI thresholds.
        """
        try:
            print("🔄 Classifying vegetation based on NDVI thresholds...")
            
            # Ensure we have a valid NDVI image
            if ndvi_image is None:
                raise ValueError("NDVI image is None")
            
            # Create classification
            classified_image = ee.Image(0).rename('classification') \
                .where(ndvi_image.gte(self.grassland_threshold_min).And(ndvi_image.lt(self.grassland_threshold_max)), 1) \
                .where(ndvi_image.gte(self.savanna_threshold_min).And(ndvi_image.lte(self.savanna_threshold_max)), 2) \
                .where(ndvi_image.gt(self.savanna_threshold_max), 3)
            
            # Ensure proper clipping
            classified_clipped = classified_image.clip(roi)
            
            # Verify the classification has valid data
            class_info = classified_clipped.reduceRegion(
                reducer=ee.Reducer.count(),
                geometry=roi,
                scale=100,
                maxPixels=1e6
            ).get('classification').getInfo()
            
            if class_info and class_info > 0:
                print(f"✅ Classification completed with {class_info} valid pixels")
                return classified_clipped
            else:
                raise ValueError("Classification resulted in no valid pixels")
                
        except Exception as e:
            print(f"❌ Classification error: {e}")
            raise Exception(f"Vegetation classification failed: {str(e)}")

    def compute_area(self, image, roi, resolution: int = 10) -> ee.List:
        """
        Computes area for each vegetation class.
        """
        try:
            print(f"🔄 Computing areas at {resolution}m resolution...")
            
            pixel_area_ha = ee.Image.pixelArea().divide(10000)
            area_stats = pixel_area_ha.addBands(image).reduceRegion(
                reducer=ee.Reducer.sum().group(
                    groupField=1,
                    groupName='class',
                ),
                geometry=roi,
                scale=resolution,
                maxPixels=1e11,
                tileScale=2  # Add tiling for large areas
            )
            
            groups = area_stats.get('groups')
            if groups is None:
                raise ValueError("Area computation returned no groups")
                
            return groups
            
        except Exception as e:
            print(f"❌ Area computation error: {e}")
            raise Exception(f"Area computation failed: {str(e)}")

    def estimate_carbon(self, area_ha_grassland: float, area_ha_savanna: float) -> tuple:
        """Estimates total biomass, carbon stock, and CO2 equivalent from class areas."""
        total_biomass = (area_ha_grassland * self.biomass_grassland) + (area_ha_savanna * self.biomass_savanna)
        carbon_stock = total_biomass * 0.5
        co2_equivalent = carbon_stock * 3.67
        return total_biomass, carbon_stock, co2_equivalent

    def analyze_grassland(self, roi_coords: Union[List, dict], 
                         start_date: str = "2021-01-01", 
                         end_date: str = "2023-01-01", 
                         resolution: int = 10) -> Dict[str, Any]:
        """
        Main workflow function for grassland analysis.
        """
        try:
            print("🔄 Starting grassland analysis...")
            
            # Validate inputs
            start_date, end_date = self._validate_dates(start_date, end_date)
            roi = self._create_geometry(roi_coords)

            # Get NDVI image
            ndvi_img = self.get_ndvi_image(roi, start_date, end_date)
            
            if ndvi_img is None:
                raise ValueError("Failed to obtain NDVI image")

            # Calculate mean NDVI
            try:
                mean_ndvi_dict = ndvi_img.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=roi,
                    scale=50,
                    maxPixels=1e9
                )
                mean_ndvi = mean_ndvi_dict.get("NDVI").getInfo()
                if mean_ndvi is None:
                    raise ValueError("Failed to calculate mean NDVI")
                print(f"✅ Mean NDVI: {mean_ndvi:.3f}")
            except Exception as e:
                print(f"❌ Mean NDVI calculation failed: {e}")
                raise Exception(f"NDVI calculation failed: {str(e)}")

            # Classify vegetation
            classified_img = self.classify_vegetation(ndvi_img, roi)
            
            if classified_img is None:
                raise ValueError("Failed to create classification")

            # Compute areas
            area_results_list = ee.List(self.compute_area(classified_img, roi, resolution)).getInfo()
            
            if not area_results_list:
                raise ValueError("Area computation returned empty results")
            
            area_by_class = {item['class']: item['sum'] for item in area_results_list}
            non_vegetation_area = area_by_class.get(0, 0)
            grassland_area = area_by_class.get(1, 0)
            savanna_area = area_by_class.get(2, 0)
            dense_vegetation_area = area_by_class.get(3, 0)

            # Calculate total area
            try:
                total_area = roi.area().getInfo() / 10000  # Convert to hectares
                total_area_km2 = total_area / 100  # Convert to km²
            except Exception as e:
                print(f"ROI area calculation failed: {e}, estimating from class areas")
                total_area = sum(area_by_class.values())
                total_area_km2 = total_area / 100

            # Estimate biomass and carbon
            total_biomass, carbon_stock, co2eq = self.estimate_carbon(grassland_area, savanna_area)

            print("✅ Grassland analysis completed successfully")
            
            return {
                "status": "success",
                "classification_image": classified_img,
                "statistics": {
                    "roi_area_hectares": round(total_area, 2),
                    "roi_area_km2": round(total_area_km2, 2),
                    "mean_ndvi": round(mean_ndvi, 3),
                    "vegetation_classification": {
                        "non_vegetation_area_ha": round(non_vegetation_area, 2),
                        "grassland_area_ha": round(grassland_area, 2),
                        "savanna_area_ha": round(savanna_area, 2),
                        "dense_vegetation_area_ha": round(dense_vegetation_area, 2)
                    },
                    "carbon_estimation": {
                        "total_biomass_Mg": round(total_biomass, 2),
                        "total_carbon_stock_MgC": round(carbon_stock, 2),
                        "co2_equivalent_MgCO2e": round(co2eq, 2)
                    }
                }
            }

        except Exception as e:
            print(f"❌ Grassland analysis failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Grassland analysis failed - no satellite data available for the selected area and time period"
            }

    def format_statistics(self, raw_statistics: Dict[str, Any]) -> Dict[str, Any]:
        """Format stored statistics for frontend display without re-running analysis"""
        try:
            return {
                "grassland_analysis": raw_statistics,
                "methodology": {
                    "approach": "Rule-based NDVI classification",
                    "thresholds": {
                        "non_vegetation": f"NDVI < {self.grassland_threshold_min}",
                        "grassland": f"NDVI {self.grassland_threshold_min}-{self.grassland_threshold_max}",
                        "savanna": f"NDVI {self.savanna_threshold_min}-{self.savanna_threshold_max}",
                        "dense_vegetation": f"NDVI > {self.savanna_threshold_max}"
                    },
                    "biomass_estimates": {
                        "grassland": f"{self.biomass_grassland} Mg/ha",
                        "savanna": f"{self.biomass_savanna} Mg/ha"
                    },
                    "data_source": "Sentinel-2 SR Harmonized (with Landsat backup)",
                    "spatial_resolution": "User-selected resolution"
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to format grassland statistics"
            }

    def create_grassland_classification_image(self, roi_coords: Union[List, dict], 
                                            start_date: str, end_date: str, resolution: int = 10) -> ee.Image:
        """Create a grassland classification image for visualization."""
        try:
            result = self.analyze_grassland(roi_coords, start_date, end_date, resolution)
            
            if result["status"] == "success" and result.get("classification_image") is not None:
                return result["classification_image"].rename('grassland_class')
            else:
                raise Exception(result.get("error", "Classification failed"))
                
        except Exception as e:
            print(f"❌ Classification image creation failed: {e}")
            raise Exception(f"Grassland classification failed: {str(e)}")

    def get_grassland_statistics(self, roi_coords: Union[List, dict], 
                               start_date: str, end_date: str, resolution: int = 10) -> Dict[str, Any]:
        """Get detailed grassland statistics by running full analysis."""
        try:
            result = self.analyze_grassland(roi_coords, start_date, end_date, resolution)
            
            if result["status"] == "error":
                return result
            
            return self.format_statistics(result["statistics"])
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Grassland statistics calculation failed"
            }