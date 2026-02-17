# 🌍 Environmental Analysis Dashboard

An open-source geospatial intelligence platform for analyzing ecosystems using satellite data and Google Earth Engine. 
This web application enables users to interactively explore, classify, and analyze various biomes such as forests, wetlands, tundra, grasslands, oceans, and more — all through a lightweight, responsive interface.

### This is the application deployed link 
https://environmental-dashboard-deg3.onrender.com/

<p align="center">
  <img src="https://github.com/user-attachments/assets/500df625-6943-4bc5-a240-730b2bbb3cc9" width="45%" style="margin-right: 10px;" />
  <img src="https://github.com/user-attachments/assets/c4ccf591-ab4d-47cb-bce0-ca36ff815db8" width="45%" />
</p>


## 🌟 Key Features

### 🔍 Multi-Ecosystem Environmental Analysis
- 🌲 **Forest Classification**: NDVI-based forest density & biomass analysis
- 🌿 **Wetland Mapping**: Classifies wetlands using multiple spectral indices
- 🏔️ **Tundra Analysis**: Adaptive classification with permafrost awareness
- 🌱 **Grassland Classification**: Maps savannas and carbon-rich grasslands
- 🦠 **Algal Bloom Detection**: Detects harmful algal blooms in water bodies
- 🏜️ **Soil Moisture Analysis**: Evaluates soil water retention & dryness
- 🌊 **Ocean Chlorophyll**: Monitors marine productivity and trophic levels

### ⚙️ Analytical Capabilities
- 🛰️ Real-time satellite data processing using Google Earth Engine
- 📐 Adjustable spatial resolution (10m – 1000m)
- 🕒 Multi-temporal support for change detection
- 📊 Comprehensive classification statistics
- 🔄 Real-time status feedback & layer toggling
- 🔓 Fully open-source — no login or keys required

### 💡 User Experience & Interface
- 🗺️ Interactive ROI drawing tools on Leaflet map
- 📱 Responsive design for desktop and mobile
- 📊 Dynamic results panel with real-time updates
- 🧱 Clean modular frontend for easy maintenance
- ⏳ Live status indicators during analysis

---

## 🛠️ Tech Stack

### 🔧 Backend
- **FastAPI** – Asynchronous Python API framework
- **Google Earth Engine** – Satellite data processing & computation
- **Uvicorn** – Lightweight ASGI server for FastAPI
- **Python 3.9+**

### 🖥️ Frontend
- **Vanilla JavaScript** – Lightweight JS with modular scripts
- **Leaflet** – Interactive mapping library
- **HTML5 & CSS3** – Modern responsive UI
- **No heavy frameworks** – Simple and fast performance

---

## 🛰️ Data Sources & Satellites

The application utilizes real-time imagery and environmental data from:

- **Sentinel-2** – High-resolution optical imaging
- **Landsat 8 & 9** – Long-term Earth observation data
- **MODIS (Terra/Aqua)** – Global land/ocean data at medium resolution
- **Sentinel-3 OLCI** – Ocean and land color imagery
- **JRC Global Surface Water** – For water masking and seasonality
- **Google Earth Engine Datasets** – Processing backend for all analysis

---

## 📁 Directory Structure
```
environmental-analysis-dashboard/
├── main.py                    # FastAPI entrypoint
├── requirements.txt           # Python dependencies
├── runtime.txt                # Python runtime version for cloud hosting
├── .gitignore                 # Ignore venv, cache, etc.
├── static/                    # Frontend static files
│   ├── index.html             # Main HTML layout
│   ├── app.js                 # Core frontend JS logic
│   ├── apis_statistics.js     # JS module for displaying statistics
│   └── styles.css             # UI styling
├── api/                       # Analysis APIs (Python modules)
│   ├── forest_api.py
│   ├── wetland_api.py
│   ├── tundra_api.py
│   ├── grassland_api.py
│   ├── algal_blooms_api.py
│   ├── soil_api.py
│   └── ocean_api.py
├── legends/                   # Legends for visualization
│   ├── __init__.py
│   └── legend_configs.py
└── README.md                  # Project documentation (this file)
```
---

## 📖 User Guide

### 🧭 Step 1: Draw Region of Interest (ROI)
- Navigate to the web interface
- Use drawing tools on the map (rectangle or polygon)
- Your selected area will be used for all environmental analysis

### 📅 Step 2: Set Parameters
- Choose a **start date** and **end date** to define the temporal range
- Select the **spatial resolution** (e.g., 10m, 100m, 1000m)
- Recommended: Select periods with at least 6 months of data

### ⚙️ Step 3: Run Analysis
- Toggle any layer switch (e.g., Forest, Wetland, Ocean)
- The system will fetch satellite data and begin processing
- Real-time progress indicators will show processing status

### 📊 Step 4: View Results
- Once complete, the layer appears on the map
- You can:
  - View results in the statistics panel
  - Compare different layers
  - Explore dynamic legends for each classification

### 🔄 Optional Actions
- Run multiple analyses sequentially
- Switch ROI or time period to compare results
- Save screenshots or inspect data visually (export features coming soon)

---
## Acknowledgments
- **Google Earth Engine** - Satellite imagery and processing platform
- **European Space Agency** - Sentinel satellite missions
- **NASA** - Landsat and MODIS data
- **Leaflet** - Open-source mapping library
- **FastAPI** - Modern Python web framework


**Built with ❤️ for environmental research and conservation.**  
*Making satellite-based analysis accessible to everyone.*
