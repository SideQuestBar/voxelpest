// WGS84 (GPS) -> the map's grid in metres (x = column, z = row, as the scene's x and z): a quadratic fitted to pyproj's
// EPSG:4326 -> 23700 turned by THETA (scripts/aoi.py) by scripts/geo_fit.py; under 1 mm off over the map and 1 km round it.
const LON0 = 19.0535, LAT0 = 47.4985, KU = 16.12876, KV = 23.901815;
const CX = [1750.000053, 3081.849816, 0.018357, 3498.788897, -2.763999, 1.227331];
const CZ = [2534.000006, -3483.839591, -0.020725, 3095.074086, -2.444447, -1.387775];

export function wgsToGrid(lon: number, lat: number): [number, number] {
  const u = (lon - LON0) * KU, v = (lat - LAT0) * KV;
  const f = (c: number[]) => c[0] + v * (c[1] + v * c[2]) + u * (c[3] + v * c[4] + u * c[5]);
  return [f(CX), f(CZ)];
}
