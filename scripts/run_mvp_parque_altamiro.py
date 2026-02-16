#!/usr/bin/env python3
"""
MVP - Simulação de Incêndio no Parque Estadual Altamiro de Moura Pacheco
Goiânia, GO, Brasil

Este script executa uma simulação de propagação de incêndio florestal
utilizando dados sintéticos que aproximam as condições do cerrado goiano.

Coordenadas do Parque:
    - Latitude: 16°34'16.23"S (-16.571175°)
    - Longitude: 49°10'55.28"W (-49.181467°)

Execução:
    python scripts/run_mvp_parque_altamiro.py

Saída:
    - GIF animado da simulação
    - Gráfico de propagação do fogo
    - Dados salvos em ~/.simfire/parque_altamiro/
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para importar simfire
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from simfire.sim.simulation import FireSimulation
from simfire.utils.config import Config


def main():
    print("=" * 60)
    print("MVP - Simulação de Incêndio Florestal")
    print("Parque Estadual Altamiro de Moura Pacheco")
    print("Goiânia, GO, Brasil")
    print("=" * 60)
    print()

    # Carrega a configuração
    config_path = ROOT_DIR / "configs" / "parque_altamiro_config.yml"
    print(f"Carregando configuração: {config_path}")
    config = Config(str(config_path))

    # Cria a simulação
    print("Inicializando simulação...")
    sim = FireSimulation(config)

    # Informações da simulação
    print()
    print("Parâmetros da Simulação:")
    print(f"  - Tamanho da área: {config.area.screen_size} pixels")
    print(f"  - Escala: {config.area.pixel_scale} pés/pixel")
    print(f"  - Umidade do combustível: {config.environment.moisture * 100:.1f}%")
    print(f"  - Duração: {config.simulation.runtime}")
    print()

    # Fase 1: Simulação inicial sem renderização (mais rápido)
    print("Fase 1: Executando simulação inicial (2h sem visualização)...")
    sim.run("2h")

    # Fase 2: Ativa a renderização para visualizar a propagação
    print("Fase 2: Ativando visualização...")
    print("  [Pressione Q ou feche a janela para encerrar]")
    print()
    sim.rendering = True

    # Executa o restante da simulação com visualização
    sim.run("6h")

    # Salva os resultados
    print()
    print("Salvando resultados...")

    try:
        sim.save_gif()
        print("  - GIF salvo com sucesso!")
    except Exception as e:
        print(f"  - Erro ao salvar GIF: {e}")

    try:
        sim.save_spread_graph()
        print("  - Gráfico de propagação salvo com sucesso!")
    except Exception as e:
        print(f"  - Erro ao salvar gráfico: {e}")

    print()
    print("=" * 60)
    print("Simulação concluída!")
    print(f"Resultados salvos em: {config.simulation.sf_home}")
    print("=" * 60)


def run_headless():
    """Executa a simulação sem interface gráfica (para servidores)."""
    print("Executando em modo headless...")

    config_path = ROOT_DIR / "configs" / "parque_altamiro_config.yml"
    config = Config(str(config_path))

    # Força modo headless
    config.simulation.headless = True

    sim = FireSimulation(config)

    # Executa a simulação
    print("Iniciando simulação de 8 horas...")
    sim.run("8h")

    # Para salvar GIF, precisamos habilitar rendering brevemente
    print("Gerando visualização para GIF...")
    sim.rendering = True
    sim.run(1)  # Executa 1 frame para inicializar o game

    try:
        sim.save_gif()
        print("GIF salvo com sucesso!")
    except Exception as e:
        print(f"Aviso: Não foi possível salvar GIF: {e}")

    try:
        sim.save_spread_graph()
        print("Gráfico de propagação salvo com sucesso!")
    except Exception as e:
        print(f"Aviso: Não foi possível salvar gráfico: {e}")

    # Exibe estatísticas finais
    obs = sim.get_attribute_data()
    fire_map = obs.get("fire_map", None)
    if fire_map is not None:
        burned = (fire_map == 2).sum()
        total = fire_map.size
        pct = (burned / total) * 100
        print(f"\nResultados:")
        print(f"  Área queimada: {burned} pixels ({pct:.1f}%)")
        print(f"  Área total: {total} pixels")

    print("\nSimulação concluída!")


def run_interactive():
    """
    Executa a simulação em modo interativo.
    Permite pausar, adicionar agentes e linhas de controle.
    """
    print("Executando em modo interativo...")

    config_path = ROOT_DIR / "configs" / "parque_altamiro_config.yml"
    config = Config(str(config_path))

    sim = FireSimulation(config)
    sim.rendering = True

    # Executa passo a passo
    print("\nControles:")
    print("  - A simulação avança automaticamente")
    print("  - Feche a janela para encerrar")
    print()

    # Loop de simulação interativo
    total_steps = 0
    max_steps = 480  # 8 horas * 60 min/hora / 1 min por step

    while total_steps < max_steps:
        # Executa 10 passos por vez
        sim.run(10)
        total_steps += 10

        # Obtém dados de observação
        obs = sim.get_attribute_data()

        # Conta pixels queimando/queimados
        fire_map = obs.get("fire_map", None)
        if fire_map is not None:
            burning = (fire_map == 1).sum()
            burned = (fire_map == 2).sum()
            print(
                f"\rTempo: {total_steps}min | "
                f"Queimando: {burning:4d} | "
                f"Queimado: {burned:5d} pixels",
                end="",
            )

    print("\n\nSimulação concluída!")
    sim.save_gif()
    sim.save_spread_graph()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="MVP - Simulação de Incêndio no Parque Altamiro"
    )
    parser.add_argument(
        "--mode",
        choices=["default", "headless", "interactive"],
        default="default",
        help="Modo de execução (default: com visualização)",
    )
    args = parser.parse_args()

    if args.mode == "headless":
        run_headless()
    elif args.mode == "interactive":
        run_interactive()
    else:
        main()
