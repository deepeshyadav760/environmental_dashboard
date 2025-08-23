# algal_blooms_api.py

import ee
from datetime import datetime
from typing import List, Union, Dict, Any

class AlgalBloomsAPI:
    """
    Algal Blooms Analysis API for detecting harmful algal blooms using Google Earth Engine.
    Uses Sentinel-3 OLCI data and NDCI (Normalized Difference Chlorophyll Index) for bloom detection.
    Updated to match the working algal_bloom_gee.py implementation.
    """

    def __init__(self):
        """Initialize Algal Blooms API with detection thresholds"""
        self.bloom_threshold_low = 0.05     # NDCI > 0.05 indicates potential bloom
        self.bloom_threshold_moderate = 0.1  # NDCI > 0.1 indicates moderate bloom
        self.bloom_threshold_high = 0.2    # NDCI > 0.2 indicates severe bloom

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

    def analyze_algal_bloom(self, roi_coords: Union[List, dict], start_date: str, end_date: str):
        """
        Performs Algal Bloom classification and analysis for a given ROI and date range.
        Uses Sentinel-3 OLCI data with water masking to prevent land misclassification.
        Optimized for memory efficiency while maintaining accuracy.
        """
        roi = ee.Geometry.Polygon(roi_coords)

        # --- 1. Sentinel-3 OLCI Data Collection ---
        print("Fetching Sentinel-3 OLCI data...")
        s3_collection = ee.ImageCollection("COPERNICUS/S3/OLCI") \
            .filterBounds(roi) \
            .filterDate(start_date, end_date) \
            .select(['Oa08_radiance', 'Oa06_radiance'])

        # Check if we have any images
        image_count = s3_collection.size().getInfo()
        if image_count == 0:
            raise ValueError(f"No Sentinel-3 OLCI images found for the period {start_date} to {end_date}. Try expanding the date range or check if the area contains water bodies.")

        print(f"Found {image_count} Sentinel-3 OLCI images")

        # Convert to float and get median composite (more stable than mean for large areas)
        s3_image = s3_collection.map(lambda img: img.toFloat()).median().clip(roi)

        # --- 2. Water Mask Creation ---
        print("Creating water mask...")
        water_mask_dataset = ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
        # Use occurrence > 0 to identify areas that have been detected as water at least once
        water_mask = water_mask_dataset.select('occurrence').gt(0).clip(roi)

        # --- 3. NDCI Calculation ---
        print("Calculating NDCI...")
        # NDCI = (Red Edge - Red) / (Red Edge + Red)
        # Oa06_radiance ≈ Red Edge (673.75 nm), Oa08_radiance ≈ Red (665 nm)
        ndci_unmasked = s3_image.normalizedDifference(['Oa06_radiance', 'Oa08_radiance']).rename('NDCI')
        
        # Apply water mask - only analyze water areas
        ndci = ndci_unmasked.updateMask(water_mask)

        # --- 4. Algal Bloom Classification ---
        print("Performing bloom classification...")
        # Classification based on NDCI thresholds:
        # Class 1: No Bloom / Clear Water (NDCI ≤ 0.05)
        # Class 2: Low Bloom (0.05 < NDCI ≤ 0.1)
        # Class 3: Moderate Bloom (0.1 < NDCI ≤ 0.2)
        # Class 4: Severe Bloom (NDCI > 0.2)
        
        algal_classes = ee.Image(1).rename('algal_class') \
            .where(ndci.gt(0.05), 2) \
            .where(ndci.gt(0.1), 3) \
            .where(ndci.gt(0.2), 4)

        # Apply water mask to final classification
        algal_classes_final = algal_classes.updateMask(water_mask).clip(roi)

        # --- 5. Statistics Calculation ---
        print("Calculating statistics...")
        
        # Calculate mean NDCI for water areas only
        mean_ndci_result = ndci.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=300,  # Sentinel-3 OLCI native resolution
            maxPixels=1e12,  # High limit for large areas
            tileScale=4  # Use tiling for memory efficiency
        )

        # Calculate area for each bloom class
        pixel_area_ha = ee.Image.pixelArea().divide(10000)  # Convert to hectares
        area_by_class_result = pixel_area_ha.addBands(algal_classes_final).reduceRegion(
            reducer=ee.Reducer.sum().group(
                groupField=1,
                groupName='class',
            ),
            geometry=roi,
            scale=300,
            maxPixels=1e12,
            tileScale=4
        ).get('groups')

        # --- 6. Process and Return Results ---
        print("Processing results...")
        results_dict = ee.Dictionary({
            'area_by_class': area_by_class_result,
            'mean_ndci': mean_ndci_result.get('NDCI'),
            'image_count': image_count
        }).getInfo()

        # Process area results
        area_results_list = results_dict.get('area_by_class', [])
        class_areas = {item['class']: item['sum'] for item in area_results_list} if area_results_list else {}

        area_no_bloom = class_areas.get(1, 0)
        area_low_bloom = class_areas.get(2, 0)
        area_moderate_bloom = class_areas.get(3, 0)
        area_severe_bloom = class_areas.get(4, 0)

        total_bloom_area_ha = area_low_bloom + area_moderate_bloom + area_severe_bloom
        mean_ndci_value = results_dict.get('mean_ndci')

        final_statistics = {
            "mean_ndci": round(mean_ndci_value, 4) if isinstance(mean_ndci_value, (int, float)) else None,
            "images_processed": results_dict.get('image_count', 0),
            "classification_by_area_ha": {
                "no_bloom_ha": round(area_no_bloom, 2),
                "low_bloom_ha": round(area_low_bloom, 2),
                "moderate_bloom_ha": round(area_moderate_bloom, 2),
                "severe_bloom_ha": round(area_severe_bloom, 2),
                "total_bloom_area_ha": round(total_bloom_area_ha, 2)
            }
        }

        return {
            "statistics": final_statistics,
            "gee_images": {
                "algal_bloom_classification": algal_classes_final
            }
        }

    def detect_algal_bloom(self, roi_coords: Union[List, dict], 
                        start_date: str = "2021-01-01", 
                        end_date: str = "2023-01-01", 
                        resolution: int = 300) -> Dict[str, Any]:
        """
        Main algal bloom detection function.
        
        Args:
            roi_coords: Region of interest coordinates
            start_date: Analysis start date (YYYY-MM-DD)
            end_date: Analysis end date (YYYY-MM-DD)
            resolution: Spatial resolution in meters (300m for Sentinel-3 OLCI)
            
        Returns:
            Dictionary containing bloom analysis results
        """
        try:
            # Validate inputs
            start_date, end_date = self._validate_dates(start_date, end_date)
            print(f"Starting algal bloom analysis for period: {start_date} to {end_date}")

            # Perform the analysis
            result = self.analyze_algal_bloom(roi_coords, start_date, end_date)
            
            # Extract results
            classification_image = result["gee_images"]["algal_bloom_classification"]
            statistics = result["statistics"]
            
            # Convert statistics to API format
            converted_statistics = self._convert_statistics_format(statistics, roi_coords)
            
            print("Algal bloom analysis completed successfully")
            return {
                "status": "success",
                "classification_image": classification_image,
                "statistics": converted_statistics,
                "data_source": "Sentinel-3 OLCI"
            }
                
        except Exception as e:
            print(f"Algal bloom analysis failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Algal bloom analysis failed. Please check if the area contains water bodies and try a different date range."
            }

    def _convert_statistics_format(self, statistics: Dict[str, Any], roi_coords: Union[List, dict]) -> Dict[str, Any]:
        """Convert statistics from analysis format to API format"""
        try:
            roi = self._create_geometry(roi_coords)
            roi_area_sq_km = roi.area(maxError=100).divide(1e6).getInfo()
            
            mean_ndci = statistics.get("mean_ndci")
            classification_by_area = statistics.get("classification_by_area_ha", {})
            images_processed = statistics.get("images_processed", 0)
            
            # Determine bloom detection and severity
            bloom_detected = False
            severity_level = "No bloom"
            
            if isinstance(mean_ndci, (int, float)):
                bloom_detected = mean_ndci > self.bloom_threshold_low
                severity_level = self._classify_severity(mean_ndci)
            
            # Calculate bloom extent in km²
            total_bloom_area_ha = classification_by_area.get("total_bloom_area_ha", 0)
            bloom_extent_sq_km = total_bloom_area_ha / 100  # Convert hectares to km²
            
            # Calculate water quality indicators
            chl_indicator = "High" if isinstance(mean_ndci, (int, float)) and mean_ndci > 0.15 else \
                        "Moderate" if isinstance(mean_ndci, (int, float)) and mean_ndci > 0.08 else "Low"
            
            turbidity_level = "High" if isinstance(mean_ndci, (int, float)) and mean_ndci > 0.12 else \
                            "Moderate" if isinstance(mean_ndci, (int, float)) and mean_ndci > 0.06 else "Low"
            
            return {
                "roi_area_sq_km": round(roi_area_sq_km, 2),
                "mean_ndci": mean_ndci,
                "bloom_detected": bloom_detected,
                "bloom_extent_sq_km": round(bloom_extent_sq_km, 2),
                "severity_level": severity_level,
                "classification_by_area_ha": classification_by_area,
                "water_quality_indicators": {
                    "chlorophyll_indicator": chl_indicator,
                    "turbidity_level": turbidity_level
                },
                "data_quality": {
                    "images_processed": images_processed,
                    "analysis_method": "Sentinel-3 OLCI NDCI",
                    "spatial_resolution": "300m",
                    "water_masked": True
                }
            }
            
        except Exception as e:
            print(f"Statistics conversion error: {e}")
            raise e

    def _classify_severity(self, ndci_val: float) -> str:
        """Classify bloom severity based on NDCI value"""
        if ndci_val is None or not isinstance(ndci_val, (int, float)) or ndci_val <= self.bloom_threshold_low:
            return "No bloom"
        elif ndci_val <= self.bloom_threshold_moderate:
            return "Low"
        elif ndci_val <= self.bloom_threshold_high:
            return "Moderate"
        else:
            return "Severe"

    def create_algal_bloom_classification_image(self, roi_coords: Union[List, dict], 
                                            start_date: str, end_date: str, resolution: int = 300) -> ee.Image:
        """
        Create an algal bloom classification image for visualization.
        
        Args:
            roi_coords: Region of interest coordinates
            start_date: Analysis start date (YYYY-MM-DD)
            end_date: Analysis end date (YYYY-MM-DD)
            resolution: Spatial resolution in meters
            
        Returns:
            Earth Engine Image with algal bloom classification
        """
        try:
            result = self.detect_algal_bloom(roi_coords, start_date, end_date, resolution)
            if result["status"] == "success":
                return result["classification_image"]
            else:
                raise ValueError(result.get("error", "Classification failed"))
                
        except Exception as e:
            print(f"Algal bloom image creation error: {e}")
            raise e

    def get_algal_bloom_statistics(self, roi_coords: Union[List, dict], 
                                start_date: str, end_date: str, resolution: int = 300) -> Dict[str, Any]:
        """
        Get detailed algal bloom statistics.
        
        Args:
            roi_coords: Region of interest coordinates
            start_date: Analysis start date (YYYY-MM-DD)
            end_date: Analysis end date (YYYY-MM-DD)
            resolution: Spatial resolution in meters
            
        Returns:
            Dictionary containing detailed algal bloom statistics
        """
        try:
            result = self.detect_algal_bloom(roi_coords, start_date, end_date, resolution)
            
            if result["status"] == "error":
                return result
            
            return {
                "status": "success",
                "algal_bloom_analysis": result["statistics"],
                "methodology": {
                    "approach": "Sentinel-3 OLCI NDCI-based bloom detection",
                    "primary_index": "NDCI (Normalized Difference Chlorophyll Index)",
                    "water_masking": "JRC Global Surface Water occurrence > 0",
                    "thresholds": {
                        "no_bloom": f"NDCI ≤ {self.bloom_threshold_low}",
                        "low_bloom": f"NDCI {self.bloom_threshold_low}-{self.bloom_threshold_moderate}",
                        "moderate_bloom": f"NDCI {self.bloom_threshold_moderate}-{self.bloom_threshold_high}",
                        "severe_bloom": f"NDCI > {self.bloom_threshold_high}"
                    },
                    "data_source": "Sentinel-3 OLCI",
                    "spatial_resolution": "300m",
                    "temporal_composite": "Median"
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Algal bloom statistics calculation failed"
            }