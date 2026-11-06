#!/usr/bin/env bash
# Requer a API no ar: uvicorn app.main:app --port 8000 --no-access-log
BASE=${BASE:-http://localhost:8000}
API_KEY=$(grep '^API_KEY=' .env | cut -d= -f2-)
USU="$BASE/api/v1/usuarios"
falhas=0

checa() {  # checa <status esperado> <descrição> <args do curl...>
  esperado=$1; desc=$2; shift 2
  obtido=$(curl -s -o /dev/null -w "%{http_code}" "$@")
  if [ "$obtido" = "$esperado" ]; then
    echo "[OK]     $obtido  $desc"
  else
    echo "[FALHA]  esperado $esperado, obtido $obtido  $desc"; falhas=$((falhas+1))
  fi
}

checa 200 "id válido, com chave"  -H "X-API-Key: $API_KEY" "$USU/1/acordos"
checa 404 "autor inexistente"     -H "X-API-Key: $API_KEY" "$USU/999/acordos"
checa 400 "id não numérico"       -H "X-API-Key: $API_KEY" "$USU/abc/acordos"
checa 400 "id zero"               -H "X-API-Key: $API_KEY" "$USU/0/acordos"
checa 401 "sem chave"             "$USU/1/acordos"
checa 401 "chave errada"          -H "X-API-Key: errada" "$USU/1/acordos"
checa 200 "/health"               "$BASE/health"
checa 200 "/health/ready"         "$BASE/health/ready"

cid=$(curl -si -H "X-Correlation-ID: demo-123" -H "X-API-Key: $API_KEY" "$USU/999/acordos" \
      | tr -d '\r' | grep -i '^x-correlation-id:' | awk '{print $2}')
if [ "$cid" = "demo-123" ]; then echo "[OK]     correlation id devolvido no cabeçalho"
else echo "[FALHA]  correlation id: obtido '$cid'"; falhas=$((falhas+1)); fi

resumo=$(curl -s -H "X-API-Key: $API_KEY" "$USU/1/acordos" \
  | python -c "import json,sys; r=json.load(sys.stdin)['resumo']; print(r['quantidadeAcordos'], r['quantidadeDocumentos'])")
if [ "$resumo" = "10 500" ]; then echo "[OK]     resumo do autor 1: 10 acordos, 500 documentos"
else echo "[FALHA]  resumo: obtido '$resumo'"; falhas=$((falhas+1)); fi

echo; echo "falhas: $falhas"; exit $falhas
