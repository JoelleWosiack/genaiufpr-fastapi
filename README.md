# genaiufpr-fastapi

API de clima construída com FastAPI, que retorna a temperatura atual de uma cidade,
a série horária das últimas 24 horas e um gráfico em PNG gerado no servidor.
Acompanha uma interface web simples para consultar tudo pelo navegador.

Projeto desenvolvido para a disciplina de Deploy da pós-graduação em IA Generativa (UFPR).

## Funcionalidades

- Busca de qualquer cidade do mundo pelo nome, com resolução automática de coordenadas.
- Temperatura atual, velocidade do vento e horário local.
- Série horária das últimas 24 horas com temperatura, umidade relativa e precipitação.
- Gráfico da temperatura das últimas 24 horas renderizado como imagem PNG.
- Interface web sem dependências externas, servida pela própria API.
- Documentação interativa gerada automaticamente pelo FastAPI.

Os dados vêm da [Open-Meteo](https://open-meteo.com), que é pública e não exige chave de acesso.

## Rotas

| Método | Rota | Descrição |
| --- | --- | --- |
| GET | `/` | Interface web |
| GET | `/docs` | Documentação interativa (Swagger UI) |
| GET | `/health` | Verificação de disponibilidade |
| GET | `/temperatura-cidade?nome_cidade=` | Temperatura atual |
| GET | `/clima-24h?nome_cidade=` | Série horária das últimas 24 horas, em JSON |
| GET | `/clima-24h/grafico?nome_cidade=` | Gráfico das últimas 24 horas, em PNG |

Exemplo:

```bash
curl "http://localhost:8000/clima-24h?nome_cidade=Curitiba"
curl -o grafico.png "http://localhost:8000/clima-24h/grafico?nome_cidade=Curitiba"
```

## Como rodar com Docker

É a forma recomendada, porque não exige nada além do Docker instalado.

```bash
git clone https://github.com/JoelleWosiack/genaiufpr-fastapi.git
cd genaiufpr-fastapi
docker build -t clima-api .
docker run -d --name clima-api -p 8000:8000 --restart unless-stopped clima-api
```

Acesse `http://localhost:8000`.

Para acompanhar os logs ou remover o container:

```bash
docker logs -f clima-api
docker rm -f clima-api
```

## Como rodar sem Docker

Requer [conda](https://conda-forge.org/download/) instalado.

```bash
git clone https://github.com/JoelleWosiack/genaiufpr-fastapi.git
cd genaiufpr-fastapi
conda env create -f environment.yml
conda activate clima_api
uvicorn clima_api:app --reload
```

## Deploy em servidor remoto

O projeto foi publicado em uma instância Ubuntu na Oracle Cloud. Há duas formas de
levar a aplicação para um servidor.

**Construindo a imagem no servidor.** Foi a abordagem usada aqui: basta clonar o
repositório na máquina remota e repetir os comandos da seção do Docker. Evita
transferir mais de 1 GB pela rede e garante que a imagem seja compilada para a
arquitetura correta do servidor.

**Transferindo uma imagem pronta.** Útil quando o servidor não tem acesso à internet.
A imagem precisa ter sido construída para a mesma arquitetura da máquina de destino.

```bash
docker save clima-api > clima-api.tar
scp -i ~/.ssh/sua_chave clima-api.tar ubuntu@IP_DO_SERVIDOR:~
ssh -i ~/.ssh/sua_chave ubuntu@IP_DO_SERVIDOR
docker load < clima-api.tar
docker run -d -p 8000:8000 --restart unless-stopped clima-api
```

Em qualquer um dos casos, a porta 8000 precisa ser liberada nas duas camadas de
firewall: no `iptables` do Ubuntu e na lista de segurança da rede virtual do provedor.

```bash
sudo iptables -I INPUT -p tcp --dport 8000 -j ACCEPT
sudo netfilter-persistent save
```

Em máquinas com pouca memória, como as do nível gratuito com 1 GB de RAM, é
necessário criar uma área de swap antes de construir a imagem, caso contrário o
`conda env create` é interrompido por falta de memória.

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## Tecnologias

- **FastAPI** para as rotas e a documentação automática
- **Uvicorn** como servidor ASGI
- **Requests** para consumir a API da Open-Meteo
- **Matplotlib** para renderizar o gráfico no servidor
- **Docker** e **conda** para empacotamento e reprodutibilidade

## Licença

MIT

