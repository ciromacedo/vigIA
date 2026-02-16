# VigIA - Contexto do Projeto e Roadmap

## Resumo Executivo

Este documento registra o estado atual do projeto VigIA, um sistema de simulação de incêndios florestais baseado no SimFire, adaptado para o contexto brasileiro. O MVP foi desenvolvido para simular incêndios no Parque Estadual Altamiro de Moura Pacheco em Goiânia/GO.

---

## Estado Atual (MVP Concluído)

### O que foi implementado

1. **Configuração para o Parque Altamiro**
   - Arquivo: `configs/parque_altamiro_config.yml`
   - Coordenadas: 16°34'16.23"S, 49°10'55.28"W
   - Área: 232 hectares (100x100 pixels, 15m/pixel)
   - Dados sintéticos (topografia Perlin, vegetação Chaparral)

2. **Scripts de Execução**
   - `scripts/run_mvp_parque_altamiro.py` - Executa a simulação
   - `scripts/visualize_openstreetmap.py` - Gera mapa estático no OSM
   - `scripts/animate_fire_spread.py` - Gera animação temporal interativa
   - `scripts/export_geojson.py` - Exporta dados para GeoJSON

3. **Infraestrutura Docker**
   - `Dockerfile.mvp` - Container com todas as dependências
   - `scripts/requirements_mvp.txt` - Dependências Python

4. **Deploy em Produção**
   - Servidor: 146.190.142.140 (nginx)
   - URLs:
     - http://146.190.142.140/menu.html (página inicial)
     - http://146.190.142.140/ (animação)
     - http://146.190.142.140/fire_simulation_map.html (mapa estático)
     - http://146.190.142.140/fire_simulation.geojson (dados)

### Parâmetros da Simulação Atual

| Parâmetro | Valor | Tipo |
|-----------|-------|------|
| Topografia | Perlin noise (750-850m) | Sintético |
| Vegetação | Chaparral (FBFM) | Sintético |
| Umidade | 2.5% | Configurável |
| Vento | 14.5 km/h de Leste | Configurável |
| Modelo | Rothermel | Físico |

### Arquivos Gerados pela Simulação

```
~/.simfire/parque_altamiro/
├── data/YYYY-MM-DD_HH-MM-SS/
│   ├── fire_map.npy        # Matriz temporal de propagação
│   ├── elevation.npy       # Elevação do terreno
│   ├── wind_speed.npy      # Velocidade do vento
│   ├── wind_direction.npy  # Direção do vento
│   ├── w_0.npy             # Carga de combustível
│   ├── sigma.npy           # Razão superfície/volume
│   ├── delta.npy           # Profundidade do combustível
│   ├── M_x.npy             # Umidade de extinção
│   └── metadata.json       # Configuração completa
├── graphs/
│   └── fire_spread_graph_*.png
└── gifs/
    └── simulation_*.gif
```

---

## Limitações do MVP Atual

1. **Dados Sintéticos**: Topografia e vegetação não correspondem à realidade
2. **Vento Constante**: Não há variação temporal ou espacial
3. **Vegetação Homogênea**: Todo o terreno usa o mesmo modelo de combustível
4. **Sem Intervenção**: Não simula combate ao fogo ou aceiros
5. **Área Limitada**: Apenas ~232 hectares
6. **Execução Offline**: Simulação precisa rodar antes de visualizar

---

## Roadmap - Próximas Etapas

### Fase 2: Dados Reais do Brasil

**Objetivo**: Substituir dados sintéticos por dados geoespaciais reais

**Tarefas**:
- [ ] Integrar TOPODATA/SRTM para elevação real
- [ ] Mapear vegetação do MapBiomas para modelos FBFM
- [ ] Criar classes `BrazilTopographyLayer` e `BrazilFuelLayer`
- [ ] Suportar coordenadas fora do CONUS (atualmente limitado aos EUA)

**Fontes de Dados**:
| Dado | Fonte | Resolução |
|------|-------|-----------|
| Elevação | TOPODATA (INPE) | 30m |
| Elevação | SRTM (NASA) | 30m |
| Vegetação | MapBiomas | 30m |
| Meteorologia | INMET/ERA5 | Variável |

**Mapeamento Vegetação Cerrado → FBFM**:
| Cerrado | Modelo FBFM |
|---------|-------------|
| Campo Limpo | ShortGrass |
| Campo Sujo | TallGrass |
| Cerrado Stricto Sensu | Brush/Chaparral |
| Cerradão | TimberLitterUnderstory |
| Mata de Galeria | HardwoodLongNeedlePineTimber |

### Fase 3: Portal Web Interativo

**Objetivo**: Permitir execução de simulações via interface web

**Funcionalidades**:
- [ ] Backend API (FastAPI/Flask) para executar simulações
- [ ] Interface para desenhar polígono da área no mapa
- [ ] Formulário para ajustar parâmetros:
  - Umidade do combustível
  - Velocidade e direção do vento
  - Ponto de ignição (clique no mapa)
  - Duração da simulação
- [ ] Fila de processamento (Celery/Redis)
- [ ] Visualização em tempo real do progresso
- [ ] Download dos resultados (GeoJSON, GIF, relatório)

**Arquitetura Proposta**:
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│   Worker    │
│  (React/Vue)│◀────│  (FastAPI)  │◀────│  (SimFire)  │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Leaflet/   │     │  PostgreSQL │     │    Redis    │
│  MapLibre   │     │  + PostGIS  │     │   (Queue)   │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Fase 4: Recursos Avançados

- [ ] Simulação de múltiplos focos simultâneos
- [ ] Aceiros e linhas de contenção interativas
- [ ] Integração com dados meteorológicos em tempo real
- [ ] Previsão de risco de incêndio
- [ ] Histórico de simulações por região
- [ ] API pública para integração com outros sistemas
- [ ] Alertas automáticos baseados em condições climáticas

---

## Estrutura de Arquivos do Projeto

```
vigIA/
├── configs/
│   ├── parque_altamiro_config.yml    # Config do MVP
│   └── [outros configs originais]
├── scripts/
│   ├── run_mvp_parque_altamiro.py    # Execução da simulação
│   ├── visualize_openstreetmap.py    # Mapa estático OSM
│   ├── animate_fire_spread.py        # Animação temporal
│   ├── export_geojson.py             # Exportação GeoJSON
│   ├── requirements_mvp.txt          # Dependências
│   ├── setup_mvp.sh                  # Script de setup
│   └── README_MVP.md                 # Documentação
├── simfire/                          # Código fonte do SimFire
│   ├── sim/simulation.py             # Classe principal
│   ├── game/managers/fire.py         # Gerenciador de fogo
│   ├── world/rothermel.py            # Modelo de propagação
│   ├── utils/config.py               # Parsing de configuração
│   └── utils/layers.py               # Camadas de dados
├── Dockerfile.mvp                    # Container Docker
├── PROJECT_CONTEXT.md                # Este arquivo
└── pyproject.toml                    # Dependências Poetry
```

---

## Comandos Úteis

### Executar Simulação Local (Docker)
```bash
# Build
docker build -f Dockerfile.mvp -t simfire-mvp .

# Executar simulação
docker run --rm -v ~/.simfire:/root/.simfire simfire-mvp

# Gerar animação
docker run --rm -v ~/.simfire:/root/.simfire -v $(pwd)/scripts:/scripts \
  simfire-mvp python /scripts/animate_fire_spread.py --output /scripts/fire_animation.html
```

### Deploy no Servidor
```bash
# Copiar arquivo para servidor
scp scripts/fire_animation.html root@146.190.142.140:/var/www/vigia/

# Acessar servidor
ssh root@146.190.142.140
```

### Servidor de Produção
- **IP**: 146.190.142.140
- **Usuário**: root
- **Web Server**: nginx
- **Diretório**: /var/www/vigia/

---

## Informações Técnicas

### Modelo de Rothermel
O SimFire usa o modelo de Rothermel para calcular a taxa de propagação:

```
R = (I_R * ξ * (1 + φ_w + φ_s)) / (ρ_b * ε * Q_ig)
```

Onde:
- `R` = Taxa de propagação (ft/min)
- `I_R` = Intensidade da reação
- `ξ` = Fluxo de propagação
- `φ_w` = Coeficiente de vento
- `φ_s` = Coeficiente de inclinação
- `ρ_b` = Densidade do leito
- `ε` = Número de aquecimento efetivo
- `Q_ig` = Calor de pré-ignição

### Conversões Importantes
- 1 pixel = 50 pés = 15.24 metros (config atual)
- 30 metros ≈ 0.00027778 graus (lat/lon)
- 1 mph ≈ 1.609 km/h

---

## Contato e Referências

### Projeto Original
- SimFire: https://github.com/mitrefireline/simfire
- Documentação: https://mitrefireline.github.io/simfire/

### Fontes de Dados Brasil
- TOPODATA: http://www.dsr.inpe.br/topodata/
- MapBiomas: https://mapbiomas.org/
- INMET: https://portal.inmet.gov.br/

---

*Última atualização: 2024-02-16*
*MVP desenvolvido para validação do conceito de simulação de incêndios no Cerrado brasileiro.*
