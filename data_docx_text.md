# Extracted text from .docx files in data

## 1. data/Important.docx

Pour le traitement des fichiers, il faut respecter l’ordre et les étapes
Interface en français
Couleur des histogrammes aux couleurs d’Algérie Telecom (Bleu et Vert)
Exportation (selon le filtre) en CSV, Excel et PDF
Les filtres en check box contenant Rechercher et Tout
Appliquer les filtres automatiquement sans appuyer sur le bouton appliquer le filtre
Les taux en %
Les fichiers Anomalies se génèrent automatiquement
Les fichiers Encaissement AR DOT exercice en cours et Encaissement AR DOT exercice N-1 
2 Administrateurs, 1 Super User (qu’on pourra dupliquer exemple 20 super user mais un seul compte) et 60 User DOT
Authentification Admin : (admin , MDP : admin) mot de passe peut être changé.
Authentification Super User : (USER, MDP : 1234) mot de passe ne peut être changé.
Authentification Admin : (Prenom.Nom@ Algerietelecom.dz , MDP : 1234) mot de passe peut être changé.
En cas de perte de mot de passe soit il contacte l’administrateur ou sois il reçoit le nouveau mot de passe via sa boite mail Algerie Telecom
Les 2 Administrateurs et 1 super user ont une visibilité sur toutes les DOT
Les User DOT ont une visibilité uniquement sur leurs DOT (exemple Oran ne peut consulter les KPI de Sétif).
Seules les 2 Administrateurs qui peuvent Uploadé les fichiers.
Le site se déconnecte automatiquement après 15 minutes d’inutilisation.
La partie upload fichier est visible uniquement pour les 2 admins
Site : DashboardDOT.at.dz
Liste des indicateurs :
Parc Corporate NGBSS
Chiffre d’Affaires AR DOT
Encaissement AR DOT
Encaissement exercice en cours
Encaissement exercice N-1
Créance DOT NGBSS
Anomalie
Parc Corporate NGBSS
Chiffre d’Affaires AR DOT
Créance DOT NGBSS

---

## 2. data/Liste des KPI/1-Parc Corporate NGBSS/Traitement à faire Parc Corporate NGBSS (Après traitement).docx

Parc Corporate NGBSS: 
Les Relations :
DOT et Actel Code
Code Customer L2 et Code Customer L3
Subscriber status, Telecom Type et Offer name
Traitement à faire:
Actel Code: « 2B|Centre Algérie Télécom pour les Entreprises HASSI MESSAOUD (2B) », la rattacher à DOT : « DOT OUARGLA »
Actel Code: « 99|Grand Compte », la rattacher à DOT : « DOT SIEGE »
Code Customer L3 : Supprimer toutes les lignes ayant pour catégorie 5 et 57
Offer Type : Supprimer toutes les lignes ayant comme offre Supplementary Offer
Si Offer name contenant Moohtarif la mettre comme anomalie Parc Corporate NGBSS
Offer name : Supprimer toutes les lignes contenant Moohtarif et Solutions Hébergements
Subscriber status : Supprimer toutes les lignes ayant pour catégorie Predeactivated 
Colonne :
OVERVIEW
BY DOT
BY Telecom Type
BY Code Customer L2
BY Code Customer L3
PREVIEW DATA
Filtre : (All, recherche et Checkbox) :
DOT
Actel Code
Subscriber status 
Telecom type
Offer Name
Code Customer L2
Code Customer L3
Visualisation :
OVERVIEW :
BY DOT :
BY Telecom type :
BY Code Customer L2 :
BY Code Customer L3 :

---

## 3. data/Liste des KPI/2-Chiffre d'Affaires AR DOT/Traitement à faire Chiffre d'affaires AR DOT.docx

Chiffre d’affaires AR DOT : 
Les Relations :
DOT (Org Name) et Taux de réalisation C.A (Chiffre Aff Exe Dzd /Objectif) 
Mois (Date GL) et Taux de réalisation C.A (Chiffre Aff Exe Dzd /Objectif) 
Traitement à faire : (Il faut respecter l’ordre) :
Garder que le tableau
Org Name : Supprimer toutes les lignes contenant AT_SIEGE
Org Name : Remplacer DOT_ par vide 
Org Name : Remplacer – et _ par espace
Trier par Org Name, Type Fact et N Fact
Si Cpt Comptable contenant la lettre A et Description (ligne de produit) ne commence pas par @ la mettre comme Anomalie Chiffre d’Affaires AR DOT
Cpt Comptable : Supprimer toutes les lignes contenant la lettre A
Date GL : Garder les lignes ayant l’année la plus récente et supprimer les autres
Prix Uni : Supprimer le « . »
Mnt Ht : Supprimer le « . »
Mnt Tax : Supprimer le « . »
Mnt Ttc : Supprimer le « . »
Chiffre Aff Exe Dzd : Supprimer le « . »
Mettre le séparateur de millier avec deux chiffres après la virgule
Ajouter une colonne TVA (=Mnt Ttc/Mnt Ht) et remplacer l’erreur #DIV/0! Par 0,00
Ajouter une colonne Chiffre Aff Exe Dzd TTC (=Chiffre Aff Exe Dzd * TVA)
Matcher la situation Journal du Chiffre d’Affaires avec la situation Description Cpt Comptable
Faire un TCD (tableau croisée dynamique)
Matcher la situation Journal du Chiffre d’Affaires la situations Objectif C.A
Ajouter une colonne Taux de réalisation C.A (Chiffre Aff Exe Dzd /Objectif) 
Colonne :
OVERVIEW
BY Org Name
BY Description Cpt Comptable
BY Date GL
BY Taux de réalisation C.A
Filtre : (All, recherche et Checkbox) :
DOT (Org Name)
Mois (Date GL)
Taux de réalisation C.A (Chiffre Aff Exe Dzd /Objectif) 
Visualisation :
OVERVIEW
Histogramme combiné (C.A et Objectif par mois de Date GL) :
Histogramme (Description Cpt Comptable) :
Histogramme (DOT et Taux de réalisation C.A) :

---

## 4. data/Liste des KPI/3-Encaissement AR DOT/Traitement à faire Encaissement AR DOT.docx

Encaissement AR DOT : 
Les Relations :
DOT (Organisation) et Taux d’encaissement (Encaissement /Montant Ttc) 
Mois (Date Date Fact) et Taux d’encaissement (Encaissement /Montant Ttc) 
Traitement à faire : (Il faut respecter l’ordre) :
Garder que le tableau
Org Name : Supprimer toutes les lignes contenant AT_SIEGE
Org Name : Remplacer DOT_ par vide
Org Name : Remplacer – et _ par espace 
N FACT : Convertir les cellules en format Nombre (sans virgule)
Trier par Org Name, Typ Fact et N Fact
Ajouter une colonne (Organisation& N Fact& Typ Fact)
Les doublons Organisation& N Fact& Typ Fact :  Remplacer par 0,00 le montant des celulles Montant Ht, Montant Taxe, Montant Ttc, Chiffre Aff Exe
Montant Ht : Remplacer . par ,
Montant Taxe : Remplacer . par ,
Montant Ttc : Remplacer . par ,
Chiffre Aff Exe : Remplacer . par ,
Encaissement : Remplacer . par ,
Mettre le séparateur de millier avec deux chiffres après la virgule
Colonne :
OVERVIEW
BY Organisation
BY Date Fact
BY Taux d’encaissement
Filtre : (All, recherche et Checkbox) :
DOT (Organisation)
Mois (Date Fact)
Taux d’encaissement (Encaissement /Montant Ttc) 
Visualisation :
OVERVIEW
Histogramme combiné (Encaissement et Montant TTC par mois de Date fact) :
Secteur 3D (encaissement / mois) :
Histogramme (DOT et Taux d’encaissement) :

---

## 5. data/Liste des KPI/4-Créance Périodique DOT/Traitement à faire Créance DOT Périodique.docx

Créance Périodique DOT : 
Les Relations :
DOT et ACTEL
ANNEE et MOIS
Produit et CUST_LEV1 et CUST_LEV2 et CUST_LEV3
Traitement à faire : (Il faut respecter l’ordre) :
DOT : Remplacer _ par espace
CUST_LEV1 : Supprimer toutes les lignes contenant Residential, Startup PME TPE et VIP-AT
CUST_LEV2 : Supprimer toutes les lignes contenant Scolaires, Convention, KMS, PME
CUST_LEV2 : Remplacer Ã© par e
CUST_LEV3 : Supprimer toutes les lignes contenant Ligne d'exploitation AT, 
CUST_LEV3 : Remplacer Ã© par e 
PRODUIT : Supprimer toutes les lignes contenant ADSL, FTTX, PSTN, VOIP, X25, XDSL
PRODUIT : Remplacer LS par Specialized Line
INVOICE_AMT : Mettre le séparateur de millier
OPEN_AMT : Mettre le séparateur de millier
TAX_AMT : Mettre le séparateur de millier
INVOICE_AMT_HT : Mettre le séparateur de millier
CREANCE_BRUT : Mettre le séparateur de millier
CREANCE_NET : Mettre le séparateur de millier
CREANCE_HT : Mettre le séparateur de millier
Mettre les cellules vides dans DOT, ACTEL, CUST_LEV1, CUST_LEV2, CUST_LEV3 et PRODUIT comme Anomalie Créance Périodique DOT
Colonne :
OVERVIEW
BY DOT
BY ANNEE
BY PRODUIT
BY CUST_LEV2
Filtre : (All, recherche et Checkbox) :
DOT
ACTEL
ANNEE
MOIS
PRODUIT
CUST_LEV1
CUST_LEV2
CUST_LEV3
Visualisation :
OVERVIEW
BY DOT : Histogramme (DOT et CRANCE_NET) :
BY ANNEE : Histogramme (ANNEE et CRANCE_NET) :
BY PRODUIT Histogramme (PRODUIT et CRANCE_NET) :
BY CUST_LEV2 : Histogramme (CUST_LEV2 et CRANCE_NET) :

---

