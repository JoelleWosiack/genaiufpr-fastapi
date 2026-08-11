FROM condaforge/miniforge3:latest

WORKDIR /app

# O environment.yml é copiado sozinho, antes do restante do código, para que o
# Docker reaproveite a camada de instalação em cache quando só o código mudar.
COPY environment.yml .

RUN conda env create -f environment.yml && conda clean --all --yes

COPY . .

EXPOSE 8000

CMD ["conda", "run", "--no-capture-output", "-n", "clima_api", \
     "uvicorn", "clima_api:app", "--host", "0.0.0.0", "--port", "8000"]
