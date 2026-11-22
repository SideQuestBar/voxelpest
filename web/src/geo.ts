// WGS84 (GPS) -> the map's grid in metres (x = column, z = row, as the scene's x and z): a quadratic fitted to pyproj's
// EPSG:4326 -> 23700 turned by THETA (scripts/aoi.py) by scripts/geo_fit.py; under 1 mm off over the map and 1 km round it.
const LON0 = 19.0535, LAT0 = 47.4985, KU = 11.542062, KV = 17.102235;
const CX = [4565.999950, 4307.144593, 0.035193, 4889.171556, -5.397766, 2.397507];
const CZ = [2534.000139, -4868.959155, -0.039727, 4325.024885, -4.774131, -2.710688];

export function wgsToGrid(lon: number, lat: number): [number, number] {
  const u = (lon - LON0) * KU, v = (lat - LAT0) * KV;
  const f = (c: number[]) => c[0] + v * (c[1] + v * c[2]) + u * (c[3] + v * c[4] + u * c[5]);
  return [f(CX), f(CZ)];
}
