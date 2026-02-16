#!/usr/bin/env python3
"""
Visualizador de Simulação de Incêndio no OpenStreetMap
======================================================

Este script carrega os resultados de uma simulação do SimFire e
plota em um mapa interativo usando OpenStreetMap (via Folium).

Funcionalidades:
- Degradê de cores baseado no tempo de queima
- Mapa interativo com zoom e pan
- Camadas para diferentes visualizações
- Exportação para HTML

Uso:
    python scripts/visualize_openstreetmap.py [--data-dir PATH] [--output FILE]
"""

import argparse
import json
import math
from pathlib import Path
from typing import Tuple, Optional
import numpy as np

try:
    import folium
    from folium import plugins
except ImportError:
    print("Erro: folium não está instalado.")
    print("Instale com: pip install folium")
    exit(1)


class FireSimulationVisualizer:
    """Classe para visualizar simulações de incêndio no OpenStreetMap."""

    def __init__(self, data_dir: Path):
        """
        Inicializa o visualizador com os dados de uma simulação.

        Args:
            data_dir: Diretório contendo os arquivos .npy e metadata.json
        """
        self.data_dir = Path(data_dir)
        self.metadata = self._load_metadata()
        self.fire_map = self._load_fire_map()
        self.burn_time_matrix = self._compute_burn_time_matrix()

        # Extrair configurações
        self.config = self.metadata.get("config", {})
        self._setup_coordinates()

    def _load_metadata(self) -> dict:
        """Carrega o arquivo metadata.json."""
        metadata_path = self.data_dir / "metadata.json"
        if not metadata_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {metadata_path}")
        with open(metadata_path) as f:
            return json.load(f)

    def _load_fire_map(self) -> np.ndarray:
        """Carrega a matriz fire_map.npy."""
        fire_map_path = self.data_dir / "fire_map.npy"
        if not fire_map_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {fire_map_path}")
        return np.load(fire_map_path)

    def _compute_burn_time_matrix(self) -> np.ndarray:
        """
        Computa a matriz de tempo de queima.

        Cada pixel recebe o valor do frame em que começou a queimar.
        Pixels não queimados recebem -1.
        """
        final_shape = self.fire_map.shape[1:]  # (height, width)
        burn_time = np.full(final_shape, -1, dtype=np.int32)

        for t in range(self.fire_map.shape[0]):
            # Marca o tempo em que cada pixel começou a queimar
            newly_burning = (self.fire_map[t] >= 1) & (burn_time == -1)
            burn_time[newly_burning] = t

        return burn_time

    def _setup_coordinates(self) -> None:
        """Configura o sistema de coordenadas geográficas."""
        op = self.config.get("operational", {})
        area = self.config.get("area", {})

        # Coordenada central
        self.center_lat = op.get("latitude", -16.571175)
        self.center_lon = op.get("longitude", -49.181467)

        # Tamanho da grade
        screen_size = area.get("screen_size", [100, 100])
        self.grid_height = screen_size[0]
        self.grid_width = screen_size[1]

        # Escala (pés por pixel -> metros por pixel)
        pixel_scale_ft = area.get("pixel_scale", 50)
        self.pixel_scale_m = pixel_scale_ft * 0.3048

        # Dimensões totais em metros
        self.area_width_m = self.grid_width * self.pixel_scale_m
        self.area_height_m = self.grid_height * self.pixel_scale_m

        # Conversão para graus
        lat_rad = math.radians(abs(self.center_lat))
        self.meters_per_deg_lat = 111320
        self.meters_per_deg_lon = 111320 * math.cos(lat_rad)

        self.delta_lat = self.area_height_m / self.meters_per_deg_lat
        self.delta_lon = self.area_width_m / self.meters_per_deg_lon

        # Limites da área
        self.north_lat = self.center_lat + (self.delta_lat / 2)
        self.south_lat = self.center_lat - (self.delta_lat / 2)
        self.west_lon = self.center_lon - (self.delta_lon / 2)
        self.east_lon = self.center_lon + (self.delta_lon / 2)

    def pixel_to_latlon(self, x: int, y: int) -> Tuple[float, float]:
        """
        Converte coordenadas de pixel para lat/lon.

        Args:
            x: Coluna (0 = oeste, max = leste)
            y: Linha (0 = norte, max = sul)

        Returns:
            Tupla (latitude, longitude)
        """
        lon = self.west_lon + (x / self.grid_width) * self.delta_lon
        lat = self.north_lat - (y / self.grid_height) * self.delta_lat
        return lat, lon

    def get_pixel_bounds(self, x: int, y: int) -> list:
        """
        Retorna os limites de um pixel como [[south, west], [north, east]].

        Args:
            x: Coluna do pixel
            y: Linha do pixel

        Returns:
            Lista com os bounds do pixel
        """
        # Canto noroeste do pixel
        nw_lat, nw_lon = self.pixel_to_latlon(x, y)
        # Canto sudeste do pixel
        se_lat, se_lon = self.pixel_to_latlon(x + 1, y + 1)

        return [[se_lat, nw_lon], [nw_lat, se_lon]]

    def time_to_color(
        self,
        burn_time: int,
        max_time: int,
        colormap: str = "YlOrRd"
    ) -> str:
        """
        Converte tempo de queima para cor em formato hex.

        Args:
            burn_time: Tempo em que o pixel queimou
            max_time: Tempo máximo da simulação
            colormap: Nome do colormap ('YlOrRd', 'Reds', 'OrRd', 'inferno')

        Returns:
            Cor em formato hexadecimal (#RRGGBB)
        """
        if burn_time < 0:
            return None  # Não queimado

        # Normaliza o tempo (0 = início, 1 = fim)
        t = burn_time / max_time if max_time > 0 else 0

        # Colormaps personalizados (do mais recente ao mais antigo)
        if colormap == "YlOrRd":
            # Amarelo -> Laranja -> Vermelho
            if t < 0.5:
                # Amarelo para Laranja
                r = 255
                g = int(255 - (255 - 165) * (t * 2))
                b = int(200 * (1 - t * 2))
            else:
                # Laranja para Vermelho escuro
                r = int(255 - (255 - 139) * ((t - 0.5) * 2))
                g = int(165 * (1 - (t - 0.5) * 2))
                b = 0
        elif colormap == "inferno":
            # Preto -> Roxo -> Vermelho -> Laranja -> Amarelo
            if t < 0.25:
                r, g, b = int(t * 4 * 120), 0, int(t * 4 * 150)
            elif t < 0.5:
                r = int(120 + (255 - 120) * ((t - 0.25) * 4))
                g = int((t - 0.25) * 4 * 100)
                b = int(150 * (1 - (t - 0.25) * 4))
            elif t < 0.75:
                r = 255
                g = int(100 + (200 - 100) * ((t - 0.5) * 4))
                b = 0
            else:
                r = 255
                g = int(200 + (255 - 200) * ((t - 0.75) * 4))
                b = int((t - 0.75) * 4 * 150)
        else:
            # Vermelho simples (mais escuro = mais antigo)
            intensity = 1 - t  # Inverte para que início seja mais intenso
            r = int(139 + (255 - 139) * intensity)
            g = int(69 * (1 - intensity))
            b = int(19 * (1 - intensity))

        return f"#{r:02x}{g:02x}{b:02x}"

    def create_map(
        self,
        colormap: str = "YlOrRd",
        opacity: float = 0.7,
        show_grid: bool = False,
        show_fire_start: bool = True,
        tiles: str = "OpenStreetMap"
    ) -> folium.Map:
        """
        Cria um mapa Folium com a visualização do incêndio.

        Args:
            colormap: Esquema de cores ('YlOrRd', 'Reds', 'inferno')
            opacity: Opacidade das células (0-1)
            show_grid: Mostrar grade de pixels
            show_fire_start: Mostrar marcador do ponto inicial
            tiles: Tipo de mapa base

        Returns:
            Objeto folium.Map
        """
        # Criar mapa centrado na área
        m = folium.Map(
            location=[self.center_lat, self.center_lon],
            zoom_start=15,
            tiles=tiles
        )

        # Adicionar diferentes camadas de mapa base
        folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)
        folium.TileLayer(
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri",
            name="Satélite (Esri)"
        ).add_to(m)
        folium.TileLayer(
            "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
            attr="OpenTopoMap",
            name="Topográfico"
        ).add_to(m)

        # Camada para área queimada
        fire_layer = folium.FeatureGroup(name="Área Queimada")

        # Obter tempo máximo
        max_time = self.burn_time_matrix.max()

        # Adicionar cada pixel queimado como um retângulo
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                burn_time = self.burn_time_matrix[y, x]
                if burn_time >= 0:  # Pixel queimou
                    color = self.time_to_color(burn_time, max_time, colormap)
                    bounds = self.get_pixel_bounds(x, y)

                    # Tooltip com informações
                    tooltip = f"Pixel ({x}, {y})<br>Queimou no frame {burn_time}<br>Tempo: {burn_time} min"

                    folium.Rectangle(
                        bounds=bounds,
                        color=color,
                        fill=True,
                        fill_color=color,
                        fill_opacity=opacity,
                        weight=0.5 if show_grid else 0,
                        tooltip=tooltip
                    ).add_to(fire_layer)

        fire_layer.add_to(m)

        # Adicionar marcador do ponto inicial do fogo
        if show_fire_start:
            fire_pos = self.config.get("fire", {}).get(
                "fire_initial_position", {}
            ).get("static", {}).get("position", "(50, 70)")

            # Parse da posição
            if isinstance(fire_pos, str):
                fire_pos = fire_pos.strip("()").split(",")
                fire_x, fire_y = int(fire_pos[0]), int(fire_pos[1])
            else:
                fire_x, fire_y = 50, 70

            fire_lat, fire_lon = self.pixel_to_latlon(fire_x, fire_y)

            folium.Marker(
                location=[fire_lat, fire_lon],
                popup=f"Início do Fogo<br>Pixel: ({fire_x}, {fire_y})<br>Lat: {fire_lat:.6f}<br>Lon: {fire_lon:.6f}",
                icon=folium.Icon(color="red", icon="fire", prefix="fa"),
                tooltip="Ponto inicial do incêndio"
            ).add_to(m)

        # Adicionar contorno da área simulada
        area_layer = folium.FeatureGroup(name="Área Simulada")
        folium.Rectangle(
            bounds=[[self.south_lat, self.west_lon], [self.north_lat, self.east_lon]],
            color="blue",
            fill=False,
            weight=2,
            dash_array="5, 5",
            tooltip="Área da simulação"
        ).add_to(area_layer)
        area_layer.add_to(m)

        # Adicionar legenda
        legend_html = self._create_legend_html(colormap, max_time)
        m.get_root().html.add_child(folium.Element(legend_html))

        # Adicionar controle de camadas
        folium.LayerControl().add_to(m)

        # Adicionar ferramentas
        plugins.Fullscreen().add_to(m)
        plugins.MeasureControl(position="topleft").add_to(m)

        # Adicionar mini mapa
        minimap = plugins.MiniMap(toggle_display=True)
        m.add_child(minimap)

        return m

    def _create_legend_html(self, colormap: str, max_time: int) -> str:
        """Cria HTML para a legenda do mapa."""
        # Gerar cores da legenda
        colors = []
        for i in range(6):
            t = int(i * max_time / 5)
            color = self.time_to_color(t, max_time, colormap)
            colors.append((t, color))

        gradient_stops = ", ".join([f"{c[1]} {i*20}%" for i, c in enumerate(colors)])

        return f"""
        <div style="
            position: fixed;
            bottom: 50px;
            left: 50px;
            z-index: 1000;
            background-color: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0,0,0,0.3);
            font-family: Arial, sans-serif;
            font-size: 12px;
        ">
            <h4 style="margin: 0 0 10px 0;">Tempo de Queima</h4>
            <div style="
                width: 150px;
                height: 20px;
                background: linear-gradient(to right, {gradient_stops});
                border: 1px solid #ccc;
            "></div>
            <div style="display: flex; justify-content: space-between; margin-top: 5px;">
                <span>0 min</span>
                <span>{max_time} min</span>
            </div>
            <div style="margin-top: 10px; font-size: 10px; color: #666;">
                Cores mais quentes = queimou primeiro<br>
                Cores mais frias = queimou depois
            </div>
        </div>
        """

    def create_animation_data(self) -> dict:
        """
        Prepara dados para animação temporal.

        Returns:
            Dicionário com dados para cada frame
        """
        frames = []
        for t in range(self.fire_map.shape[0]):
            frame_data = {
                "time": t,
                "burning": [],
                "burned": []
            }

            for y in range(self.grid_height):
                for x in range(self.grid_width):
                    status = self.fire_map[t, y, x]
                    lat, lon = self.pixel_to_latlon(x, y)

                    if status == 1:  # Queimando
                        frame_data["burning"].append([lat, lon])
                    elif status == 2:  # Queimado
                        frame_data["burned"].append([lat, lon])

            frames.append(frame_data)

        return {"frames": frames, "total_frames": len(frames)}

    def get_statistics(self) -> dict:
        """Retorna estatísticas da simulação."""
        last_frame = self.fire_map[-1]

        burned_pixels = (last_frame == 2).sum()
        total_pixels = last_frame.size
        area_per_pixel = (self.pixel_scale_m ** 2) / 10000  # hectares

        return {
            "total_pixels": int(total_pixels),
            "burned_pixels": int(burned_pixels),
            "burned_percentage": float(burned_pixels / total_pixels * 100),
            "area_total_ha": float(total_pixels * area_per_pixel),
            "area_burned_ha": float(burned_pixels * area_per_pixel),
            "simulation_frames": int(self.fire_map.shape[0]),
            "max_burn_time": int(self.burn_time_matrix.max()),
            "bounds": {
                "north": self.north_lat,
                "south": self.south_lat,
                "east": self.east_lon,
                "west": self.west_lon
            }
        }


def find_latest_simulation(base_dir: Path) -> Optional[Path]:
    """Encontra o diretório da simulação mais recente."""
    data_dir = base_dir / "data"
    if not data_dir.exists():
        return None

    # Lista diretórios ordenados por nome (que contém timestamp)
    sim_dirs = sorted(data_dir.iterdir(), reverse=True)
    for d in sim_dirs:
        if d.is_dir() and (d / "fire_map.npy").exists():
            return d

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Visualiza simulação de incêndio no OpenStreetMap"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Diretório com os dados da simulação (fire_map.npy, metadata.json)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="fire_simulation_map.html",
        help="Arquivo HTML de saída (padrão: fire_simulation_map.html)"
    )
    parser.add_argument(
        "--colormap",
        type=str,
        default="YlOrRd",
        choices=["YlOrRd", "Reds", "inferno"],
        help="Esquema de cores (padrão: YlOrRd)"
    )
    parser.add_argument(
        "--opacity",
        type=float,
        default=0.7,
        help="Opacidade das células (0-1, padrão: 0.7)"
    )
    parser.add_argument(
        "--show-grid",
        action="store_true",
        help="Mostrar bordas da grade de pixels"
    )

    args = parser.parse_args()

    # Encontrar diretório de dados
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        # Tentar encontrar automaticamente
        base_dir = Path.home() / ".simfire" / "parque_altamiro"
        data_dir = find_latest_simulation(base_dir)
        if data_dir is None:
            print("Erro: Nenhuma simulação encontrada.")
            print("Execute primeiro: python scripts/run_mvp_parque_altamiro.py")
            return

    print(f"Carregando dados de: {data_dir}")

    # Criar visualizador
    viz = FireSimulationVisualizer(data_dir)

    # Exibir estatísticas
    stats = viz.get_statistics()
    print()
    print("=" * 50)
    print("ESTATÍSTICAS DA SIMULAÇÃO")
    print("=" * 50)
    print(f"Frames simulados: {stats['simulation_frames']}")
    print(f"Área total: {stats['area_total_ha']:.1f} ha")
    print(f"Área queimada: {stats['area_burned_ha']:.1f} ha ({stats['burned_percentage']:.1f}%)")
    print(f"Tempo máximo de queima: {stats['max_burn_time']} min")
    print()
    print("Limites geográficos:")
    print(f"  Norte: {stats['bounds']['north']:.6f}")
    print(f"  Sul:   {stats['bounds']['south']:.6f}")
    print(f"  Leste: {stats['bounds']['east']:.6f}")
    print(f"  Oeste: {stats['bounds']['west']:.6f}")
    print()

    # Criar mapa
    print("Gerando mapa interativo...")
    m = viz.create_map(
        colormap=args.colormap,
        opacity=args.opacity,
        show_grid=args.show_grid
    )

    # Salvar
    output_path = Path(args.output)
    m.save(str(output_path))
    print(f"Mapa salvo em: {output_path.absolute()}")
    print()
    print("Abra o arquivo HTML em um navegador para visualizar.")


if __name__ == "__main__":
    main()
