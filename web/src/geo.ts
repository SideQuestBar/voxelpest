// WGS84 (GPS) -> the map's grid in metres (x = column, z = row, as the scene's x and z): a quadratic fitted to pyproj's
// EPSG:4326 -> 23700 turned by THETA (scripts/aoi.py) by scripts/geo_fit.py; under 1 mm off over the map and 1 km round it.
const LON0 = 19.0535, LAT0 = 47.4985, KU = 10.671693, KV = 15.762486;
const CX = [5077.999900, 4673.234799, 0.041522, 5287.925804, -6.333709, 2.804713];
const CZ = [3558.000089, -5282.801367, -0.046860, 4677.767911, -5.602952, -3.170514];

export function wgsToGrid(lon: number, lat: number): [number, number] {
  const u = (lon - LON0) * KU, v = (lat - LAT0) * KV;
  const f = (c: number[]) => c[0] + v * (c[1] + v * c[2]) + u * (c[3] + v * c[4] + u * c[5]);
  return [f(CX), f(CZ)];
}
