#!/usr/bin/env python3
"""
Exporta dados da simulação para GeoJSON
=======================================

Este script exporta a matriz de propagação do fogo para formato GeoJSON,
permitindo uso em qualquer plataforma de mapas (QGIS, Leaflet, Mapbox, etc).

Uso:
    python scripts/export_geojson.py [--data-dir PATH] [--output FILE]
"""

import argparse
import json
import math
from pathlib import Path
from typing import Optional
import numpy as np


def pixel_to_polygon(x: int, y: int, config: dict) -> list:
    """
    Converte um pixel para um polígono GeoJSON.

    Returns:
        Lista de coordenadas [[[lon, lat], ...]] no formato GeoJSON
    """
    # Extrair configuração
    center_lat = config["operational"]["latitude"]
    center_lon = config["operational"]["longitude"]
    screen_size = config["area"]["screen_size"]
    pixel_scale_ft = config["area"]["pixel_scale"]

    grid_height, grid_width = screen_size
    pixel_scale_m = pixel_scale_ft * 0.3048

    # Calcular extensões
    area_width_m = grid_width * pixel_scale_m
    area_height_m = grid_height * pixel_scale_m

    lat_rad = math.radians(abs(center_lat))
    meters_per_deg_lat = 111320
    meters_per_deg_lon = 111320 * math.cos(lat_rad)

    delta_lat = area_height_m / meters_per_deg_lat
    delta_lon = area_width_m / meters_per_deg_lon

    # Limites
    north_lat = center_lat + (delta_lat / 2)
    west_lon = center_lon - (delta_lon / 2)

    # Tamanho de cada pixel em graus
    pixel_lat = delta_lat / grid_height
    pixel_lon = delta_lon / grid_width

    # Cantos do pixel
    nw_lat = north_lat - (y * pixel_lat)
    nw_lon = west_lon + (x * pixel_lon)
    se_lat = nw_lat - pixel_lat
    se_lon = nw_lon + pixel_lon

    # Polígono no formato GeoJSON (lon, lat)
    return [[[nw_lon, nw_lat], [se_lon, nw_lat], [se_lon, se_lat], [nw_lon, se_lat], [nw_lon, nw_lat]]]


def time_to_color_rgb(burn_time: int, max_time: int) -> tuple:
    """Converte tempo de queima para cor RGB."""
    if burn_time < 0 or max_time <= 0:
        return (128, 128, 128)  # Cinza para não queimado

    t = burn_time / max_time

    # Degradê: Vermelho escuro -> Laranja -> Amarelo
    if t < 0.5:
        r = 255
        g = int(255 * (t * 2))
        b = 0
    else:
        r = 255
        g = 255
        b = int(255 * ((t - 0.5) * 2))

    return (r, g, b)


def export_to_geojson(data_dir: Path, output_path: Path, simplify: bool = False):
    """
    Exporta os dados da simulação para GeoJSON.

    Args:
        data_dir: Diretório com fire_map.npy e metadata.json
        output_path: Caminho do arquivo GeoJSON de saída
        simplify: Se True, agrupa pixels adjacentes (reduz tamanho)
    """
    # Carregar dados
    with open(data_dir / "metadata.json") as f:
        metadata = json.load(f)

    fire_map = np.load(data_dir / "fire_map.npy")
    config = metadata["config"]

    # Calcular matriz de tempo de queima
    grid_height, grid_width = fire_map.shape[1], fire_map.shape[2]
    burn_time = np.full((grid_height, grid_width), -1, dtype=np.int32)

    for t in range(fire_map.shape[0]):
        newly_burning = (fire_map[t] >= 1) & (burn_time == -1)
        burn_time[newly_burning] = t

    max_time = burn_time.max()

    # Criar features GeoJSON
    features = []

    for y in range(grid_height):
        for x in range(grid_width):
            bt = burn_time[y, x]
            if bt >= 0:  # Pixel queimou
                r, g, b = time_to_color_rgb(bt, max_time)

                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": pixel_to_polygon(x, y, config)
                    },
                    "properties": {
                        "pixel_x": x,
                        "pixel_y": y,
                        "burn_time": int(bt),
                        "burn_time_normalized": float(bt / max_time) if max_time > 0 else 0,
                        "color_rgb": [r, g, b],
                        "color_hex": f"#{r:02x}{g:02x}{b:02x}"
                    }
                }
                features.append(feature)

    # Criar GeoJSON completo
    geojson = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}
        },
        "metadata": {
            "simulation_frames": fire_map.shape[0],
            "max_burn_time": int(max_time),
            "total_pixels": grid_height * grid_width,
            "burned_pixels": len(features),
            "center_lat": config["operational"]["latitude"],
            "center_lon": config["operational"]["longitude"]
        },
        "features": features
    }

    # Salvar
    with open(output_path, "w") as f:
        json.dump(geojson, f)

    print(f"GeoJSON exportado: {output_path}")
    print(f"  Features: {len(features)}")
    print(f"  Tamanho: {output_path.stat().st_size / 1024:.1f} KB")


def export_burn_time_matrix(data_dir: Path, output_path: Path):
    """Exporta a matriz de tempo de queima como CSV para análise."""
    fire_map = np.load(data_dir / "fire_map.npy")

    # Calcular matriz de tempo de queima
    grid_height, grid_width = fire_map.shape[1], fire_map.shape[2]
    burn_time = np.full((grid_height, grid_width), -1, dtype=np.int32)

    for t in range(fire_map.shape[0]):
        newly_burning = (fire_map[t] >= 1) & (burn_time == -1)
        burn_time[newly_burning] = t

    # Salvar como CSV
    np.savetxt(output_path, burn_time, delimiter=",", fmt="%d")
    print(f"Matriz de tempo de queima salva: {output_path}")


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
    parser = argparse.ArgumentParser(description="Exporta simulação para GeoJSON")
    parser.add_argument("--data-dir", type=str, help="Diretório com os dados")
    parser.add_argument("--output", type=str, default="fire_simulation.geojson")
    parser.add_argument("--csv", action="store_true", help="Também exportar CSV")

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

    # Exportar GeoJSON
    output_path = Path(args.output)
    export_to_geojson(data_dir, output_path)

    # Exportar CSV se solicitado
    if args.csv:
        csv_path = output_path.with_suffix(".csv")
        export_burn_time_matrix(data_dir, csv_path)


if __name__ == "__main__":
    main()
