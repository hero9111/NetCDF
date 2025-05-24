# oceanocal_v2/handlers/overlay_handler.py

import plotly.graph_objs as go
import os
import json
import logging

def get_overlay_traces(filename):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(BASE_DIR, "resources", "overlays", filename)
    traces = []

    if not os.path.exists(path):
        logging.warning(f"오버레이 파일이 존재하지 않습니다: {path}")
        return []

    try:
        # (1) GeoJSON 지원
        if filename.lower().endswith((".geojson", ".json")):
            with open(path, "r", encoding="utf-8") as f:
                geo = json.load(f)
                for feat in geo["features"]:
                    coords = feat["geometry"]["coordinates"]
                    prop = feat.get("properties", {})
                    feat_type = feat["geometry"]["type"]

                    if feat_type == "Polygon":
                        for poly in coords:
                            # For simple polygons, coords is [exterior_ring, interior_ring1, ...]
                            # We only plot the exterior ring for now.
                            lons, lats = zip(*poly[0])
                            traces.append(go.Scattergeo(
                                lon=list(lons), lat=list(lats), mode="lines", line=dict(width=1, color="black"),
                                name=prop.get("name", filename), hoverinfo="text",
                                text=f"{prop.get('name', '')}"
                            ))
                    elif feat_type == "MultiPolygon":
                        for multi_poly in coords:
                            for poly in multi_poly:
                                lons, lats = zip(*poly[0])
                                traces.append(go.Scattergeo(
                                    lon=list(lons), lat=list(lats), mode="lines", line=dict(width=1, color="black"),
                                    name=prop.get("name", filename), hoverinfo="text",
                                    text=f"{prop.get('name', '')}"
                                ))
                    elif feat_type == "LineString":
                        lons, lats = zip(*coords)
                        traces.append(go.Scattergeo(
                            lon=list(lons), lat=list(lats), mode="lines", line=dict(width=1, color="blue"),
                            name=prop.get("name", filename), hoverinfo="text",
                            text=f"{prop.get('name', '')}"
                        ))
                    elif feat_type == "MultiLineString":
                        for line_str in coords:
                            lons, lats = zip(*line_str)
                            traces.append(go.Scattergeo(
                                lon=list(lons), lat=list(lats), mode="lines", line=dict(width=1, color="blue"),
                                name=prop.get("name", filename), hoverinfo="text",
                                text=f"{prop.get('name', '')}"
                            ))
            logging.info(f"GeoJSON 오버레이 로드됨: {filename}")
            return traces

        # (2) CSV/ASCII(위도,경도) 지원
        elif filename.lower().endswith((".txt", ".csv")):
            with open(path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(",")
                    if len(parts) % 2 != 0:
                        logging.warning(f"오버레이 파일 '{filename}'의 {i+1}번째 줄이 유효하지 않습니다 (홀수 개수).")
                        continue
                    lats, lons = [], []
                    for j in range(0, len(parts), 2):
                        try:
                            lats.append(float(parts[j]))
                            lons.append(float(parts[j+1]))
                        except ValueError:
                            logging.warning(f"오버레이 파일 '{filename}'의 {i+1}번째 줄에서 숫자 변환 오류 발생.")
                            continue
                    if lats and lons:
                        traces.append(go.Scattergeo(
                            lat=lats, lon=lons, mode="lines",
                            line=dict(width=1, color="green"), # Default color for CSV lines
                            name=f"{filename}_line_{i+1}", hoverinfo="text",
                            text=f"Overlay Line {i+1}"
                        ))
            logging.info(f"CSV/ASCII 오버레이 로드됨: {filename}")
            return traces

        else:
            logging.warning(f"지원되지 않는 오버레이 파일 형식: {filename}")
            return []

    except Exception as e:
        logging.error(f"오버레이 파일 '{filename}'을 로드하는 중 오류 발생: {e}", exc_info=True)
        return []