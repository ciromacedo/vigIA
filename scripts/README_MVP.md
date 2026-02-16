# MVP - Simulação de Incêndio no Parque Altamiro de Moura Pacheco

## Sobre

Este MVP simula a propagação de um incêndio florestal no **Parque Estadual Altamiro de Moura Pacheco**, localizado em Goiânia, GO, Brasil.

### Coordenadas do Parque
- **Latitude**: 16°34'16.23"S (-16.571175°)
- **Longitude**: 49°10'55.28"W (-49.181467°)

### Características da Simulação
- **Vegetação**: Simulada como Chaparral (similar ao Cerrado Stricto Sensu)
- **Terreno**: Gerado proceduralmente (elevação ~750-850m)
- **Vento**: Ventos de Leste, ~15 km/h (típico do período seco)
- **Umidade**: 2.5% (condição de seca severa)

## Instalação

### Opção 1: Com Poetry (Recomendado)

```bash
# Instalar Python 3.9 (se necessário)
# Ubuntu/Debian:
sudo apt install python3.9 python3.9-venv python3.9-dev

# Instalar Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Instalar dependências
cd vigIA
poetry env use python3.9
poetry install

# Executar
poetry run python scripts/run_mvp_parque_altamiro.py
```

### Opção 2: Com Conda

```bash
# Criar ambiente
conda create -n simfire python=3.9 -y
conda activate simfire

# Instalar dependências
pip install -r scripts/requirements_mvp.txt

# Executar
python scripts/run_mvp_parque_altamiro.py
```

### Opção 3: Com venv

```bash
# Criar ambiente virtual
python3.9 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r scripts/requirements_mvp.txt

# Executar
python scripts/run_mvp_parque_altamiro.py
```

## Execução

### Modo Padrão (com visualização)
```bash
python scripts/run_mvp_parque_altamiro.py
```

### Modo Headless (sem interface gráfica)
```bash
python scripts/run_mvp_parque_altamiro.py --mode headless
```

### Modo Interativo (com logs detalhados)
```bash
python scripts/run_mvp_parque_altamiro.py --mode interactive
```

## Saída

Os resultados são salvos em `~/.simfire/parque_altamiro/`:
- `simulation.gif` - Animação da propagação do fogo
- `spread_graph.png` - Gráfico de área queimada vs tempo
- `*.npy` - Dados brutos da simulação

## Configuração

O arquivo de configuração está em `configs/parque_altamiro_config.yml`.

### Parâmetros Principais

| Parâmetro | Valor | Descrição |
|-----------|-------|-----------|
| `area.screen_size` | [100, 100] | Tamanho em pixels (~3km x 3km) |
| `environment.moisture` | 0.025 | Umidade do combustível (2.5%) |
| `wind.simple.speed` | 9 | Velocidade do vento (mph) |
| `wind.simple.direction` | 90 | Direção do vento (90° = Leste) |
| `fire.fire_initial_position.static.position` | (50, 70) | Ponto inicial do fogo |

### Ajustando a Simulação

**Mudar ponto inicial do fogo:**
```yaml
fire:
  fire_initial_position:
    static:
      position: (30, 50)  # Novo ponto (x, y)
```

**Aumentar velocidade do vento:**
```yaml
wind:
  simple:
    speed: 15  # mph
```

**Simular período mais úmido:**
```yaml
environment:
  moisture: 0.06  # 6% de umidade
```

## Próximos Passos (Opção B - Dados Reais)

Para usar dados reais do terreno:

1. **Obter DEM (Elevação)**:
   - Fonte: [TOPODATA INPE](http://www.dsr.inpe.br/topodata/)
   - Formato: GeoTIFF

2. **Obter Mapa de Vegetação**:
   - Fonte: [MapBiomas](https://mapbiomas.org/)
   - Mapear para modelos de combustível do SimFire

3. **Adaptar código**:
   - Criar `BrazilTopographyLayer` e `BrazilFuelLayer`
   - Implementar conversão de coordenadas

## Modelo de Propagação

O SimFire usa o **Modelo de Rothermel** para calcular a taxa de propagação do fogo:

```
R = I_R * ξ * (1 + φ_w + φ_s) / (ρ_b * ε * Q_ig)
```

Onde:
- `R` = Taxa de propagação (ft/min)
- `I_R` = Intensidade da reação
- `φ_w` = Coeficiente de vento
- `φ_s` = Coeficiente de inclinação

## Licença

Este projeto é baseado no [SimFire](https://github.com/mitrefireline/simfire) da MITRE.
