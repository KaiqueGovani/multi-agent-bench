# Storage local da POC

O provider padrao continua sendo `local`. Para usar MinIO local, suba a stack:

```powershell
docker compose -f infra/docker/docker-compose.yml up -d postgres minio
```

Configure a API:

```powershell
$env:STORAGE_PROVIDER="minio"
$env:STORAGE_BUCKET="multi-agent-bench-poc"
$env:STORAGE_ENDPOINT_URL="http://127.0.0.1:9000"
$env:STORAGE_ACCESS_KEY="minioadmin"
$env:STORAGE_SECRET_KEY="minioadmin"
$env:STORAGE_REGION="us-east-1"
```

Para producao, use `STORAGE_PROVIDER=s3` e aponte as mesmas variaveis para o
bucket cloud equivalente. O dominio da aplicacao deve continuar acessando
anexos apenas pela interface de storage.
