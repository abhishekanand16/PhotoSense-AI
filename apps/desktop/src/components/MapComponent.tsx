import React, { useEffect, useRef, useMemo } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import "leaflet.markercluster";
import { PhotoLocation } from "../services/api";

// Fix default marker icons issue with Leaflet + bundlers
// @ts-ignore
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

interface MapComponentProps {
  locations: PhotoLocation[];
  onClusterClick?: (bounds: L.LatLngBounds, photoIds: number[]) => void;
  onMarkerClick?: (photoId: number) => void;
  selectedPhotoId?: number | null;
  height?: string;
  defaultZoom?: number;
  className?: string;
}

const MapComponent: React.FC<MapComponentProps> = ({
  locations,
  onClusterClick,
  onMarkerClick,
  selectedPhotoId,
  height = "300px",
  defaultZoom = 3,
  className = "",
}) => {
  const mapRef = useRef<L.Map | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const markersRef = useRef<L.MarkerClusterGroup | null>(null);
  const selectedMarkerRef = useRef<L.Marker | null>(null);

  // Calculate map center from locations
  const center = useMemo(() => {
    if (locations.length === 0) {
      return [20, 0] as [number, number]; // World center
    }
    const avgLat = locations.reduce((sum, loc) => sum + loc.latitude, 0) / locations.length;
    const avgLon = locations.reduce((sum, loc) => sum + loc.longitude, 0) / locations.length;
    return [avgLat, avgLon] as [number, number];
  }, [locations]);

  // Initialize map
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    // Create map
    const map = L.map(containerRef.current, {
      center: center,
      zoom: locations.length === 0 ? 2 : defaultZoom,
      scrollWheelZoom: true,
      zoomControl: true,
    });

    // Add OpenStreetMap tiles
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(map);

    mapRef.current = map;

    // Cleanup on unmount
    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  // Update markers when locations change
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Remove existing markers
    if (markersRef.current) {
      map.removeLayer(markersRef.current);
    }

    if (locations.length === 0) return;

    // Create marker cluster group
    const markers = L.markerClusterGroup({
      chunkedLoading: true,
      maxClusterRadius: 50,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      zoomToBoundsOnClick: false, // We handle clicks ourselves
      iconCreateFunction: (cluster) => {
        const count = cluster.getChildCount();
        let size = "small";
        if (count > 100) size = "large";
        else if (count > 10) size = "medium";

        return L.divIcon({
          html: `<div class="cluster-marker cluster-${size}"><span>${count}</span></div>`,
          className: "marker-cluster-custom",
          iconSize: L.point(40, 40),
        });
      },
    });

    // Add markers for each location
    const markerMap = new Map<number, L.Marker>();
    
    locations.forEach((loc) => {
      const marker = L.marker([loc.latitude, loc.longitude], {
        title: loc.city || loc.region || loc.country || "Photo",
      });

      // Store photo_id in marker options
      (marker.options as any).photoId = loc.photo_id;

      marker.on("click", () => {
        if (onMarkerClick) {
          onMarkerClick(loc.photo_id);
        }
      });

      // Add popup with location name
      const locationName = [loc.city, loc.region, loc.country]
        .filter(Boolean)
        .join(", ") || "Unknown location";
      marker.bindPopup(`<b>${locationName}</b>`);

      markers.addLayer(marker);
      markerMap.set(loc.photo_id, marker);
    });

    // Handle cluster clicks
    markers.on("clusterclick", (e: any) => {
      const cluster = e.layer;
      const childMarkers = cluster.getAllChildMarkers();
      const photoIds = childMarkers.map((m: any) => m.options.photoId).filter(Boolean);
      const bounds = cluster.getBounds();

      if (onClusterClick) {
        onClusterClick(bounds, photoIds);
      }

      // Zoom to cluster bounds
      map.fitBounds(bounds, { padding: [50, 50] });
    });

    map.addLayer(markers);
    markersRef.current = markers;

    // Fit map to show all markers
    if (locations.length > 0) {
      const bounds = markers.getBounds();
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 });
      }
    }
  }, [locations, onClusterClick, onMarkerClick]);

  // Handle selected photo highlighting
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedPhotoId) return;

    // Find the location for the selected photo
    const selectedLocation = locations.find((loc) => loc.photo_id === selectedPhotoId);
    if (!selectedLocation) return;

    // Remove previous selected marker
    if (selectedMarkerRef.current) {
      map.removeLayer(selectedMarkerRef.current);
    }

    // Create a highlighted marker for the selected photo
    const highlightIcon = L.divIcon({
      html: `<div class="selected-marker-pulse"></div>`,
      className: "selected-marker",
      iconSize: L.point(24, 24),
      iconAnchor: L.point(12, 12),
    });

    const highlightMarker = L.marker(
      [selectedLocation.latitude, selectedLocation.longitude],
      { icon: highlightIcon, zIndexOffset: 1000 }
    );

    highlightMarker.addTo(map);
    selectedMarkerRef.current = highlightMarker;

    // Pan to the selected location smoothly
    map.setView([selectedLocation.latitude, selectedLocation.longitude], 
      Math.max(map.getZoom(), 10), 
      { animate: true }
    );

    return () => {
      if (selectedMarkerRef.current && map) {
        map.removeLayer(selectedMarkerRef.current);
      }
    };
  }, [selectedPhotoId, locations]);

  // Update map center when it changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || locations.length === 0) return;
    
    // Only recenter if we have a significant change
    const currentCenter = map.getCenter();
    const distance = map.distance(currentCenter, L.latLng(center[0], center[1]));
    if (distance > 100000) { // More than 100km difference
      map.setView(center, defaultZoom, { animate: true });
    }
  }, [center, defaultZoom]);

  return (
    <>
      <style>{`
        .marker-cluster-custom {
          background: transparent;
        }
        .cluster-marker {
          background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
          border-radius: 50%;
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;
          font-size: 12px;
          box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
          border: 3px solid white;
        }
        .cluster-small {
          width: 36px;
          height: 36px;
          font-size: 11px;
        }
        .cluster-medium {
          width: 44px;
          height: 44px;
          font-size: 13px;
        }
        .cluster-large {
          width: 52px;
          height: 52px;
          font-size: 15px;
        }
        .selected-marker {
          background: transparent;
        }
        .selected-marker-pulse {
          width: 24px;
          height: 24px;
          background: #ef4444;
          border-radius: 50%;
          border: 3px solid white;
          box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
          animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
          0% {
            box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
          }
          70% {
            box-shadow: 0 0 0 15px rgba(239, 68, 68, 0);
          }
          100% {
            box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);
          }
        }
        .leaflet-container {
          border-radius: 16px;
          font-family: inherit;
        }
        .leaflet-popup-content-wrapper {
          border-radius: 12px;
        }
        .leaflet-popup-content {
          margin: 12px 16px;
          font-size: 13px;
        }
      `}</style>
      <div
        ref={containerRef}
        className={`rounded-2xl overflow-hidden ${className}`}
        style={{ height, width: "100%" }}
      />
    </>
  );
};

export default MapComponent;
