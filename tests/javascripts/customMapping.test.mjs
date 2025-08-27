const helpers = require('./support/helpers');
const {createLatitudelongitudeArea, createEastingNorthingArea, createPostcodeArea, addingFeaturesToMap,
    addingPostcodeCentroidMarkerToMap, eastingsNorthingsToLatLng,
    latLngToEastingsNorthings, createAreaCircle,
    createBleedCircle, createCoordinateAreaLabel, createPostcodeAreaLabel, appendAreaToAreaList
} = require('../../app/assets/javascripts/esm/customMapping.mjs')

const L = require('leaflet');
const proj4 = require('proj4');
proj4.defs("EPSG:27700",
  "+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 +x_0=400000 +y_0=-100000 +ellps=airy +towgs84=446.448,-125.157,542.06,0.15,0.247,0.842,-20.489 +units=m +no_defs +type=crs");

let latitude = 51.503630;
let longitude = -0.126770;
let easting = 530111;
let northing = 179963;
let radius = 5000;
let bleed = 7000;
let postcode = 'SW1A 2AS';

let mymap = {fitBounds: jest.fn(), setView: jest.fn(), addLayer: jest.fn()}

beforeAll(() => {
    require('./support/teardown.js');
});

beforeEach(() => {
    require('./support/teardown.js');
    markerIcon = L.icon({
        iconUrl:"test.jpg"
    });
    document.body.innerHTML = `<div class="govuk-form-group">
      <label class="govuk-label" for="postcode">
      Postcode
      </label>
      <input class="govuk-input govuk-input--width-10" id="postcode" name="postcode" type="Search" value="rg128sn">
      </div>
      <ul class="area-list">
      </ul>
      <div id="area-list-map" role="region" aria-label="Map of the United Kingdom, showing no areas" aria-describedby="area-list-map__description" </div>`;
    mapElement = document.getElementById('area-list-map');
});

afterEach(() => {
    document.body.innerHTML = '';
});

afterAll(() => {
    require('./support/teardown.js');
});

describe('Eastings and northings coordinates can be converted into latitude and longitude coordinates', () => {
    test("User has entered the eastings and northings", () => {
        latitude_longitude = eastingsNorthingsToLatLng(proj4, easting, northing)
        expect(latitude_longitude[1]).toBeCloseTo(-0.12676920841036216, 13);
        expect(latitude_longitude[0]).toBeCloseTo(51.50363280909527, 13);
    });
})

describe('Latitude and longitude coordinates can be converted into eastings and northing coordinates', () => {
    test("User has entered the eastings and northings", () => {
        expect(latLngToEastingsNorthings(proj4, latitude, longitude)[0]).toBe(530110.9539385812);
        expect(latLngToEastingsNorthings(proj4, latitude, longitude, proj4)[1]).toBe(179962.68572307157);
    });
})

describe('Area and bleed circles are created when user inputs coordinates/postcode and radius and searches', () => {

    test("User has entered the latitude, longitude and radius and then searched to generate the leaflet circle and marker on the map", () => {
        circle = createAreaCircle(L, [latitude, longitude], radius);
        bleed_circle = createBleedCircle(L, [latitude, longitude], bleed);
        expect(circle._mRadius).toBe(5000);
        expect(circle._latlng.lat).toBeCloseTo(latitude);
        expect(circle._latlng.lng).toBeCloseTo(longitude);
        expect(circle instanceof L.Circle).toBe(true);

        expect(bleed_circle._mRadius).toBe(bleed);
        expect(bleed_circle._latlng.lat).toBeCloseTo(latitude);
        expect(bleed_circle._latlng.lng).toBeCloseTo(longitude);
        expect(bleed_circle instanceof L.Circle).toBe(true);
    });
})

describe('Coordinate Area label is created when area is created using coordinates and radius', () => {

    test("User has entered the latitude, longitude and radius and then searched to generate the area label", () => {
        createCoordinateAreaLabel('latitude_longitude', radius, latitude, longitude, mapElement);
        expected_label = "Map of the United Kingdom, showing an area of " + radius / 1000 + "km around the latitude " + latitude.toFixed(2) + ", longitude " + longitude.toFixed(2);
        expect(document.getElementById('area-list-map').getAttribute('aria-label')).toBe(expected_label);
    });
    test("User has entered the latitude, longitude and radius and then searched to generate the area label", () => {
        createCoordinateAreaLabel("easting_northing", radius, easting, northing, mapElement);
        expected_label = "Map of the United Kingdom, showing an area of " + radius / 1000 + "km around the easting of " + easting.toFixed(0) + ", northing of " + northing.toFixed(0);
        expect(document.getElementById('area-list-map').getAttribute('aria-label')).toBe(expected_label);
    });
})

describe('Postcode Area label is created when area is created using postcode and radius', () => {

    test("User has entered the postcode and radius and then searched to generate the leaflet circle and marker on the map", () => {
        createPostcodeAreaLabel(radius, mapElement, postcode);
        expected_label = "Map of the United Kingdom, showing an area of " + radius / 1000 + "km around the postcode " + postcode;
        expect(document.getElementById('area-list-map').getAttribute('aria-label')).toBe(expected_label);
    });

});

describe('Latitude and longitude area is created on the map when latitude and longitude searched and radius entered', () => {
    let bleed_circle = {addTo: jest.fn(), getBounds: jest.fn().mockReturnValue({extend: jest.fn()})};
    let circle = {addTo: jest.fn(), getBounds: jest.fn().mockReturnValue({extend: jest.fn()})};
    let pinpoint = {addTo: jest.fn(), getLatLng: jest.fn().mockReturnValue([0,0])};
    test("User has entered the postcode and radius and then searched to generate the leaflet circle and marker on the map", () => {
        createLatitudelongitudeArea(L, latitude, longitude, radius, bleed, mapElement);
        addingFeaturesToMap(L, mymap, bleed_circle, circle, pinpoint);
        expect(bleed_circle.addTo).toHaveBeenCalledWith(mymap);
        expect(circle.addTo).toHaveBeenCalledWith(mymap);
        expect(pinpoint.addTo).toHaveBeenCalledWith(mymap);
        expect(mymap.fitBounds).toHaveBeenCalledWith(bleed_circle.getBounds(), {padding: [1,1]});
        expected_label = "Map of the United Kingdom, showing an area of " + radius / 1000 + "km around the latitude " + latitude.toFixed(2)+", longitude "+longitude.toFixed(2);
        expect(document.getElementById('area-list-map').getAttribute('aria-label')).toBe(expected_label);
    });

});


describe('Easting and northing area is created on the map when easting and northing searched and radius entered', () => {
    let bleed_circle = {addTo: jest.fn(), getBounds: jest.fn().mockReturnValue({extend: jest.fn()})};
    let circle = {addTo: jest.fn(), getBounds: jest.fn().mockReturnValue({extend: jest.fn()})};
    let pinpoint = {addTo: jest.fn(), getLatLng: jest.fn().mockReturnValue([0,0])};
    test("User has entered the easting, northing and radius and then searched to generate the leaflet circle and marker on the map", () => {

        createEastingNorthingArea(L, proj4, easting, northing, radius, bleed, mapElement);
        addingFeaturesToMap(L, mymap, bleed_circle, circle, pinpoint);
        expect(bleed_circle.addTo).toHaveBeenCalledWith(mymap);
        expect(circle.addTo).toHaveBeenCalledWith(mymap);
        expect(pinpoint.addTo).toHaveBeenCalledWith(mymap);
        expect(mymap.fitBounds).toHaveBeenCalledWith(bleed_circle.getBounds(), {padding: [1,1]});
        expected_label = "Map of the United Kingdom, showing an area of "+radius/1000+"km around the easting of "+easting+", northing of "+northing;
        expect(document.getElementById('area-list-map').getAttribute('aria-label')).toBe(expected_label);
    });

});

describe('Postcode area is created on the map when postcode searched and radius entered', () => {
    let centroid = [54, -2];
    let bleed_circle = {addTo: jest.fn(), getBounds: jest.fn().mockReturnValue({extend: jest.fn()})};
    let circle = {addTo: jest.fn(), getBounds: jest.fn().mockReturnValue({extend: jest.fn()})};
    let pinpoint = {addTo: jest.fn(), getLatLng: jest.fn().mockReturnValue([0,0])};
    test("User has entered the postcode and radius and then searched to generate the leaflet circle and marker on the map", () => {
        createPostcodeArea(L, centroid, radius, bleed, postcode);
        addingFeaturesToMap(L, mymap, bleed_circle, circle, pinpoint);
        expect(bleed_circle.addTo).toHaveBeenCalledWith(mymap);
        expect(circle.addTo).toHaveBeenCalledWith(mymap);
        expect(pinpoint.addTo).toHaveBeenCalledWith(mymap);
        expect(mymap.fitBounds).toHaveBeenCalledWith(bleed_circle.getBounds(), {padding: [1,1]});
        expected_label = "Map of the United Kingdom, showing an area of " + radius / 1000 + "km around the postcode " + postcode;
        expect(document.getElementById('area-list-map').getAttribute('aria-label')).toBe(expected_label);
    });

});

describe('Pinpoint marker is added to leaflet map for postcode centroid', () => {
    centroid = [54, -2];
    test("User has entered the postcode then searched to generate the marker on the map", () => {
        addingPostcodeCentroidMarkerToMap(L, mymap, centroid);
        expect(mymap.setView).toHaveBeenCalledWith({"lat": centroid[0], "lng": centroid[1]}, 13);
        expect(mymap.addLayer).toHaveBeenCalledWith(pinpoint);
    });
});

describe('Area is added to area list', () => {
    let label = "Test label";
    test("User has added an area to the Leaflet map", () => {
        appendAreaToAreaList(label);
        expect(document.querySelector('.area-list-item').textContent).toBe(label);
    });
});
