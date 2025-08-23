import ee
from datetime import datetime
from typing import List, Union, Dict, Any

class ForestAPI:
    """
    Simplified Forest Analysis API - No Fallbacks, Real Satellite Data Only
    """

    def __init__(self):
        """Initialize Forest API with classification thresholds"""
        self.dense_forest_threshold = 0.6    # NDVI > 0.6
        self.moderate_forest_threshold = 0.3  # NDVI 0.3-0.6
        
        # Satellite data sources in priority order
        self.satellite_sources = [
            {
                'name': 'Sentinel-2 SR Harmonized',
                'collection': 'COPERNICUS/S2_SR_HARMONIZED',
                'bands': ['B2', 'B3', 'B4', 'B8', 'B11'],
                'cloud_threshold': [10, 20, 30, 50]
            },
            {
                'name': 'Landsat 8 Surface Reflectance',
                'collection': 'LANDSAT/LC08/C02/T1_L2',
                'bands': ['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6'],
                'cloud_threshold': [20, 30, 50]
            }
        ]

    def _create_geometry(self, roi_coords: Union[List, dict]):
        """Create Earth Engine geometry from coordinates."""
        if isinstance(roi_coords, list):
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

    def _get_satellite_data(self, roi, start_date: str, end_date: str):
        """Get satellite data with multiple source fallback - NO SYNTHETIC DATA"""
        
        for source in self.satellite_sources:
            print(f"🔍 Trying {source['name']}...")
            
            try:
                # Try different cloud thresholds
                for cloud_threshold in source['cloud_threshold']:
                    print(f"  - Cloud threshold: {cloud_threshold}%")
                    
                    if source['name'] == 'Sentinel-2 SR Harmonized':
                        collection = ee.ImageCollection(source['collection']) \
                            .filterBounds(roi) \
                            .filterDate(start_date, end_date) \
                            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_threshold)) \
                            .select(source['bands'])
                    else:  # Landsat
                        collection = ee.ImageCollection(source['collection']) \
                            .filterBounds(roi) \
                            .filterDate(start_date, end_date) \
                            .filter(ee.Filter.lt('CLOUD_COVER', cloud_threshold)) \
                            .select(source['bands'])
                    
                    # Check if we have data
                    image_count = collection.size().getInfo()
                    print(f"    Found {image_count} images")
                    
                    if image_count > 0:
                        # Process the imagery
                        if source['name'] == 'Sentinel-2 SR Harmonized':
                            image = self._process_sentinel2(collection, roi)
                        else:  # Landsat
                            image = self._process_landsat(collection, roi)
                        
                        # Verify we have valid data
                        if self._validate_image_data(image, roi):
                            print(f"✅ Successfully obtained data from {source['name']}")
                            return {
                                'image': image,
                                'source': source['name'],
                                'image_count': image_count
                            }
                        else:
                            print(f"    No valid data after processing")
                            continue
                
                print(f"No usable data from {source['name']}")
                
            except Exception as e:
                print(f"Error with {source['name']}: {e}")
                continue
        
        # If all satellite sources fail, raise error - NO FALLBACKS
        raise Exception("No satellite data available for the selected area and time period. Please try different dates or check if the area has forest coverage.")

    def _process_sentinel2(self, collection, roi):
        """Process Sentinel-2 data"""
        def mask_clouds(image):
            qa = image.select('QA60')
            cloud_bit_mask = 1 << 10
            cirrus_bit_mask = 1 << 11
            mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
            return image.updateMask(mask).divide(10000)
        
        # Apply cloud masking and get median
        image = collection.map(mask_clouds).median().clip(roi)
        
        # Calculate NDVI and NBR
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        nbr = image.normalizedDifference(['B8', 'B11']).rename('NBR')
        
        return image.addBands([ndvi, nbr])

    def _process_landsat(self, collection, roi):
        """Process Landsat data"""
        def apply_scale_factors(image):
            optical_bands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
            return image.addBands(optical_bands, None, True)
        
        # Apply scaling and get median
        image = collection.map(apply_scale_factors).median().clip(roi)
        
        # Calculate NDVI and NBR (using Landsat bands)
        ndvi = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
        nbr = image.normalizedDifference(['SR_B5', 'SR_B6']).rename('NBR')
        
        return image.addBands([ndvi, nbr])

    def _validate_image_data(self, image, roi):
        """Validate that image has actual data"""
        try:
            # Check if NDVI has valid values
            ndvi_stats = image.select('NDVI').reduceRegion(
                reducer=ee.Reducer.count(),
                geometry=roi,
                scale=100,
                maxPixels=1e9
            )
            
            pixel_count = ndvi_stats.get('NDVI').getInfo()
            return pixel_count is not None and pixel_count > 0
            
        except Exception:
            return False

    def classify_forest_and_estimate_biomass(self, roi_coords: Union[List, dict], 
                                           start_date: str = "2021-01-01", 
                                           end_date: str = "2023-01-01", 
                                           resolution: int = 10) -> Dict[str, Any]:
        """
        Forest classification and biomass estimation - REAL DATA ONLY
        """
        try:
            # Validate inputs
            start_date, end_date = self._validate_dates(start_date, end_date)
            roi = self._create_geometry(roi_coords)

            # Calculate ROI area
            area_m2 = roi.area()
            area_ha = area_m2.divide(10000)
            area_km2 = area_m2.divide(1e6)
            area_km2_val = area_km2.getInfo()

            print(f"🌲 Analyzing forest for {area_km2_val:.2f} km² area...")

            # Get satellite data - will raise exception if no data available
            satellite_result = self._get_satellite_data(roi, start_date, end_date)
            image = satellite_result['image']
            data_source = satellite_result['source']

            # Extract NDVI for classification
            ndvi = image.select('NDVI')

            # Create forest classification image
            forest_classification = ee.Image(1) \
                .where(ndvi.gte(self.moderate_forest_threshold).And(ndvi.lte(self.dense_forest_threshold)), 2) \
                .where(ndvi.gt(self.dense_forest_threshold), 3) \
                .rename('forest_class').clip(roi)

            # Calculate statistics
            stats = image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=roi,
                scale=resolution,
                maxPixels=1e11
            )

            mean_ndvi = stats.get('NDVI').getInfo()
            mean_nbr = stats.get('NBR').getInfo()
            area_ha_val = area_ha.getInfo()

            if mean_ndvi is None:
                raise Exception("No valid NDVI data found in the selected area")

            # Forest classification based on NDVI
            forest_class = self._classify_forest(mean_ndvi)

            # Biomass estimation based on NDVI
            above_biomass = self._estimate_biomass(mean_ndvi)
            below_biomass = round(0.2 * above_biomass, 2)
            total_biomass_per_ha = round(above_biomass + below_biomass, 2)
            total_biomass = round(total_biomass_per_ha * area_ha_val, 2)

            # Carbon stock estimation
            carbon_conversion_factor = 0.47
            average_carbon_per_ha = round(total_biomass_per_ha * carbon_conversion_factor, 2)
            total_carbon_stock = round(total_biomass * carbon_conversion_factor, 2)

            # CO₂ equivalent estimation
            co2_eq = round(total_carbon_stock * 3.67, 2)

            print(f"Forest analysis completed using {data_source}")

            return {
                "status": "success",
                "classification_image": forest_classification,
                "statistics": {
                    "roi_area_ha": round(area_ha_val, 2),
                    "roi_area_km2": round(area_km2_val, 2),
                    "mean_NDVI": round(mean_ndvi, 4),
                    "mean_NBR": round(mean_nbr or 0, 4),
                    "forest_classification": forest_class,
                    "data_source": data_source,
                    "images_processed": satellite_result['image_count'],
                    "biomass_partitioning": {
                        "aboveground_biomass_Mg_per_ha": round(above_biomass, 2),
                        "belowground_biomass_Mg_per_ha": below_biomass,
                        "total_biomass_Mg_per_ha": total_biomass_per_ha
                    },
                    "biomass_estimation": {
                        "average_biomass_Mg_per_ha": total_biomass_per_ha,
                        "total_biomass_Mg": total_biomass
                    },
                    "carbon_stock_estimation": {
                        "conversion_factor": carbon_conversion_factor,
                        "average_carbon_stock_MgC_per_ha": average_carbon_per_ha,
                        "total_carbon_stock_MgC": total_carbon_stock
                    },
                    "co2_equivalent_estimation": {
                        "conversion_factor": 3.67,
                        "total_co2_eq_Mg": co2_eq
                    }
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Forest analysis failed - no satellite data available for the selected area and time period"
            }

    def _classify_forest(self, ndvi_val: float) -> str:
        """Classify forest type based on NDVI value"""
        if ndvi_val > self.dense_forest_threshold:
            return "Dense Forest"
        elif ndvi_val > self.moderate_forest_threshold:
            return "Moderate Forest"
        else:
            return "Sparse or Non-Forest"

    def _estimate_biomass(self, ndvi_val: float) -> float:
        """Estimate biomass based on NDVI value using empirical relationships"""
        if ndvi_val > self.dense_forest_threshold:
            return 150.0  # Dense forest
        elif ndvi_val > self.moderate_forest_threshold:
            return 80.0   # Moderate forest
        else:
            return 25.0   # Sparse vegetation

    def create_forest_classification_image(self, roi_coords: Union[List, dict], 
                                         start_date: str, end_date: str, resolution: int = 10) -> ee.Image:
        """Create forest classification image for visualization."""
        try:
            result = self.classify_forest_and_estimate_biomass(roi_coords, start_date, end_date, resolution)
            if result["status"] == "success":
                return result["classification_image"]
            else:
                raise Exception(result.get("error", "Classification failed"))
        except Exception as e:
            raise Exception(f"Forest classification failed: {str(e)}")

    def get_forest_statistics(self, roi_coords: Union[List, dict], 
                            start_date: str, end_date: str, resolution: int = 10) -> Dict[str, Any]:
        """Get detailed forest statistics."""
        try:
            result = self.classify_forest_and_estimate_biomass(roi_coords, start_date, end_date, resolution)
            
            if result["status"] == "error":
                return result
            
            return {
                "status": "success",
                "forest_analysis": result["statistics"],
                "methodology": {
                    "approach": "Multi-satellite NDVI classification",
                    "thresholds": {
                        "dense_forest": f"NDVI > {self.dense_forest_threshold}",
                        "moderate_forest": f"NDVI {self.moderate_forest_threshold}-{self.dense_forest_threshold}",
                        "sparse_forest": f"NDVI < {self.moderate_forest_threshold}"
                    },
                    "data_sources": [source['name'] for source in self.satellite_sources],
                    "spatial_resolution": f"{resolution}m"
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Forest statistics calculation failed"
            }