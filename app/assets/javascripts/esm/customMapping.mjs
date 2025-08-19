/* eslint no-undef: 0 */ // The vars aren't globally scoped and are therefore viewed as undefined

// Function to create a Leaflet Circle using latitude and longitude coordinates,
// radius and estimated bleed that is then added to the map
export function createLatitudelongitudeArea(L, first_coordinate, second_coordinate, radius, bleed, mapElement, markerIcon) {
  let coordinates = [first_coordinate, second_coordinate];
  let circle = createAreaCircle(L, coordinates, radius);
  let bleed_circle = createBleedCircle(L, coordinates, bleed);
  let pinpoint = L.marker(coordinates, {icon: markerIcon});
  createCoordinateAreaLabel('latitude_longitude', radius, first_coordinate, second_coordinate, mapElement);
  return [ circle, bleed_circle, pinpoint ];
}

// Function to create a Leaflet Circle using easting and northing coordinates,
// radius and estimated bleed that is then added to the map
export function createEastingNorthingArea(L, proj4, first_coordinate, second_coordinate, radius, bleed, mapElement, markerIcon) {
  let latlng = eastingsNorthingsToLatLng(proj4, parseFloat(first_coordinate), parseFloat(second_coordinate));
  let circle = createAreaCircle(L, latlng, radius);
  let bleed_circle = createBleedCircle(L, latlng, bleed);
  let pinpoint = L.marker(latlng, {icon: markerIcon});
  createCoordinateAreaLabel('easting_northing', radius, parseFloat(first_coordinate).toFixed(0), parseFloat(second_coordinate).toFixed(0), mapElement);
  return [ circle, bleed_circle, pinpoint ];
}

// Function to create a Leaflet Circle using postcode centroid,
// radius and estimated bleed that is then added to the map
export function createPostcodeArea(L, centroid, radius, bleed, postcode, mapElement, markerIcon) {
  let circle = createAreaCircle(L, centroid, radius);
  let bleed_circle = createBleedCircle(L, centroid, bleed);
  let pinpoint = L.marker(centroid, {icon: markerIcon});
  createPostcodeAreaLabel(radius, mapElement, postcode);
  return [ circle, bleed_circle, pinpoint ];
}

// Function that adds the Custom area features to the Leaflet map
export function addingFeaturesToMap(L, mymap, bleed_circle, circle, pinpoint) {
  console.log(bleed_circle);
  bleed_circle.addTo(mymap);
  circle.addTo(mymap);
  pinpoint.addTo(mymap);
  mymap.fitBounds(
    bleed_circle.getBounds(),
    {padding: [1, 1]}
  );
}

// Function that plots the centroid on the Leaflet map with custom marker and then adjusts the zoom level of the map
export function addingPostcodeCentroidMarkerToMap(L, mymap, centroid, markerIcon) {
  let pinpoint = L.marker(centroid, {icon: markerIcon});
  pinpoint.addTo(mymap);
  mymap.setView(pinpoint.getLatLng(), 13);
}

// Function that converts easting and northing coordinates to latitude and longitude, using proj4 library
export function eastingsNorthingsToLatLng(proj4, easting, northing) {
    let latlng = proj4('EPSG:27700', 'EPSG:4326', [easting, northing]);
    return [latlng[1], latlng[0]];
}

// Function that converts latitude and longitude coordinates to easting and northing, using proj4 library
export function latLngToEastingsNorthings(proj4, lat, lng) {
    let eastingnorthing = proj4('EPSG:4326', 'EPSG:27700',[lng, lat]);
    return [eastingnorthing[0], eastingnorthing[1]];
}

// Function to create Leaflet circle for the alert area
export function createAreaCircle(L, coordinates, radius) {
    return L.circle(coordinates, radius, {
      color: '#0201FE',
      fillColor: 'none',
      fillOpacity: 0.3,
      weight: 3,
    });
}

// Function to create Leaflet circle for the estimated bleed area
export function createBleedCircle(L, coordinates, bleed_radius) {
    return L.circle(coordinates, bleed_radius, {
      color: '#0201FE',
      fillColor: 'none',
      fillOpacity: 0.3,
      dashArray: '4,7.5,5,7.5,8,8,5,8,7.5,8,5,8,7,8,5,8,4',
      weight: 2,
    });
  }

// Function to create a label for the coordinate area plotted on the Leaflet map, that is then added as an aria-label to the map
export function createCoordinateAreaLabel(coordinate_type, radius, first_coordinate, second_coordinate, mapElement) {
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

// Function to create a label for the postcode area plotted on the Leaflet map, that is then added as an aria-label to the map
export function createPostcodeAreaLabel(radius, mapElement, postcode) {
    radius = radius / 1000;
    let label =  "Map of the United Kingdom, showing an area of "+radius+"km around the postcode "+postcode;
    mapElement.setAttribute('aria-label', label);
    appendAreaToAreaList(label);
  }

// Function to add the area description to the visually hidden area list
export function appendAreaToAreaList(label) {
    let area_list = document.querySelector('.area-list');
    let li = document.createElement("li");
    li.classList.add("area-list-item");
    li.classList.add("govuk-visually-hidden");
    li.textContent = label;
    area_list.appendChild(li);
}

// module.exports = {createLatitudelongitudeArea, createEastingNorthingArea, createPostcodeArea, addingFeaturesToMap,
//   addingPostcodeCentroidMarkerToMap, eastingsNorthingsToLatLng,
//   latLngToEastingsNorthings, createAreaCircle,
//   createBleedCircle, createCoordinateAreaLabel, createPostcodeAreaLabel, appendAreaToAreaList
// };
