function createLatitudelongitudeArea(first_coordinate, second_coordinate, radius, bleed, mapElement) {
  circle = createAreaCircle([first_coordinate, second_coordinate], radius);
  bleed_circle = createBleedCircle([first_coordinate, second_coordinate], bleed);
  pinpoint = L.marker([first_coordinate, second_coordinate], {icon: markerIcon});
  createCoordinateAreaLabel('latitude_longitude', radius, first_coordinate, second_coordinate, mapElement);
  return circle, bleed_circle, pinpoint;
}

function createEastingNorthingArea(first_coordinate, second_coordinate, radius, bleed, mapElement) {
  latlngs = eastingsNorthingsToLatLng(parseFloat(first_coordinate), parseFloat(second_coordinate));
  circle = createAreaCircle([latlngs.lat, latlngs.lng], radius);
  bleed_circle = createBleedCircle([latlngs.lat, latlngs.lng], bleed);
  pinpoint = L.marker([latlngs.lat, latlngs.lng], {icon: markerIcon});
  createCoordinateAreaLabel('easting_northing', radius, parseFloat(first_coordinate).toFixed(0), parseFloat(second_coordinate).toFixed(0), mapElement);
  return circle, bleed_circle, pinpoint;
}

function createPostcodeArea(centroid, radius, bleed, postcode) {
  circle = createAreaCircle(centroid, radius);
  bleed_circle = createBleedCircle(centroid, bleed);
  pinpoint = L.marker(centroid, {icon: markerIcon});
  createPostcodeAreaLabel(radius, mapElement, postcode);
  return circle, bleed_circle, pinpoint;
}

function addingFeaturesToMap(mymap, bleed_circle, circle, pinpoint) {
  bleed_circle.addTo(mymap);
  circle.addTo(mymap);
  pinpoint.addTo(mymap);
  mymap.fitBounds(
    bleed_circle.getBounds(),
    {padding: [1, 1]}
  );
}

function addingPostcodeCentroidMarkerToMap(mymap, centroid) {
  pinpoint = L.marker(centroid, {icon: markerIcon});
  pinpoint.addTo(mymap);
  mymap.setView(pinpoint.getLatLng(), 13);
}

function eastingsNorthingsToLatLng(easting, northing) {
    let latlng = proj4('EPSG:27700', 'EPSG:4326', [easting, northing]);
    return {lat: latlng[1], lng: latlng[0]};
}

function latLngToEastingsNorthings(lat, lng) {
    let eastingnorthing = proj4('EPSG:4326', 'EPSG:27700',[lng, lat]);
    return {easting: eastingnorthing[0], northing: eastingnorthing[1]};
}

function createAreaCircle(coordinates, radius) {
    return L.circle(coordinates, radius, {
      color: '#0201FE',
      fillColor: 'none',
      fillOpacity: 0.3,
      weight: 3,
    });
}

function createBleedCircle(coordinates, bleed_radius) {
    return L.circle(coordinates, bleed_radius, {
      color: '#0201FE',
      fillColor: 'none',
      fillOpacity: 0.3,
      dashArray: '4,7.5,5,7.5,8,8,5,8,7.5,8,5,8,7,8,5,8,4',
      weight: 2,
    });
  }

function createCoordinateAreaLabel(coordinate_type, radius, first_coordinate, second_coordinate, mapElement) {
    radius = radius / 1000;
    let label;
    if (coordinate_type == 'latitude_longitude') {
      label =  "Map of the United Kingdom, showing an area of "+radius+"km around the latitude "+parseFloat(first_coordinate).toFixed(2)+", longitude "+parseFloat(second_coordinate).toFixed(2);
    } else if (coordinate_type == 'easting_northing') {
      label =  "Map of the United Kingdom, showing an area of "+radius+"km around the easting of "+ first_coordinate + ", northing of " + second_coordinate;
    }
    appendAreaToAreaList(label);
    mapElement.setAttribute('aria-label', label);
  }

function createPostcodeAreaLabel(radius, mapElement, postcode) {
    radius = radius / 1000;
    let label;
    label =  "Map of the United Kingdom, showing an area of "+radius+"km around the postcode "+postcode;
    mapElement.setAttribute('aria-label', label);
    appendAreaToAreaList(label);
  }

function appendAreaToAreaList(label) {
    let area_list = document.querySelector('.area-list');
    let li = document.createElement("li");
    li.classList.add("area-list-item");
    li.classList.add("govuk-visually-hidden");
    li.textContent = label;
    area_list.appendChild(li);
}
