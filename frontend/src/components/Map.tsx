import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import axios from 'axios';
import L from 'leaflet';

// Fix for default marker icon in Leaflet with Vite/Webpack
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});

L.Marker.prototype.options.icon = DefaultIcon;

const MapComponent: React.FC = () => {
    const [geoJsonData, setGeoJsonData] = useState(null);

    useEffect(() => {
        axios.get('http://localhost:8000/api/stations')
            .then(response => {
                setGeoJsonData(response.data);
            })
            .catch(error => {
                console.error("Error fetching station data:", error);
            });
    }, []);

    const downloadStationJson = (feature: any) => {
        const url = window.URL.createObjectURL(
            new Blob([JSON.stringify(feature, null, 2)], { type: 'application/json' })
        );
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `station_${feature.properties.station_id}.json`);
        document.body.appendChild(link);
        link.click();
        link.parentNode?.removeChild(link);
    };

    const onEachFeature = (feature: any, layer: L.Layer) => {
        if (feature.properties && feature.properties.name) {
            const btnId = `download-btn-${feature.properties.station_id}`;
            const popupContent = `
                <div style="font-family: sans-serif; font-size: 14px; min-width: 200px;">
                    <h3 style="margin: 0 0 8px 0; border-bottom: 1px solid #ccc; padding-bottom: 4px;">${feature.properties.name} (${feature.properties.station_id})</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px;">
                        <strong>Country:</strong> <span>${feature.properties.country}</span>
                        <strong>Elevation:</strong> <span>${feature.properties.elevation_m} m</span>
                        
                        <strong>Temp:</strong> <span>${feature.properties.temperature_c} °C</span>
                        <strong>Dew Point:</strong> <span>${feature.properties.dew_point_c} °C</span>
                        
                        <strong>Wind:</strong> <span>${feature.properties.wind_direction_deg}° / ${feature.properties.wind_speed_kt} kt</span>
                        <strong>Visibility:</strong> <span>${feature.properties.visibility_km} km</span>
                        
                        <strong>Pressure:</strong> <span>${feature.properties.pressure_hpa} hPa</span>
                        <strong>Station P:</strong> <span>${feature.properties.station_pressure_hpa} hPa</span>
                        
                        <strong>Pressure Tendency:</strong> <span>${feature.properties.pressure_change_3h} hPa (${feature.properties.pressure_tendency_characteristic})</span>
                        
                        <strong>Weather Code:</strong> <span>${feature.properties.present_weather_code || 'N/A'}</span>
                        <strong>Cloud Cover:</strong> <span>${feature.properties.cloud_cover_octas}/8</span>
                    </div>
                    <div style="margin-top: 8px; display: flex; justify-content: space-between; align-items: center;">
                        <button id="${btnId}" style="padding: 4px 8px; cursor: pointer; background: #007bff; color: white; border: none; border-radius: 3px; font-size: 12px;">Download JSON</button>
                    </div>
                    <div style="margin-top: 8px; font-size: 12px; color: #555;">
                        <p style="margin: 2px 0;">Raw: ${feature.properties.raw_synop.split('\n')[0]}...</p>
                    </div>
                </div>
            `;
            layer.bindPopup(popupContent);
            layer.on('popupopen', () => {
                const btn = document.getElementById(btnId);
                if (btn) {
                    btn.onclick = (e) => {
                        e.stopPropagation(); // Prevent map click propagation if any
                        downloadStationJson(feature);
                    };
                }
            });
        }
    };

    const downloadJson = () => {
        if (!geoJsonData) return;
        const url = window.URL.createObjectURL(
            new Blob([JSON.stringify(geoJsonData, null, 2)], { type: 'application/json' })
        );
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'weather_stations.json');
        document.body.appendChild(link);
        link.click();
        link.parentNode?.removeChild(link);
    };

    return (
        <div style={{ position: 'relative', height: '100vh', width: '100%' }}>
            <MapContainer center={[20.5937, 78.9629]} zoom={5} style={{ height: '100%', width: '100%' }}>
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                {geoJsonData && (
                    <GeoJSON data={geoJsonData} onEachFeature={onEachFeature} />
                )}
            </MapContainer>
            <button
                onClick={downloadJson}
                style={{
                    position: 'absolute',
                    top: '80px',
                    left: '10px',
                    zIndex: 1000,
                    padding: '8px 12px',
                    backgroundColor: 'white',
                    border: '2px solid rgba(0,0,0,0.2)',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontWeight: 'bold',
                    boxShadow: '0 1px 5px rgba(0,0,0,0.4)'
                }}
            >
                Download
            </button>
        </div>
    );
};

export default MapComponent;
