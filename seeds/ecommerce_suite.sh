#!/usr/bin/env bash
# Suite du cas e-commerce : traitements (risques 7 a 13) et BIA (processus 6 a 9)
# Valeurs provisoires de demonstration, a valider avec les responsables.
API=http://127.0.0.1:8000/api
: "${RISKMAP_PW:?Definis RISKMAP_PW avant de lancer ce script}"
TOKEN=$(curl -s -X POST $API/auth/login \
  --data-urlencode "username=admin_risk" --data-urlencode "password=$RISKMAP_PW" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
[ -z "$TOKEN" ] && { echo "Echec login"; exit 1; }
H="Authorization: Bearer $TOKEN"; J="Content-Type: application/json"

send() {  # $1 = route, $2 = json, $3 = libelle
  code=$(curl -s -o /tmp/resp.json -w "%{http_code}" -X POST "$API/$1" -H "$H" -H "$J" -d "$2")
  case $code in 2*) echo "OK  $code  $3" ;; *) echo "ERR $code  $3"; cat /tmp/resp.json; echo ;; esac
}
t() { send "risks/$1/treatments" "{\"strategy\":\"$2\",\"action\":\"$3\",\"status\":\"à faire\"}" "risque $1 : $3"; }

echo "=== Traitements"
t 7  "réduire"    "Mettre en place une protection anti-DDoS et un CDN"
t 8  "réduire"    "Isoler les sauvegardes et tester régulièrement la restauration"
t 8  "réduire"    "Préparer un plan de reprise après incident"
t 9  "réduire"    "Ajouter un second prestataire de paiement de secours"
t 10 "transférer" "Souscrire un SLA renforcé et un plan de reprise multi-zones"
t 11 "réduire"    "Activer l'authentification multifacteur sur tous les comptes administrateur"
t 11 "réduire"    "Chiffrer les données personnelles et auditer les accès"
t 12 "réduire"    "Contractualiser un second transporteur"
t 13 "réduire"    "Créer un environnement de test et une procédure de retour arrière"

echo "=== BIA"
bia() { send "bia" "{\"process_id\":$1,\"financial_impact\":$2,\"operational_impact\":$3,\"legal_impact\":$4,\"reputational_impact\":$5,\"business_consequences\":\"$6\",\"essential_resources\":\"$7\"}" "BIA processus $1"; }

bia 6 5 5 3 4 \
 "Une interruption du paiement en ligne arrête immédiatement les ventes et génère des pertes de chiffre d'affaires, des paniers abandonnés et des litiges clients. Valeurs provisoires, à valider." \
 "Site web, passerelle de paiement, hébergement cloud, base clients et commandes, équipe IT d'exploitation."
bia 7 3 3 2 3 \
 "Une indisponibilité du catalogue ou des stocks provoque des erreurs de prix ou de disponibilité, des commandes impossibles à honorer et une baisse de confiance. Valeurs provisoires, à valider." \
 "Site web, base de données produits et stocks, entrepôt, équipe IT."
bia 8 3 4 2 4 \
 "Une défaillance de la logistique retarde les livraisons, augmente les demandes de remboursement et dégrade l'image de la boutique. Valeurs provisoires, à valider." \
 "Transporteur, entrepôt et stock, base des commandes, outils de suivi des colis."
bia 9 2 3 4 4 \
 "Une indisponibilité ou une fuite touchant le service client expose des données personnelles (obligations RGPD) et fait perdre la confiance des clients. Valeurs provisoires, à valider." \
 "Base clients, outil de support, équipe service client, équipe IT."
