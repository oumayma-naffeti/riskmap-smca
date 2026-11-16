#!/usr/bin/env bash
# Cas e-commerce : valeurs provisoires, hypotheses de demonstration
API=http://127.0.0.1:8000/api
: "${RISKMAP_PW:?Definis RISKMAP_PW avant de lancer ce script}"
RESP=$(curl -s -X POST $API/auth/login \
  --data-urlencode "username=admin_risk" --data-urlencode "password=$RISKMAP_PW")
TOKEN=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
[ -z "$TOKEN" ] && { echo "Echec login : $RESP"; exit 1; }

H="Authorization: Bearer $TOKEN"; J="Content-Type: application/json"
post()  { curl -s -X POST "$API/$1" -H "$H" -H "$J" -d "$2"; }
getid() { python3 -c "import sys,json; print(json.load(sys.stdin)['id'])"; }

# --- Actifs
A_WEB=$(post assets '{"name":"Site web e-commerce","asset_type":"application","description":"Vitrine et panier (hypothese)"}' | getid)
A_DB=$(post assets '{"name":"Base clients et commandes","asset_type":"application","description":"Donnees personnelles et historique des commandes (hypothese)"}' | getid)
A_PAY=$(post assets '{"name":"Passerelle de paiement","asset_type":"fournisseur","description":"Prestataire de paiement en ligne (hypothese)"}' | getid)
A_HOST=$(post assets '{"name":"Hebergement cloud","asset_type":"fournisseur","description":"Serveurs et reseau du site (hypothese)"}' | getid)
A_CARR=$(post assets '{"name":"Transporteur","asset_type":"fournisseur","description":"Livraison des colis (hypothese)"}' | getid)
A_WH=$(post assets '{"name":"Entrepot et stock","asset_type":"local","description":"Preparation des commandes (hypothese)"}' | getid)
A_IT=$(post assets '{"name":"Equipe IT","asset_type":"personnel","description":"Exploitation et support (hypothese)"}' | getid)

# --- Processus (MTPD/RTO/RPO = hypotheses a valider)
P_PAY=$(post processes "{\"name\":\"Prise de commande et paiement en ligne\",\"description\":\"Du panier a la confirmation de paiement\",\"criticality\":5,\"mtpd_hours\":4,\"rto_hours\":1,\"rpo_minutes\":5,\"asset_ids\":[$A_WEB,$A_DB,$A_PAY,$A_HOST,$A_IT]}" | getid)
P_STK=$(post processes "{\"name\":\"Gestion du catalogue et des stocks\",\"description\":\"Mise a jour des produits, prix et disponibilites\",\"criticality\":4,\"mtpd_hours\":24,\"rto_hours\":8,\"rpo_minutes\":60,\"asset_ids\":[$A_WEB,$A_DB,$A_WH]}" | getid)
P_LIV=$(post processes "{\"name\":\"Livraison et logistique\",\"description\":\"Preparation, expedition et suivi des colis\",\"criticality\":4,\"mtpd_hours\":48,\"rto_hours\":24,\"rpo_minutes\":240,\"asset_ids\":[$A_CARR,$A_WH,$A_DB]}" | getid)
P_SAV=$(post processes "{\"name\":\"Service client\",\"description\":\"Support, retours et remboursements\",\"criticality\":3,\"mtpd_hours\":72,\"rto_hours\":24,\"rpo_minutes\":240,\"asset_ids\":[$A_DB,$A_IT]}" | getid)

# --- Risques
r() { post risks "$1" | getid; }
R1=$(r "{\"process_id\":$P_PAY,\"asset_id\":$A_WEB,\"threat\":\"Attaque DDoS pendant une periode de forte activite\",\"vulnerability\":\"Pas de protection anti-DDoS ni de CDN\",\"probability\":3,\"impact\":4}")
R2=$(r "{\"process_id\":$P_PAY,\"asset_id\":$A_DB,\"threat\":\"Ransomware chiffrant la base clients et commandes\",\"vulnerability\":\"Sauvegardes non isolees, restauration non testee\",\"probability\":3,\"impact\":5}")
R3=$(r "{\"process_id\":$P_PAY,\"asset_id\":$A_PAY,\"threat\":\"Panne du prestataire de paiement\",\"vulnerability\":\"Un seul prestataire, pas de solution de repli\",\"probability\":3,\"impact\":4}")
R4=$(r "{\"process_id\":$P_PAY,\"asset_id\":$A_HOST,\"threat\":\"Indisponibilite prolongee de l hebergeur\",\"vulnerability\":\"Une seule zone de disponibilite, pas de plan de reprise\",\"probability\":2,\"impact\":5}")
R5=$(r "{\"process_id\":$P_SAV,\"asset_id\":$A_DB,\"threat\":\"Fuite de donnees personnelles clients\",\"vulnerability\":\"Comptes administrateur sans authentification multifacteur\",\"probability\":3,\"impact\":5}")
R6=$(r "{\"process_id\":$P_LIV,\"asset_id\":$A_CARR,\"threat\":\"Defaillance du transporteur\",\"vulnerability\":\"Dependance a un seul transporteur\",\"probability\":4,\"impact\":2}")
R7=$(r "{\"process_id\":$P_STK,\"asset_id\":$A_WEB,\"threat\":\"Erreur de deploiement ou de mise a jour du catalogue\",\"vulnerability\":\"Pas d environnement de test ni de retour arriere\",\"probability\":3,\"impact\":3}")

# --- Traitements (responsables et echeances a definir)
t() { post treatments "{\"risk_id\":$1,\"strategy\":\"$2\",\"action\":\"$3\"}" > /dev/null; }
t $R1 "réduire" "Mettre en place une protection anti-DDoS et un CDN"
t $R2 "réduire" "Isoler les sauvegardes et tester la restauration"
t $R2 "réduire" "Preparer un plan de reprise apres incident"
t $R3 "réduire" "Ajouter un second prestataire de paiement de secours"
t $R4 "transférer" "Souscrire un SLA renforce et un plan de reprise multi-zones"
t $R5 "réduire" "Activer l authentification multifacteur sur tous les comptes admin"
t $R5 "réduire" "Chiffrer les donnees personnelles et auditer les acces"
t $R6 "réduire" "Contractualiser un second transporteur"
t $R7 "réduire" "Creer un environnement de test et une procedure de retour arriere"

echo "Cas e-commerce charge."
curl -s $API/dashboard -H "$H" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['totals']); print(d['risks_by_level'])"
