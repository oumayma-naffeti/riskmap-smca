#!/usr/bin/env bash
API=http://127.0.0.1:8000/api
: "${RISKMAP_PW:?Definis RISKMAP_PW}"
TOKEN=$(curl -s -X POST $API/auth/login --data-urlencode "username=admin_risk" \
  --data-urlencode "password=$RISKMAP_PW" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
[ -z "$TOKEN" ] && { echo "Echec login"; exit 1; }
H="Authorization: Bearer $TOKEN"

echo "Seront supprimés : risques 2 3 | BIA 2 3 4 | processus 1 3 4"
read -r -p "Taper OUI pour confirmer : " ok
[ "$ok" = "OUI" ] || { echo "Annulé."; exit 0; }

del() { code=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$API/$1" -H "$H"); echo "$code  DELETE $1"; }
for r in 2 3; do del risks/$r; done
for b in 2 3 4; do del bia/$b; done
for p in 1 3 4; do del processes/$p; done
