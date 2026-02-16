#!/usr/bin/env python3
"""
Animação Temporal da Propagação do Fogo no OpenStreetMap
========================================================

Este script cria uma visualização animada da propagação do incêndio,
permitindo ver a evolução temporal frame a frame.

Funcionalidades:
- Play/Pause da animação
- Controle de velocidade
- Slider para navegar no tempo
- Estatísticas em tempo real

Uso:
    python scripts/animate_fire_spread.py [--data-dir PATH] [--output FILE]
"""

import argparse
import json
import math
from pathlib import Path
from typing import Optional, List, Tuple
import numpy as np


class FireAnimationGenerator:
    """Gera animação HTML da propagação do fogo."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.metadata = self._load_metadata()
        self.fire_map = self._load_fire_map()
        self.config = self.metadata.get("config", {})
        self._setup_coordinates()

    def _load_metadata(self) -> dict:
        with open(self.data_dir / "metadata.json") as f:
            return json.load(f)

    def _load_fire_map(self) -> np.ndarray:
        return np.load(self.data_dir / "fire_map.npy")

    def _setup_coordinates(self) -> None:
        op = self.config.get("operational", {})
        area = self.config.get("area", {})

        self.center_lat = op.get("latitude", -16.571175)
        self.center_lon = op.get("longitude", -49.181467)

        screen_size = area.get("screen_size", [100, 100])
        self.grid_height = screen_size[0]
        self.grid_width = screen_size[1]

        pixel_scale_ft = area.get("pixel_scale", 50)
        self.pixel_scale_m = pixel_scale_ft * 0.3048

        self.area_width_m = self.grid_width * self.pixel_scale_m
        self.area_height_m = self.grid_height * self.pixel_scale_m

        lat_rad = math.radians(abs(self.center_lat))
        self.meters_per_deg_lat = 111320
        self.meters_per_deg_lon = 111320 * math.cos(lat_rad)

        self.delta_lat = self.area_height_m / self.meters_per_deg_lat
        self.delta_lon = self.area_width_m / self.meters_per_deg_lon

        self.north_lat = self.center_lat + (self.delta_lat / 2)
        self.south_lat = self.center_lat - (self.delta_lat / 2)
        self.west_lon = self.center_lon - (self.delta_lon / 2)
        self.east_lon = self.center_lon + (self.delta_lon / 2)

    def pixel_to_latlon(self, x: int, y: int) -> Tuple[float, float]:
        lon = self.west_lon + ((x + 0.5) / self.grid_width) * self.delta_lon
        lat = self.north_lat - ((y + 0.5) / self.grid_height) * self.delta_lat
        return lat, lon

    def prepare_animation_data(self, sample_rate: int = 1) -> dict:
        """
        Prepara os dados para animação.

        Args:
            sample_rate: Pegar 1 a cada N frames (para reduzir dados)
        """
        total_frames = self.fire_map.shape[0]
        frames_data = []

        for t in range(0, total_frames, sample_rate):
            frame = self.fire_map[t]

            burning_pixels = []
            burned_pixels = []

            for y in range(self.grid_height):
                for x in range(self.grid_width):
                    status = frame[y, x]
                    if status == 1:  # Queimando
                        lat, lon = self.pixel_to_latlon(x, y)
                        burning_pixels.append([lat, lon])
                    elif status == 2:  # Queimado
                        lat, lon = self.pixel_to_latlon(x, y)
                        burned_pixels.append([lat, lon])

            frames_data.append({
                "time": t,
                "burning": burning_pixels,
                "burned_count": len(burned_pixels),
                "burning_count": len(burning_pixels)
            })

        # Para a camada de queimados, criar acumulativo
        burn_time_matrix = np.full((self.grid_height, self.grid_width), -1)
        for t in range(total_frames):
            newly_burning = (self.fire_map[t] >= 1) & (burn_time_matrix == -1)
            burn_time_matrix[newly_burning] = t

        # Criar lista de pixels queimados com seu tempo
        burned_pixels_with_time = []
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                bt = burn_time_matrix[y, x]
                if bt >= 0:
                    lat, lon = self.pixel_to_latlon(x, y)
                    burned_pixels_with_time.append({
                        "lat": lat,
                        "lon": lon,
                        "time": int(bt)
                    })

        return {
            "frames": frames_data,
            "total_frames": total_frames,
            "sample_rate": sample_rate,
            "burned_pixels": burned_pixels_with_time,
            "bounds": {
                "north": self.north_lat,
                "south": self.south_lat,
                "east": self.east_lon,
                "west": self.west_lon
            },
            "center": {
                "lat": self.center_lat,
                "lon": self.center_lon
            },
            "pixel_size": {
                "lat": self.delta_lat / self.grid_height,
                "lon": self.delta_lon / self.grid_width
            },
            "grid": {
                "width": self.grid_width,
                "height": self.grid_height
            }
        }

    def generate_html(self, output_path: Path, sample_rate: int = 2) -> None:
        """Gera o arquivo HTML com a animação."""

        print("Preparando dados da animação...")
        anim_data = self.prepare_animation_data(sample_rate)

        # Ponto inicial do fogo
        fire_pos = self.config.get("fire", {}).get(
            "fire_initial_position", {}
        ).get("static", {}).get("position", "(50, 70)")

        if isinstance(fire_pos, str):
            fire_pos = fire_pos.strip("()").split(",")
            fire_x, fire_y = int(fire_pos[0].strip()), int(fire_pos[1].strip())
        else:
            fire_x, fire_y = 50, 70

        fire_lat, fire_lon = self.pixel_to_latlon(fire_x, fire_y)

        html_content = self._generate_html_template(
            anim_data,
            fire_lat,
            fire_lon,
            fire_x,
            fire_y
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"Animação salva em: {output_path}")

    def _generate_html_template(
        self,
        anim_data: dict,
        fire_lat: float,
        fire_lon: float,
        fire_x: int,
        fire_y: int
    ) -> str:
        """Gera o template HTML completo."""

        return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Animação - Propagação de Incêndio</title>

    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />

    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />

    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1a1a2e;
            color: white;
        }}

        #map {{
            width: 100%;
            height: calc(100vh - 180px);
        }}

        .control-panel {{
            background: linear-gradient(135deg, #16213e 0%, #1a1a2e 100%);
            padding: 15px 20px;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 20px;
            border-top: 2px solid #e94560;
        }}

        .control-group {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .control-group label {{
            font-size: 12px;
            color: #a0a0a0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .btn {{
            background: #e94560;
            border: none;
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.3s ease;
        }}

        .btn:hover {{
            background: #ff6b6b;
            transform: translateY(-2px);
        }}

        .btn:active {{
            transform: translateY(0);
        }}

        .btn-secondary {{
            background: #0f3460;
        }}

        .btn-secondary:hover {{
            background: #1a4a7a;
        }}

        #timeSlider {{
            flex: 1;
            min-width: 200px;
            height: 8px;
            -webkit-appearance: none;
            background: #0f3460;
            border-radius: 4px;
            outline: none;
        }}

        #timeSlider::-webkit-slider-thumb {{
            -webkit-appearance: none;
            width: 20px;
            height: 20px;
            background: #e94560;
            border-radius: 50%;
            cursor: pointer;
            transition: all 0.2s ease;
        }}

        #timeSlider::-webkit-slider-thumb:hover {{
            transform: scale(1.2);
            background: #ff6b6b;
        }}

        #speedSelect {{
            background: #0f3460;
            border: 1px solid #e94560;
            color: white;
            padding: 8px 15px;
            border-radius: 5px;
            font-size: 14px;
            cursor: pointer;
        }}

        .stats-panel {{
            background: linear-gradient(135deg, #0f3460 0%, #16213e 100%);
            padding: 15px 20px;
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            gap: 15px;
            border-bottom: 2px solid #e94560;
        }}

        .stat-item {{
            text-align: center;
            min-width: 120px;
        }}

        .stat-value {{
            font-size: 28px;
            font-weight: bold;
            color: #e94560;
        }}

        .stat-label {{
            font-size: 11px;
            color: #a0a0a0;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 5px;
        }}

        .legend {{
            position: absolute;
            bottom: 200px;
            right: 10px;
            background: rgba(26, 26, 46, 0.95);
            padding: 15px;
            border-radius: 8px;
            z-index: 1000;
            border: 1px solid #e94560;
        }}

        .legend h4 {{
            margin-bottom: 10px;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #a0a0a0;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 5px 0;
            font-size: 12px;
        }}

        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 3px;
        }}

        .progress-bar {{
            width: 100%;
            height: 4px;
            background: #0f3460;
            position: relative;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #e94560, #ff6b6b);
            transition: width 0.1s linear;
        }}

        .time-display {{
            font-size: 24px;
            font-weight: bold;
            font-family: 'Courier New', monospace;
            color: #e94560;
            min-width: 100px;
            text-align: center;
        }}

        .title-bar {{
            background: #0f3460;
            padding: 10px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .title-bar h1 {{
            font-size: 18px;
            font-weight: 500;
        }}

        .title-bar .location {{
            font-size: 12px;
            color: #a0a0a0;
        }}
    </style>
</head>
<body>
    <div class="title-bar">
        <h1><i class="fas fa-fire"></i> Simulação de Incêndio - Parque Altamiro de Moura Pacheco</h1>
        <span class="location">
            <i class="fas fa-map-marker-alt"></i>
            {abs(self.center_lat):.4f}°S, {abs(self.center_lon):.4f}°W
        </span>
    </div>

    <div class="stats-panel">
        <div class="stat-item">
            <div class="stat-value" id="statTime">0</div>
            <div class="stat-label">Tempo (min)</div>
        </div>
        <div class="stat-item">
            <div class="stat-value" id="statBurning">0</div>
            <div class="stat-label">Queimando</div>
        </div>
        <div class="stat-item">
            <div class="stat-value" id="statBurned">0</div>
            <div class="stat-label">Queimados</div>
        </div>
        <div class="stat-item">
            <div class="stat-value" id="statArea">0.0</div>
            <div class="stat-label">Área (ha)</div>
        </div>
        <div class="stat-item">
            <div class="stat-value" id="statPercent">0.0%</div>
            <div class="stat-label">Progresso</div>
        </div>
    </div>

    <div class="progress-bar">
        <div class="progress-fill" id="progressFill"></div>
    </div>

    <div id="map"></div>

    <div class="control-panel">
        <button class="btn" id="playBtn" onclick="togglePlay()">
            <i class="fas fa-play" id="playIcon"></i>
            <span id="playText">Play</span>
        </button>

        <button class="btn btn-secondary" onclick="resetAnimation()">
            <i class="fas fa-redo"></i> Reset
        </button>

        <button class="btn btn-secondary" onclick="stepBackward()">
            <i class="fas fa-step-backward"></i>
        </button>

        <button class="btn btn-secondary" onclick="stepForward()">
            <i class="fas fa-step-forward"></i>
        </button>

        <div class="control-group">
            <label>Tempo:</label>
            <input type="range" id="timeSlider" min="0" max="{anim_data['total_frames'] - 1}" value="0"
                   oninput="seekTo(this.value)">
        </div>

        <div class="time-display" id="timeDisplay">00:00</div>

        <div class="control-group">
            <label>Velocidade:</label>
            <select id="speedSelect" onchange="changeSpeed(this.value)">
                <option value="2000">0.5x</option>
                <option value="1000">1x</option>
                <option value="500" selected>2x</option>
                <option value="250">4x</option>
                <option value="100">10x</option>
                <option value="50">20x</option>
            </select>
        </div>
    </div>

    <div class="legend">
        <h4>Legenda</h4>
        <div class="legend-item">
            <div class="legend-color" style="background: #ff4444;"></div>
            <span>Queimando agora</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #8b4513;"></div>
            <span>Já queimado</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #e94560;"></div>
            <span>Ponto inicial</span>
        </div>
    </div>

    <!-- Leaflet JS -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

    <script>
        // Dados da animação
        const animData = {json.dumps(anim_data)};
        const fireStart = {{ lat: {fire_lat}, lon: {fire_lon}, x: {fire_x}, y: {fire_y} }};

        // Configuração
        const pixelSizeLat = animData.pixel_size.lat;
        const pixelSizeLon = animData.pixel_size.lon;
        const totalFrames = animData.total_frames;
        const sampleRate = animData.sample_rate;
        const areaPerPixel = {self.pixel_scale_m ** 2 / 10000}; // hectares

        // Estado da animação
        let currentFrame = 0;
        let isPlaying = false;
        let playInterval = null;
        let speed = 500;

        // Inicializar mapa
        const map = L.map('map').setView([animData.center.lat, animData.center.lon], 15);

        // Camadas de mapa base
        const osmLayer = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap'
        }});

        const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            attribution: '© Esri'
        }});

        const topoLayer = L.tileLayer('https://{{s}}.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenTopoMap'
        }});

        // Adicionar camada padrão
        satelliteLayer.addTo(map);

        // Controle de camadas
        L.control.layers({{
            'OpenStreetMap': osmLayer,
            'Satélite': satelliteLayer,
            'Topográfico': topoLayer
        }}).addTo(map);

        // Retângulo da área simulada
        const bounds = [
            [animData.bounds.south, animData.bounds.west],
            [animData.bounds.north, animData.bounds.east]
        ];
        L.rectangle(bounds, {{
            color: '#00ff00',
            weight: 2,
            fill: false,
            dashArray: '10, 5'
        }}).addTo(map);

        // Marcador do ponto inicial
        const fireIcon = L.divIcon({{
            html: '<i class="fas fa-fire" style="color: #e94560; font-size: 24px; text-shadow: 0 0 10px #ff0000;"></i>',
            iconSize: [24, 24],
            iconAnchor: [12, 24],
            className: 'fire-icon'
        }});

        L.marker([fireStart.lat, fireStart.lon], {{ icon: fireIcon }})
            .bindPopup(`<b>Início do Fogo</b><br>Pixel: (${{fireStart.x}}, ${{fireStart.y}})<br>Lat: ${{fireStart.lat.toFixed(6)}}<br>Lon: ${{fireStart.lon.toFixed(6)}}`)
            .addTo(map);

        // Camadas para fogo
        let burningLayer = L.layerGroup().addTo(map);
        let burnedLayer = L.layerGroup().addTo(map);

        // Pré-processar pixels queimados por tempo
        const burnedByTime = {{}};
        animData.burned_pixels.forEach(p => {{
            const t = Math.floor(p.time / sampleRate) * sampleRate;
            if (!burnedByTime[t]) burnedByTime[t] = [];
            burnedByTime[t].push(p);
        }});

        // Criar retângulo para um pixel
        function createPixelRect(lat, lon, color, opacity) {{
            const halfLat = pixelSizeLat / 2;
            const halfLon = pixelSizeLon / 2;
            return L.rectangle([
                [lat - halfLat, lon - halfLon],
                [lat + halfLat, lon + halfLon]
            ], {{
                color: color,
                weight: 0,
                fillColor: color,
                fillOpacity: opacity
            }});
        }}

        // Cache de retângulos queimados
        const burnedRects = [];
        let lastBurnedFrame = -1;

        // Atualizar visualização
        function updateVisualization() {{
            const frameIndex = Math.floor(currentFrame / sampleRate);
            const frame = animData.frames[Math.min(frameIndex, animData.frames.length - 1)];

            // Limpar camada de queimando
            burningLayer.clearLayers();

            // Adicionar pixels queimando (vermelho brilhante)
            frame.burning.forEach(([lat, lon]) => {{
                createPixelRect(lat, lon, '#ff4444', 0.9).addTo(burningLayer);
            }});

            // Adicionar novos pixels queimados (marrom)
            for (let t = (lastBurnedFrame + 1) * sampleRate; t <= currentFrame; t += sampleRate) {{
                const pixels = burnedByTime[t] || [];
                pixels.forEach(p => {{
                    const rect = createPixelRect(p.lat, p.lon, '#8b4513', 0.6);
                    rect.addTo(burnedLayer);
                    burnedRects.push({{ time: t, rect: rect }});
                }});
            }}
            lastBurnedFrame = frameIndex;

            // Atualizar estatísticas
            updateStats(frame);
        }}

        // Atualizar estatísticas
        function updateStats(frame) {{
            const burnedCount = burnedRects.length;
            const burningCount = frame.burning.length;
            const totalPixels = animData.grid.width * animData.grid.height;
            const areaHa = burnedCount * areaPerPixel;
            const percent = (burnedCount / totalPixels * 100).toFixed(1);

            document.getElementById('statTime').textContent = currentFrame;
            document.getElementById('statBurning').textContent = burningCount;
            document.getElementById('statBurned').textContent = burnedCount;
            document.getElementById('statArea').textContent = areaHa.toFixed(1);
            document.getElementById('statPercent').textContent = percent + '%';

            // Atualizar barra de progresso
            const progress = (currentFrame / totalFrames * 100);
            document.getElementById('progressFill').style.width = progress + '%';

            // Atualizar display de tempo
            const minutes = currentFrame;
            const hours = Math.floor(minutes / 60);
            const mins = minutes % 60;
            document.getElementById('timeDisplay').textContent =
                String(hours).padStart(2, '0') + ':' + String(mins).padStart(2, '0');

            // Atualizar slider
            document.getElementById('timeSlider').value = currentFrame;
        }}

        // Controles de reprodução
        function togglePlay() {{
            isPlaying = !isPlaying;

            const icon = document.getElementById('playIcon');
            const text = document.getElementById('playText');

            if (isPlaying) {{
                icon.className = 'fas fa-pause';
                text.textContent = 'Pause';
                startPlayback();
            }} else {{
                icon.className = 'fas fa-play';
                text.textContent = 'Play';
                stopPlayback();
            }}
        }}

        function startPlayback() {{
            if (playInterval) clearInterval(playInterval);
            playInterval = setInterval(() => {{
                if (currentFrame >= totalFrames - 1) {{
                    togglePlay();
                    return;
                }}
                currentFrame += sampleRate;
                updateVisualization();
            }}, speed);
        }}

        function stopPlayback() {{
            if (playInterval) {{
                clearInterval(playInterval);
                playInterval = null;
            }}
        }}

        function resetAnimation() {{
            stopPlayback();
            isPlaying = false;
            document.getElementById('playIcon').className = 'fas fa-play';
            document.getElementById('playText').textContent = 'Play';

            currentFrame = 0;
            lastBurnedFrame = -1;
            burnedLayer.clearLayers();
            burnedRects.length = 0;
            updateVisualization();
        }}

        function seekTo(frame) {{
            frame = parseInt(frame);

            if (frame < currentFrame) {{
                // Voltar no tempo - precisa reconstruir
                lastBurnedFrame = -1;
                burnedLayer.clearLayers();
                burnedRects.length = 0;
            }}

            currentFrame = frame;
            updateVisualization();
        }}

        function stepForward() {{
            if (currentFrame < totalFrames - 1) {{
                currentFrame += sampleRate;
                updateVisualization();
            }}
        }}

        function stepBackward() {{
            if (currentFrame > 0) {{
                seekTo(Math.max(0, currentFrame - sampleRate));
            }}
        }}

        function changeSpeed(newSpeed) {{
            speed = parseInt(newSpeed);
            if (isPlaying) {{
                stopPlayback();
                startPlayback();
            }}
        }}

        // Inicializar
        updateVisualization();
    </script>
</body>
</html>'''


def find_latest_simulation(base_dir: Path) -> Optional[Path]:
    """Encontra o diretório da simulação mais recente."""
    data_dir = base_dir / "data"
    if not data_dir.exists():
        return None

    sim_dirs = sorted(data_dir.iterdir(), reverse=True)
    for d in sim_dirs:
        if d.is_dir() and (d / "fire_map.npy").exists():
            return d
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Gera animação temporal da propagação do fogo"
    )
    parser.add_argument("--data-dir", type=str, help="Diretório com os dados")
    parser.add_argument(
        "--output",
        type=str,
        default="fire_animation.html",
        help="Arquivo HTML de saída"
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=2,
        help="Taxa de amostragem (1 = todos os frames, 2 = metade, etc)"
    )

    args = parser.parse_args()

    # Encontrar dados
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        base_dir = Path.home() / ".simfire" / "parque_altamiro"
        data_dir = find_latest_simulation(base_dir)
        if data_dir is None:
            print("Erro: Nenhuma simulação encontrada.")
            return

    print(f"Carregando dados de: {data_dir}")

    generator = FireAnimationGenerator(data_dir)
    output_path = Path(args.output)
    generator.generate_html(output_path, args.sample_rate)

    print()
    print("=" * 50)
    print("ANIMAÇÃO GERADA COM SUCESSO!")
    print("=" * 50)
    print(f"Arquivo: {output_path.absolute()}")
    print()
    print("Funcionalidades:")
    print("  - Play/Pause da animação")
    print("  - Controle de velocidade (0.5x a 20x)")
    print("  - Slider para navegar no tempo")
    print("  - Estatísticas em tempo real")
    print("  - Camadas de mapa (OSM, Satélite, Topo)")
    print()
    print("Abra o arquivo HTML em um navegador para visualizar.")


if __name__ == "__main__":
    main()
