import plotly.graph_objs as go
import plotly.io as pio
import numpy as np

z = np.random.rand(3, 774)
fig = go.Figure(go.Heatmap(z=z))
html = pio.to_html(fig, full_html=False)
with open("test_plot.html", "w", encoding="utf-8") as f:
    f.write(html)
