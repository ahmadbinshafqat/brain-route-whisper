const points = window.ROUTE_POINTS || [];
if (points.length > 0) {
  const map = L.map('map');
  const latLngs = points.map((p) => [p.lat, p.lng]);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  latLngs.forEach((latLng, index) => {
    const point = points[index];
    L.marker(latLng)
      .addTo(map)
      .bindPopup(`<strong>${point.order}. ${point.label}</strong>`);
  });

  L.polyline(latLngs, { color: '#6d28d9', weight: 4, opacity: 0.8 }).addTo(map);
  map.fitBounds(latLngs, { padding: [35, 35] });
}
