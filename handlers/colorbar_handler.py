# oceanocal_v2/handlers/colorbar_handler.py

import os

def get_colormap(name):
    # Panoply .pal 파일을 Plotly colorscale로 변환 (예시)
    # resources/colorbars 디렉토리를 기준으로 경로 설정
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(BASE_DIR, "resources", "colorbars", name)
    if not path.endswith('.pal'):
        path += ".pal"
    colors = []
    try:
        with open(path, "r") as f:
            for line in f:
                if line.startswith("#") or not line.strip(): continue
                parts = line.strip().split()
                if len(parts) == 3:
                    r, g, b = [int(x) for x in parts]
                    hexcol = '#%02x%02x%02x' % (r, g, b)
                    colors.append(hexcol)
    except Exception as e:
        #logging.warning(f"컬러맵 '{name}' 로드 실패: {e}. 기본 컬러맵 사용.", exc_info=True)
        colors = ['#0000ff', '#00ff00', '#ff0000']  # fallback
    # Plotly colorscale: list of (fraction, color)
    if not colors:
        colors = ['#0000ff', '#00ff00', '#ff0000'] # Ensure fallback if file is empty
    return [(i/(len(colors)-1), color) for i, color in enumerate(colors)]