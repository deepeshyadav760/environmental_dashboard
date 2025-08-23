import ee
from datetime import datetime
from typing import List, Union, Dict, Any

class OceanAPI:
    """
    Simplified Ocean Analysis API - Multiple Satellites, No Synthetic Fallbacks
    """

    def __init__(self):
        """Initialize Ocean API with chlorophyll classification thresholds"""
        self.chl_thresholds = {
            'oligotrophic': 5.0,      # 0-5 mg/m³
            'mesotrophic': 15.0,      # 5-15 mg/m³
            'moderate_eutrophic': 30.0, # 15-30 mg/m³
            'eutrophic': 90.0,        # 30-90 mg/m³
            'hypereutrophic': 100.0   # 90+ mg/m³
        }

        # Multiple satellite datasets for chlorophyll analysis (priority order)
        self.satellite_sources = [
            {
                'name': 'MODIS Aqua L3SMI',
                'dataset': 'NASA/OCEANDATA/MODIS-Aqua/L3SMI',
                'band': 'chlor_a',
                'scale': 4638
            },
            {
                'name': 'VIIRS SNPP L3SMI',
                'dataset': 'NASA/OCEANDATA/VIIRS-SNPP/L3SMI', 
                'band': 'chlor_a',
                'scale': 4638
            },
            {
                'name': 'MODIS Terra L3SMI',
                'dataset': 'NASA/OCEANDATA/MODIS-Terra/L3SMI',
                'band': 'chlor_a', 
                'scale': 4638
            },
            {
                'name': 'Sentinel-3 OLCI',
                'dataset': 'COPERNICUS/S3/OLCI',
                'band': ['Oa08_radiance', 'Oa06_radiance'],
                'scale': 300
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

    def _create_ocean_mask(self, roi) -> ee.Image:
        """Create ocean mask using JRC Global Surface Water"""
        try:
            # Use JRC Global Surface Water to identify water bodies
            jrc_water = ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
            
            # Create mask for areas with water occurrence
            water_occurrence = jrc_water.select('occurrence')
            ocean_mask = water_occurrence.gt(10)  # Areas with >10% water occurrence
            
            # Clean up the mask
            ocean_mask = ocean_mask.focal_max(radius=2, kernelType='circle') \
                .focal_min(radius=1, kernelType='circle')
            
            return ocean_mask.clip(roi).rename('ocean_mask')
            
        except Exception as e:
            print(f"Ocean mask creation error: {e}")
            raise Exception("Unable to create ocean mask for the selected area")

    def _get_chlorophyll_data(self, roi, start_date: str, end_date: str, ocean_mask: ee.Image) -> Dict[str, Any]:
        """Try multiple satellite sources for chlorophyll data - NO SYNTHETIC FALLBACKS"""
        
        for source in self.satellite_sources:
            try:
                print(f"🔍 Trying {source['name']} for chlorophyll data...")
                
                if source['name'] == 'Sentinel-3 OLCI':
                    result = self._process_sentinel3_olci(roi, start_date, end_date, ocean_mask)
                else:
                    result = self._process_ocean_color_data(
                        source['dataset'], source['band'], source['scale'],
                        roi, start_date, end_date, ocean_mask
                    )
                
                if result['data_available'] and result['mean_chlorophyll'] is not None:
                    result['data_source'] = source['name']
                    print(f"Successfully obtained data from {source['name']}")
                    return result
                else:
                    print(f"{source['name']}: No valid data found")
                    
            except Exception as e:
                print(f"{source['name']} failed: {e}")
                continue
        
        # If all sources fail, raise error - NO FALLBACKS
        raise Exception("No ocean chlorophyll data available for the selected area and time period. Please select coastal or marine areas with sufficient ocean coverage.")

    def _process_ocean_color_data(self, dataset: str, band: str, scale: int, 
                                roi, start_date: str, end_date: str, ocean_mask: ee.Image) -> Dict[str, Any]:
        """Process standard ocean color datasets"""
        collection = ee.ImageCollection(dataset) \
            .filterBounds(roi) \
            .filterDate(start_date, end_date) \
            .select(band)

        image_count = collection.size().getInfo()
        print(f"  Found {image_count} images")

        if image_count == 0:
            return {'data_available': False, 'mean_chlorophyll': None}

        # Get median composite
        chl_median = collection.median()
        
        # Apply ocean mask
        chl_ocean_only = chl_median.updateMask(ocean_mask)
        
        # Quality control - remove outliers
        chl_cleaned = chl_ocean_only.updateMask(
            chl_ocean_only.gt(0.01).And(chl_ocean_only.lt(100))
        )

        # Calculate statistics
        chl_stats = chl_cleaned.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=scale,
            maxPixels=1e9
        )

        mean_chl = chl_stats.get(band).getInfo()
        
        if mean_chl is None or mean_chl <= 0:
            return {'data_available': False, 'mean_chlorophyll': None}

        return {
            'chl_image': chl_cleaned.clip(roi).rename('chlor_a'),
            'mean_chlorophyll': round(mean_chl, 3),
            'data_available': True,
            'images_processed': image_count
        }

    def _process_sentinel3_olci(self, roi, start_date: str, end_date: str, ocean_mask: ee.Image) -> Dict[str, Any]:
        """Process Sentinel-3 OLCI data and convert to chlorophyll"""
        try:
            s3_collection = ee.ImageCollection('COPERNICUS/S3/OLCI') \
                .filterBounds(roi) \
                .filterDate(start_date, end_date) \
                .select(['Oa08_radiance', 'Oa06_radiance'])

            image_count = s3_collection.size().getInfo()
            print(f"  Found {image_count} Sentinel-3 OLCI images")

            if image_count == 0:
                return {'data_available': False, 'mean_chlorophyll': None}

            # Get median composite
            s3_image = s3_collection.median().clip(roi)

            # Calculate NDCI (Normalized Difference Chlorophyll Index)
            ndci = s3_image.normalizedDifference(['Oa06_radiance', 'Oa08_radiance']).rename('NDCI')
            
            # Convert NDCI to chlorophyll concentration using empirical relationship
            # Empirical formula: Chl-a = 10^(1.61 * NDCI + 0.082)
            # Simplified for this application: Chl-a ≈ NDCI * 25 + 2.5
            chl_estimate = ndci.multiply(25).add(2.5).clamp(0.1, 100).rename('chlor_a')
            
            # Apply ocean mask
            chl_ocean = chl_estimate.updateMask(ocean_mask)

            # Calculate statistics
            chl_stats = chl_ocean.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=roi,
                scale=300,
                maxPixels=1e9
            )

            mean_chl = chl_stats.get('chlor_a').getInfo()
            
            if mean_chl is None or mean_chl <= 0:
                return {'data_available': False, 'mean_chlorophyll': None}

            return {
                'chl_image': chl_ocean.clip(roi),
                'mean_chlorophyll': round(mean_chl, 3),
                'data_available': True,
                'images_processed': image_count
            }

        except Exception as e:
            print(f"Sentinel-3 OLCI processing error: {e}")
            return {'data_available': False, 'mean_chlorophyll': None}

    def analyze_chlorophyll(self, roi_coords: Union[List, dict],
                             start_date: str = "2021-01-01",
                             end_date: str = "2023-01-01",
                             resolution: int = 4638) -> Dict[str, Any]:
        """Main chlorophyll analysis with multiple satellite sources - NO FALLBACKS"""
        try:
            start_date, end_date = self._validate_dates(start_date, end_date)
            roi = self._create_geometry(roi_coords)
            area_km2 = roi.area().divide(1e6).getInfo()

            print(f"🌊 Analyzing ocean chlorophyll for {area_km2:.2f} km² area...")

            # Create ocean mask - will raise exception if fails
            ocean_mask = self._create_ocean_mask(roi)
            
            # Get chlorophyll data - will raise exception if no data available
            chl_result = self._get_chlorophyll_data(roi, start_date, end_date, ocean_mask)

            # Create classification
            classification_image = self._create_ocean_chlorophyll_classification(
                chl_result['chl_image'], ocean_mask, roi
            )

            # Calculate statistics
            statistics = self._calculate_ocean_statistics(
                chl_result, ocean_mask, area_km2, roi
            )

            print(f"Ocean chlorophyll analysis completed using {chl_result['data_source']}")

            return {
                "status": "success",
                "classification_image": classification_image,
                "statistics": statistics,
                "ocean_mask": ocean_mask
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Ocean chlorophyll analysis failed - no satellite data available or insufficient ocean coverage"
            }

    def _create_ocean_chlorophyll_classification(self, chl_image, ocean_mask, roi) -> ee.Image:
        """Create chlorophyll classification for ocean areas only"""
        try:
            # Chlorophyll classification based on trophic levels
            oligotrophic = chl_image.lte(self.chl_thresholds['oligotrophic'])
            mesotrophic = chl_image.gt(self.chl_thresholds['oligotrophic']).And(
                chl_image.lte(self.chl_thresholds['mesotrophic']))
            moderate_eutrophic = chl_image.gt(self.chl_thresholds['mesotrophic']).And(
                chl_image.lte(self.chl_thresholds['moderate_eutrophic']))
            eutrophic = chl_image.gt(self.chl_thresholds['moderate_eutrophic']).And(
                chl_image.lte(self.chl_thresholds['eutrophic']))
            hypereutrophic = chl_image.gt(self.chl_thresholds['eutrophic'])

            classification = ee.Image(0) \
                .where(mesotrophic, 1) \
                .where(moderate_eutrophic, 2) \
                .where(eutrophic, 3) \
                .where(hypereutrophic, 4)
            
            # Apply ocean mask
            ocean_classification = classification.updateMask(ocean_mask)
            
            return ocean_classification.rename('ocean_chl_class').clip(roi)

        except Exception as e:
            print(f"Classification error: {e}")
            raise Exception("Failed to create chlorophyll classification")

    def _calculate_ocean_statistics(self, chl_result: Dict, ocean_mask: ee.Image, 
                                   area_km2: float, roi) -> Dict[str, Any]:
        """Calculate ocean statistics"""
        try:
            # Calculate ocean area
            pixel_area = ee.Image.pixelArea().divide(1e6)
            ocean_area_result = pixel_area.updateMask(ocean_mask).reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=roi,
                scale=1000,
                maxPixels=1e9
            )
            
            ocean_area_km2 = ocean_area_result.get('area').getInfo()
            if ocean_area_km2 is None:
                ocean_area_km2 = 0
            
            land_area_km2 = area_km2 - ocean_area_km2
            ocean_coverage_percent = (ocean_area_km2 / area_km2) * 100 if area_km2 > 0 else 0
            
            # Determine data source quality
            data_source = chl_result.get('data_source', 'Unknown')
            is_satellite_data = chl_result.get('data_available', False)
            images_processed = chl_result.get('images_processed', 0)
            
            if ocean_area_km2 > 0 and chl_result['mean_chlorophyll'] is not None:
                trophic_status = self._classify_trophic_status(chl_result['mean_chlorophyll'])
                water_quality = self._assess_water_quality(chl_result['mean_chlorophyll'])
                bloom_risk = self._assess_bloom_risk(chl_result['mean_chlorophyll'])
                analysis_applicable = True
            else:
                trophic_status = "Insufficient ocean coverage"
                water_quality = "Not applicable"
                bloom_risk = "Not applicable"
                analysis_applicable = False

            return {
                "roi_area_km2": round(area_km2, 2),
                "land_area_km2": round(land_area_km2, 2),
                "ocean_area_km2": round(ocean_area_km2, 2),
                "ocean_coverage_percent": round(ocean_coverage_percent, 1),
                "mean_chlorophyll_mg_m3": chl_result['mean_chlorophyll'] if analysis_applicable else None,
                "trophic_status": trophic_status,
                "water_quality_assessment": water_quality,
                "bloom_risk": bloom_risk,
                "analysis_applicable": analysis_applicable,
                "data_source": data_source,
                "images_processed": images_processed,
                "satellite_data_used": is_satellite_data,
                "analysis_method": f"Multi-satellite ocean color analysis ({data_source})",
                "recommendation": "Ocean chlorophyll analysis completed" if analysis_applicable else "Select coastal or marine areas with >20% ocean coverage"
            }

        except Exception as e:
            print(f"Statistics calculation error: {e}")
            raise Exception("Failed to calculate ocean statistics")

    def _classify_trophic_status(self, chl_val: float) -> str:
        """Classify trophic status based on chlorophyll concentration"""
        if chl_val <= self.chl_thresholds['oligotrophic']:
            return "Oligotrophic (Very Low)"
        elif chl_val <= self.chl_thresholds['mesotrophic']:
            return "Mesotrophic (Low)"
        elif chl_val <= self.chl_thresholds['moderate_eutrophic']:
            return "Moderately Eutrophic"
        elif chl_val <= self.chl_thresholds['eutrophic']:
            return "Eutrophic (High)"
        else:
            return "Hypereutrophic (Very High)"

    def _assess_water_quality(self, chl_val: float) -> str:
        """Assess water quality based on chlorophyll levels"""
        if chl_val <= 5.0:
            return "Excellent - Clear ocean water"
        elif chl_val <= 15.0:
            return "Good - Productive ocean"
        elif chl_val <= 30.0:
            return "Moderate - Highly productive"
        elif chl_val <= 90.0:
            return "Poor - Very productive, potential issues"
        else:
            return "Very Poor - High bloom risk"

    def _assess_bloom_risk(self, chl_val: float) -> str:
        """Assess algal bloom risk based on chlorophyll levels"""
        if chl_val <= 15.0:
            return "Low"
        elif chl_val <= 30.0:
            return "Moderate"
        elif chl_val <= 90.0:
            return "High"
        else:
            return "Very High - Immediate concern"

    # Legacy interface methods for compatibility
    def create_chlorophyll_classification_image(self, roi_coords: Union[List, dict],
                                                start_date: str, end_date: str, 
                                                resolution: int = 4638) -> ee.Image:
        """Create classification image for visualization"""
        try:
            result = self.analyze_chlorophyll(roi_coords, start_date, end_date, resolution)
            if result["status"] == "success":
                return result["classification_image"]
            else:
                raise Exception(result.get("error", "Classification failed"))
        except Exception as e:
            raise Exception(f"Chlorophyll classification failed: {str(e)}")

    def get_chlorophyll_statistics(self, roi_coords: Union[List, dict],
                                   start_date: str, end_date: str, 
                                   resolution: int = 4638) -> Dict[str, Any]:
        """Get chlorophyll statistics"""
        try:
            result = self.analyze_chlorophyll(roi_coords, start_date, end_date, resolution)
            
            if result["status"] == "error":
                return result
            
            return {
                "status": "success",
                "chlorophyll_analysis": result["statistics"],
                "methodology": {
                    "approach": "Multi-satellite ocean color analysis",
                    "data_sources": [source['name'] for source in self.satellite_sources],
                    "ocean_masking": "JRC Global Surface Water",
                    "classification": "Trophic status based on chlorophyll-a concentration",
                    "spatial_resolution": f"{resolution}m (varies by satellite)"
                }
            }
        except Exception as e:
            return {
                "status": "error", 
                "error": str(e),
                "message": "Ocean chlorophyll analysis failed"
            }