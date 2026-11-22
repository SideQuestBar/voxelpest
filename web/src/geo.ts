// WGS84 (GPS) -> the map's grid in metres (x = column, z = row, as the scene's x and z): a quadratic fitted to pyproj's
// EPSG:4326 -> 23700 turned by THETA (scripts/aoi.py) by scripts/geo_fit.py; under 1 mm off over the map and 1 km round it.
const LON0 = 19.0535, LAT0 = 47.4985, KU = 14.023544, KV = 20.601056;
const CX = [2262.000058, 3575.632429, 0.024532, 4024.027368, -3.688433, 1.623590];
const CZ = [2534.000059, -4042.030135, -0.027701, 3559.706968, -3.261652, -1.836034];

export function wgsToGrid(lon: number, lat: number): [number, number] {
  const u = (lon - LON0) * KU, v = (lat - LAT0) * KV;
  const f = (c: number[]) => c[0] + v * (c[1] + v * c[2]) + u * (c[3] + v * c[4] + u * c[5]);
  return [f(CX), f(CZ)];
}
