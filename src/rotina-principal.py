## Importando libs necessarias para o pipeline
import pandas as pd
import boto3
import io
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
import logging
import sys
from datetime import datetime

# 1. Gera uma string com a data e hora atual (ex: 2026-05-28_18-30-00)
data_hora_atual = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
nome_do_arquivo = f"app_{data_hora_atual}.log"

# 2. Configura o logging usando o novo nome
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(nome_do_arquivo, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
# 2. Criar o objeto 'logger' que usaremos no código
logger = logging.getLogger("Jornada de Dados")


logger.info("Iniciando o script de extração de dados...")

load_dotenv()


logger.info("Importando variaveis de ambiente")
## configurando variaveis de ambiente, todas salvas no arquivos .env na raiz do projeto
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")
DATABASE_URL= os.getenv("DATABASE_URL")
DIRECT_URL= os.getenv("DIRECT_URL")


## Criando conexão com o S3
logger.info(f"Conectando ao S3")
s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    endpoint_url=S3_ENDPOINT_URL,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)



logger.info(f"Verificando arquivos no Bucket")
response = s3.list_objects_v2(Bucket=BUCKET_NAME)
arquivos = [obj["Key"] for obj in response["Contents"]]

logger.info(f"{arquivos}")



logger.info(f"Tentando conectar ao banco de dados")
engine = create_engine(DATABASE_URL)


## Nome das tabelas finais, usando como padrão o nome do arquivo original.
tabelas = ['clientes', 'preco_competidores', 'produtos', 'vendas']
dataframe = {}



## Lendo arquivos parquet
for tabela in tabelas:
    file_key = f"{tabela}.parquet"
    logger.info(f"Lendo arquivo: {file_key}")
    response = s3.get_object(Bucket=BUCKET_NAME, Key=file_key)
    parquet_bytes = response["Body"].read()
    dataframe[tabela] = pd.read_parquet(io.BytesIO(parquet_bytes))




for tabela, df in dataframe.items():
    logger.info(f"Criando tabela: {tabela}")
    df.to_sql(
        tabela,                # Nome da tabela no banco
        engine,                # Engine de conexão
        if_exists="replace",   # Substituir se existir
        index=False,           # Não salvar índice do pandas
    )
    logger.info(f"Tabela {tabela} criada com sucesso!!")



logger.info("\n📊 Verificação final:")
for tabela in tabelas:
    df_verificacao = pd.read_sql_query(f"SELECT COUNT(*) as total FROM {tabela}", engine)
    total = df_verificacao["total"].iloc[0]
    logger.info(f"  ✅ {tabela}: {total} linhas no banco")

# Fechar conexão
engine.dispose()
