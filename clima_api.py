"""API de clima com histórico e gráfico das últimas 24 horas.

Consome a API pública Open-Meteo (sem necessidade de chave de acesso).
"""

import io
from datetime import datetime
from pathlib import Path

import matplotlib

# O backend Agg desenha em memória, sem depender de interface gráfica.
# Obrigatório para rodar dentro de um container, que não tem tela.
matplotlib.use("Agg")

import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import requests  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse, Response  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SEGUNDOS = 15

# Caminho absoluto derivado do próprio arquivo: funciona igual rodando local
# ou dentro do container, independente do diretório de trabalho.
DIRETORIO_ESTATICO = Path(__file__).resolve().parent / "static"

COR_FUNDO = "#ffffff"
COR_LINHA = "#2563eb"
COR_MAXIMA = "#dc2626"
COR_MINIMA = "#0d9488"
COR_TEXTO = "#0f172a"
COR_TEXTO_SUAVE = "#64748b"
COR_GRADE = "#e2e8f0"

app = FastAPI(
    title="API de Clima",
    description=(
        "Consulta o clima de uma cidade e gera um gráfico da temperatura "
        "nas últimas 24 horas. Dados fornecidos pela Open-Meteo."
    ),
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=DIRETORIO_ESTATICO), name="static")


def buscar_cidade(nome_cidade: str) -> dict:
    """Converte o nome de uma cidade em coordenadas geográficas."""
    parametros = {
        "name": nome_cidade,
        "count": 1,
        "language": "pt",
        "format": "json",
    }
    try:
        resposta = requests.get(GEO_URL, params=parametros, timeout=TIMEOUT_SEGUNDOS)
        resposta.raise_for_status()
    except requests.RequestException as erro:
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao consultar o serviço de geocodificação: {erro}",
        )

    resultados = resposta.json().get("results")
    if not resultados:
        raise HTTPException(
            status_code=404,
            detail=f"Cidade '{nome_cidade}' não encontrada.",
        )

    cidade = resultados[0]
    return {
        "nome": cidade["name"],
        "pais": cidade.get("country", ""),
        "latitude": cidade["latitude"],
        "longitude": cidade["longitude"],
    }


def buscar_previsao(latitude: float, longitude: float) -> dict:
    """Busca o clima atual e a série horária no entorno do momento presente."""
    parametros = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation",
        "current_weather": True,
        "past_days": 1,
        "forecast_days": 1,
        "timezone": "auto",
    }
    try:
        resposta = requests.get(
            WEATHER_URL, params=parametros, timeout=TIMEOUT_SEGUNDOS
        )
        resposta.raise_for_status()
    except requests.RequestException as erro:
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao consultar o serviço de clima: {erro}",
        )
    return resposta.json()


def recortar_ultimas_24h(previsao: dict) -> dict:
    """Extrai as 24 horas que antecedem o momento atual.

    A Open-Meteo devolve um intervalo maior (dia anterior + dia atual, incluindo
    horas futuras), então é preciso recortar a janela desejada.
    """
    horas = previsao["hourly"]["time"]
    agora = previsao["current_weather"]["time"]

    # Datas em ISO 8601 de mesmo formato podem ser comparadas como texto.
    indices_passados = [i for i, hora in enumerate(horas) if hora <= agora]
    if not indices_passados:
        raise HTTPException(
            status_code=502,
            detail="O serviço de clima não retornou horas já ocorridas.",
        )

    fim = indices_passados[-1]
    janela = slice(max(0, fim - 23), fim + 1)

    return {
        "horas": horas[janela],
        "temperaturas": previsao["hourly"]["temperature_2m"][janela],
        "umidades": previsao["hourly"]["relative_humidity_2m"][janela],
        "precipitacoes": previsao["hourly"]["precipitation"][janela],
    }


def gerar_grafico_png(cidade: dict, serie: dict) -> bytes:
    """Desenha o gráfico de temperatura e devolve a imagem em bytes."""
    horas = [datetime.fromisoformat(hora) for hora in serie["horas"]]
    temperaturas = serie["temperaturas"]

    figura, eixo = plt.subplots(figsize=(10, 4.2), dpi=140)
    try:
        figura.patch.set_facecolor(COR_FUNDO)
        eixo.set_facecolor(COR_FUNDO)

        margem = max(1.5, (max(temperaturas) - min(temperaturas)) * 0.18)
        piso = min(temperaturas) - margem
        eixo.set_ylim(piso, max(temperaturas) + margem)

        eixo.fill_between(horas, temperaturas, piso, color=COR_LINHA, alpha=0.10)
        eixo.plot(horas, temperaturas, color=COR_LINHA, linewidth=2.4)

        indice_max = temperaturas.index(max(temperaturas))
        indice_min = temperaturas.index(min(temperaturas))
        for indice, cor in ((indice_max, COR_MAXIMA), (indice_min, COR_MINIMA)):
            eixo.plot(
                horas[indice],
                temperaturas[indice],
                marker="o",
                markersize=7,
                color=cor,
                markeredgecolor=COR_FUNDO,
                markeredgewidth=2,
                zorder=3,
            )
            eixo.annotate(
                f"{temperaturas[indice]:.1f}°",
                xy=(horas[indice], temperaturas[indice]),
                xytext=(0, 12),
                textcoords="offset points",
                ha="center",
                fontsize=10,
                color=cor,
                fontweight="bold",
            )

        local = f"{cidade['nome']}, {cidade['pais']}".strip(", ")
        eixo.set_title(
            f"Temperatura nas últimas 24 horas · {local}",
            fontsize=13,
            fontweight="600",
            color=COR_TEXTO,
            pad=16,
            loc="left",
        )
        eixo.set_ylabel("°C", fontsize=10, color=COR_TEXTO_SUAVE)
        eixo.grid(True, axis="y", linestyle="-", linewidth=0.7, color=COR_GRADE)
        eixo.set_axisbelow(True)
        # Sem as bordas do gráfico o desenho fica mais leve e moderno.
        for lado in ("top", "right", "left"):
            eixo.spines[lado].set_visible(False)
        eixo.spines["bottom"].set_color(COR_GRADE)
        eixo.tick_params(colors=COR_TEXTO_SUAVE, labelsize=9, length=0)

        eixo.xaxis.set_major_formatter(mdates.DateFormatter("%Hh"))
        eixo.xaxis.set_major_locator(mdates.HourLocator(interval=3))
        figura.tight_layout()

        buffer = io.BytesIO()
        figura.savefig(buffer, format="png", facecolor=COR_FUNDO)
        return buffer.getvalue()
    finally:
        # Sem isso, cada requisição deixaria uma figura na memória do processo.
        plt.close(figura)


@app.get("/", include_in_schema=False)
def raiz():
    return FileResponse(DIRETORIO_ESTATICO / "index.html")


@app.get("/health")
def health():
    """Verifica se a aplicação está no ar, sem depender de serviços externos."""
    return {"status": "ok"}


@app.get("/temperatura-cidade")
def temperatura_cidade(nome_cidade: str):
    """Retorna a temperatura atual da cidade informada."""
    cidade = buscar_cidade(nome_cidade)
    previsao = buscar_previsao(cidade["latitude"], cidade["longitude"])
    atual = previsao["current_weather"]

    return {
        "cidade": cidade["nome"],
        "pais": cidade["pais"],
        "hora_local": atual["time"],
        "temperatura_c": atual["temperature"],
        "vento_kmh": atual["windspeed"],
    }


@app.get("/clima-24h")
def clima_24h(nome_cidade: str):
    """Retorna a série horária das últimas 24 horas, com um resumo."""
    cidade = buscar_cidade(nome_cidade)
    previsao = buscar_previsao(cidade["latitude"], cidade["longitude"])
    serie = recortar_ultimas_24h(previsao)

    temperaturas = [t for t in serie["temperaturas"] if t is not None]
    if not temperaturas:
        raise HTTPException(
            status_code=502,
            detail="O serviço de clima não retornou temperaturas para o período.",
        )
    precipitacoes = [p for p in serie["precipitacoes"] if p is not None]

    return {
        "cidade": cidade["nome"],
        "pais": cidade["pais"],
        "latitude": cidade["latitude"],
        "longitude": cidade["longitude"],
        "fuso_horario": previsao.get("timezone"),
        "atual": {
            "hora_local": previsao["current_weather"]["time"],
            "temperatura_c": previsao["current_weather"]["temperature"],
            "vento_kmh": previsao["current_weather"]["windspeed"],
        },
        "resumo": {
            "temperatura_minima_c": min(temperaturas),
            "temperatura_maxima_c": max(temperaturas),
            "temperatura_media_c": round(sum(temperaturas) / len(temperaturas), 1),
            "precipitacao_total_mm": round(sum(precipitacoes), 1),
        },
        "horas": [
            {
                "hora": hora,
                "temperatura_c": temperatura,
                "umidade_relativa_pct": umidade,
                "precipitacao_mm": precipitacao,
            }
            for hora, temperatura, umidade, precipitacao in zip(
                serie["horas"],
                serie["temperaturas"],
                serie["umidades"],
                serie["precipitacoes"],
            )
        ],
    }


@app.get(
    "/clima-24h/grafico",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
)
def clima_24h_grafico(nome_cidade: str):
    """Retorna um gráfico PNG da temperatura nas últimas 24 horas."""
    cidade = buscar_cidade(nome_cidade)
    previsao = buscar_previsao(cidade["latitude"], cidade["longitude"])
    serie = recortar_ultimas_24h(previsao)

    if any(t is None for t in serie["temperaturas"]):
        raise HTTPException(
            status_code=502,
            detail="O serviço de clima retornou temperaturas incompletas.",
        )

    imagem = gerar_grafico_png(cidade, serie)
    return Response(content=imagem, media_type="image/png")
