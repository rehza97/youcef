# Complete RBAC System - Ready to Use!

## 🎉 What You Get

Your FastAPI + React application now has a **production-ready RBAC system** that:

✅ **Auto-initializes** on first run (zero config needed)
✅ Creates **25 granular permissions** covering all actions
✅ Creates **8 default roles** (admin → SUPER_USER → DOT_USER → specialized → User)
✅ Creates **default admin account** automatically
✅ Protects **all backend endpoints** with permission checks
✅ Protects **frontend routes and UI elements** with permission gates
✅ Supports **DOT (regional) scoping** for data access
✅ Provides **complete documentation** and guides

---

## 🚀 Quick Start (30 Seconds)

```bash
# 1. Start your FastAPI backend
cd fastapi_backend
uvicorn main:app --reload

# Auto-initialization runs → See console output

# 2. Login to frontend
# Navigate to: http://localhost:5173/login
# Username: admin
# Password: Admin123!ChangeMeNow!

# 3. Change password immediately!
# Go to: /change-password
```

**Done!** You now have a fully functional RBAC system.

---

## 📚 Documentation

| Document | Description | When to Read |
|----------|-------------|--------------|
| **[QUICK_START.md](QUICK_START.md)** | 30-second setup + quick reference | Start here! |
| **[RBAC_SETUP_GUIDE.md](RBAC_SETUP_GUIDE.md)** | Complete setup & troubleshooting | Having issues? |
| **[DEFAULT_ROLES_REFERENCE.md](DEFAULT_ROLES_REFERENCE.md)** | Role details & permission mapping | Understanding roles |
| **[RBAC_SYSTEM_SUMMARY.md](RBAC_SYSTEM_SUMMARY.md)** | Executive overview & architecture | Big picture view |
| **[PERMISSION_SYSTEM_IMPLEMENTATION.md](PERMISSION_SYSTEM_IMPLEMENTATION.md)** | Full technical documentation | Deep dive |

**Quick Reference Card:** Start with `QUICK_START.md` - it has everything you need in one page!

---

## 🔐 Default Admin Account

**Automatically created on first run:**

| Field | Value |
|-------|-------|
| Username | `admin` |
| Email | `admin@company.local` |
| Password | `Admin123!ChangeMeNow!` |

**⚠️ IMPORTANT:** Change the password immediately after first login!

### Custom Credentials (Optional)

Set environment variables **before** first start:

```bash
export DEFAULT_ADMIN_USERNAME="youradmin"
export DEFAULT_ADMIN_EMAIL="admin@yourcompany.com"
export DEFAULT_ADMIN_PASSWORD="YourSecurePassword123!"
```

---

## 👥 Default Roles

8 roles automatically created:

| # | Role | Permissions | Use Case |
|---|------|-------------|----------|
| 1 | **admin** | 25 (ALL) | System administrator |
| 2 | **SUPER_USER** | 15 | Senior management |
| 3 | **DOT_USER** | 7 | Regional staff (DOT-scoped) |
| 4 | **Data Analyst** | 7 | Analytics & reporting |
| 5 | **ETL Operator** | 7 | Data engineering |
| 6 | **File Manager** | 4 | Document management |
| 7 | **Moderator** | 6 | Community management |
| 8 | **User** | 3 | Basic end users |

**Admin can customize all roles** via the `/roles` page!

---

## 🔑 Permissions (25 Total)

### User & Role Management (4)
- can_manage_users
- can_view_users
- can_manage_rbac
- can_view_rbac

### Dashboard & Analytics (4)
- can_view_dashboard
- can_view_analytics
- can_export_analytics
- can_view_encaissement_data

### File Management (3)
- can_upload_files
- can_manage_files
- can_manage_own_files

### ETL & Processing (2)
- can_run_etl
- can_view_etl_results

### Messaging (4)
- can_send_messages
- can_manage_messages
- can_manage_notifications
- can_broadcast

### Settings (2)
- can_manage_settings
- can_view_settings

### DOT & Data (5)
- can_view_dot_data
- can_view_all_dots
- can_manage_dots
- can_view_park_data
- can_manage_park_data

### Audit (1)
- can_view_audit_logs

---

## 🎯 Common Tasks

### Assign Role to User
1. Login as admin
2. Navigate to `/users`
3. Click "Edit" on a user
4. Select role from dropdown
5. Save

### Create Custom Role
1. Login as admin
2. Navigate to `/roles`
3. Click "Add Role"
4. Enter name and description
5. Select permissions (searchable multi-select)
6. Save

### Assign User to DOT Region
```bash
# Only admins can do this via API
POST /api/parks/dots/{dot_id}/assign-user/{user_id}
```

---

## 🛠️ What's Implemented

### Backend ✅
- ✅ Permission service with admin override
- ✅ 25 permissions seeded
- ✅ 8 default roles with permission assignments
- ✅ All endpoints protected with permission checks
- ✅ DOT-based regional scoping
- ✅ Auto-initialization on startup
- ✅ Auto-creation of admin account

### Frontend ✅
- ✅ `<PermissionRoute>` for route protection
- ✅ `<PermissionGate>` for UI element gating
- ✅ `usePermission` hook for conditional logic
- ✅ Protected routes: /users, /roles, /permissions, /settings, /encaissement
- ✅ Permission-gated buttons on Users and Roles pages

### Files Created
```
Backend:
├── fastapi_backend/
│   ├── core/rbac_init.py                    # Auto-init + admin creation
│   ├── services/permission_service.py        # Permission logic
│   └── migrations/
│       ├── seed_permissions.py               # 25 permissions
│       ├── seed_default_roles.py             # 8 roles
│       └── init_rbac.py                      # Master script

Frontend:
├── frontend/src/
│   ├── components/auth/PermissionRoute.jsx   # Permission components
│   ├── hooks/usePermission.js                # Permission hook
│   └── App.jsx                               # Protected routes

Documentation:
├── QUICK_START.md                            # Quick reference
├── RBAC_SETUP_GUIDE.md                       # Setup guide
├── DEFAULT_ROLES_REFERENCE.md                # Role details
├── RBAC_SYSTEM_SUMMARY.md                    # Executive summary
├── PERMISSION_SYSTEM_IMPLEMENTATION.md       # Full docs
└── README_RBAC.md                            # This file
```

---

## ✅ Verification

Run these checks after starting your backend:

```bash
# 1. Check backend started successfully
curl http://localhost:8000/api/health

# 2. Login with default admin
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin123!ChangeMeNow!"}'

# 3. Check permissions created (use token from step 2)
curl http://localhost:8000/api/permissions/ \
  -H "Authorization: Bearer YOUR_TOKEN"
# Should return 25 permissions

# 4. Check roles created
curl http://localhost:8000/api/roles/ \
  -H "Authorization: Bearer YOUR_TOKEN"
# Should return 8 roles

# 5. Check admin has all permissions
curl http://localhost:8000/api/roles/1/permissions \
  -H "Authorization: Bearer YOUR_TOKEN"
# Should return 25 permissions for admin role
```

**All passing?** ✅ You're good to go!

---

## 🔒 Security Features

✅ **Server-side enforcement** - All endpoints protected
✅ **Client-side defense** - UI elements hidden (defense in depth)
✅ **Admin override** - Admin bypasses all permission checks
✅ **DOT scoping** - Regional data isolation
✅ **Password security** - Bcrypt hashing
✅ **Token-based auth** - JWT access tokens
✅ **Audit ready** - Permission checks logged

---

## 📊 System Status

| Component | Status |
|-----------|--------|
| Backend Permission System | ✅ Complete |
| Frontend Permission System | ✅ Complete |
| Default Roles | ✅ 8 Created |
| Default Permissions | ✅ 25 Created |
| Admin Account | ✅ Auto-created |
| Auto-initialization | ✅ Working |
| DOT Scoping | ✅ Functional |
| Documentation | ✅ Complete |
| Production Ready | ✅ Yes |

---

## 🆘 Troubleshooting

### Backend won't start
```bash
# Check Python dependencies
pip install -r requirements.txt

# Check database connection
# Verify DATABASE_URL in .env
```

### Admin login fails
```bash
# Check console logs for admin credentials
# Default: admin / Admin123!ChangeMeNow!

# Or create manually:
python
>>> from core.rbac_init import create_default_admin
>>> from database.connection import SessionLocal
>>> create_default_admin(SessionLocal())
```

### Permission checks failing
```bash
# Re-run initialization
cd fastapi_backend
python -m migrations.init_rbac
```

### Frontend shows 403 errors
1. Check user has role assigned
2. Verify role has required permission
3. Check browser console for errors
4. Hard refresh (Ctrl+Shift+R)

**Still stuck?** See `RBAC_SETUP_GUIDE.md` troubleshooting section

---

## 🎓 Next Steps

### For Admins
1. ✅ Login and change password
2. ✅ Review default roles at `/roles`
3. ✅ Create additional users at `/users`
4. ✅ Assign roles to users
5. ✅ Customize roles as needed

### For Developers
1. ✅ Read `PERMISSION_SYSTEM_IMPLEMENTATION.md`
2. ✅ Learn how to add permission checks to new endpoints
3. ✅ Learn how to protect new frontend routes
4. ✅ Understand DOT scoping for regional data

### For Organizations
1. ✅ Map your org structure to roles
2. ✅ Customize default roles or create new ones
3. ✅ Set up DOT regions if using regional access
4. ✅ Train staff on permission system

---

## 📞 Support

**Documentation:**
- Quick Start: `QUICK_START.md`
- Setup Guide: `RBAC_SETUP_GUIDE.md`
- Technical Docs: `PERMISSION_SYSTEM_IMPLEMENTATION.md`

**Common Issues:**
- Admin login → Check console logs for credentials
- Permission errors → Verify role assignments
- DOT access → Ensure DOT assignment for DOT_USER role

---

## 🎉 You're Ready!

Your RBAC system is **fully operational** and **production-ready**!

**Next:** Start backend → Login as admin → Explore!

```bash
cd fastapi_backend && uvicorn main:app --reload
```

**Questions?** Check the docs or review console logs for helpful info.

---

**Version:** 1.0
**Status:** Production Ready
**Last Updated:** Auto-generated on system initialization









i have 4 dasbhaord right ? each dasbaird calculate kpis used data saved from certain files i need to investigate how the data
from the park for park dasbhaord and Chiffre d'Affaires relay on AT___Journal_du_Chiffre_d_affa_180525 and Description Cpt
Comptable and Objectif C.A then there is the third dasbhaord Encaissement AR DOT that relay on follozing files
AT___Etat_des_Factures_AR_et_e_120525 2024 and AT___Etat_des_Factures_AR_et_e_120525 2025 and finaly Créance Périodique DOT
dasbhaord relay on DG_canva_creance_2023_2024 do u need headers and data simple for each file ?

⏺ Yes, exactly! I need headers and sample data for each file to investigate the data flow. This will help me trace:

  1. File → ETL Processing (how data is transformed)
  2. ETL → Database (which columns map to which tables)
  3. Database → Dashboard KPIs (how KPIs are calculated)

  Let me create a structured analysis plan:

⏺ Please provide headers and 2-3 rows of sample data for each file:

  Dashboard 1: Chiffre d'Affaires (Revenue)

  📄 File: AT___Journal_du_Chiffre_d_affa_180525
  - Headers please
  - Sample rows (especially columns: "Description Cpt Comptable", "Objectif C.A", and any date/amount columns)

  Dashboard 2: Encaissement AR DOT

  📄 File: AT___Etat_des_Factures_AR_et_e_120525 2024
  - Headers please
  - Sample rows

  📄 File: AT___Etat_des_Factures_AR_et_e_120525 2025
  - Headers please
  - Sample rows

  Dashboard 3: Créance Périodique DOT

  📄 File: DG_canva_creance_2023_2024
  - Headers please
  - Sample rows

  Dashboard 4: Park Dashboard

  Just to confirm - does the park dashboard use the park data you already showed me, or are there other files involved?

  ---
  Once you provide these, I'll:
  1. Trace the ETL flow for each file
  2. Map columns to database tables
  3. Identify KPI calculation logic
  4. Create a data lineage diagram
  5. Spot any missing/incomplete mappings





1-Parc Corporate NGBSS has : 
  Daoud Youcef_Subscriber Park Report_Rapport sur le Parc des abonns_2025-07-07_09-34-00 : 
    simple : 
      Extraction Date_Date d ‘extraction	DOT	Actel Code_Code d’actel	Code Customer L1_Code Catégorie level 1	Description Customer L1_Nom du Catégorie level 1	Code Customer L2_Code Catégorie level 2	Description Customer L2_Nom du Catégorie level 2	Code Customer L3_Code Catégorie level 3	Description Customer L3_Nom du Catégorie level 3	Telecom type_SERVICE / PRODUIT	Offer Type_Type d’offre	Offer name_Nom de l’offre	Rental Fees_Frais d’abonnement	Customer code_NCLI	Service number_ND	Related Service Number_Numero de service correspondant	USERNAME_Nom d’utilisateur	Subscriber status_Status de l’abonne	Status date_Date du statut	Creation Date_Date de creation	Active Date_Date d'activation	CSR Name_Nom CSR	Department Name_Nom de département1	State_Wilaya	Area_Daira	Town_Commune	Grid_Quartier	Street_Voie	Street Number_Numero De Voie	Building No._Batiment	Unit_Escalier	Floor_Etage	House No._Numero de maison	Additional Address Information_Complément d'adresse	Customer full name_NOM ET PRENOM	Province_Wilaya	District_Daira	City_Commune	Postal Code_Code postal	Expiry Date_Date d’expiration	ICCID_N° SIM	IMSI_IMSI	Contact number_Numéro de contact
07.07.2025 09:07:02	DOT CONSTANTINE	O2|ACTEL Martyrs (O2)	02	Corporate	301	Administration & organization	4	Public service	PSTN	Primary Offer	MIXTEAbonnement standard Corporate	1,50	70000024200049	31886544	UNKNOWN	21331886544	Active	UNKNOWN	01.11.1988 12:11:00	31.10.1988 11:10:01	Root Operator	Internal system	Constantine	UNKNOWN	CONSTANTINE	BAB EL KANTARA	CFPA	UNKNOWN	UNKNOWN	UNKNOWN	UNKNOWN	UNKNOWN	.,CHUC	.  HOPITAL IBN BADIS	Constantine	UNKNOWN	CONSTANTINE	25000	UNKNOWN	UNKNOWN	UNKNOWN	UNKNOWN
07.07.2025 09:07:02	DOT CONSTANTINE	O2|ACTEL Martyrs (O2)	02	Corporate	302	Officially agreed professional customer	96	Officially agreed MICLAT	PSTN	Primary Offer	Abonnement standard PSTN MICLAT	1,50	70000062200781	31810172	UNKNOWN	21331810172	Active	UNKNOWN	25.03.2007 11:03:31	25.03.2007 10:03:32	Root Operator	Internal system	Constantine	UNKNOWN	CONSTANTINE	NONE	Constantine	UNKNOWN	UNKNOWN	UNKNOWN	UNKNOWN	UNKNOWN	.,AEROPORT MED BOUDIAF	.  DTN Wilaya	Constantine	CONSTANTINE	CONSTANTINE CITE DAKSI	25003	UNKNOWN	UNKNOWN	UNKNOWN	UNKNOWN
07.07.2025 09:07:02		2B|Centre Algérie Télécom pour les Entreprises HASSI MESSAOUD (2B)	02	Corporate	302	Officially agreed professional customer	165	Officialy agreed large company	PSTN	Primary Offer	MIXTEAbonnement exceptionnel	0,00	70000128500001	99029345	UNKNOWN	21399029345	Active	UNKNOWN	23.05.2012 08:05:56	UNKNOWN	Root Operator	Internal system	Ouargla	UNKNOWN	HASSI MESSAOUD	NONE	HASSI MESSAOUD	UNKNOWN	UNKNOWN	UNKNOWN	UNKNOWN	UNKNOWN	.	SHDP  IRARA  INT	Ouargla	OUARGLA	HASSI MESSAOUD	30001	UNKNOWN	UNKNOWN	UNKNOWN	UNKNOWN
07.07.2025 09:07:02		2B|Centre Algérie Télécom pour les Entreprises HASSI MESSAOUD (2B)	02	Corporate	302	Officially agreed professional customer	165	Officialy agreed large company	PSTN	Primary Offer	MIXTEAbonnement exceptionnel	0,00	70000235500001	99015124	UNKNOWN	21399015124	Active	UNKNOWN	16.02.2012 02:02:04	UNKNOWN	Root Operator	Internal system	Ouargla	UNKNOWN	HASSI MESSAOUD	NONE	HASSI MESSAOUD	UNKNOWN	UNKNOWN	UNKNOWN	UNKNOWN	UNKNOWN	.	INT  STUDIO 511  INT	Ouargla	OUARGLA	HASSI MESSAOUD	30001	UNKNOWN	UNKNOWN	UNKNOWN	UNKNOWN
2-Chiffre d'Affaires AR DOT : 
  AT___Journal_du_Chiffre_d_affa_180525 : 
    sample : 
      Org Name	Origine	N Fact	Typ Fact	Date Fact	N Client	Client	Delai Paie	Devise	Obj Fact	Cpt Comptable	Date facture GL	Date GL	Periode de facturation	Reference	Termine Flag	Tax Amount	Creer Par	N Ligne	Description (ligne de produit)	Uom	Qte	Prix Uni	Taux Change	Mnt Ht	Tax	Mnt Tax	Mnt Ttc	Memo Line Id	Chiffre Aff Exe Dzd
AT_SIEGE	DCC	1	CM	18/02/2025	1152	AMBASSADE DE BRESIL		DZD	Facture d'avoir sur la TVA pour la facture N°201/CORP/2025 (Attestation d'éxoneration TVA)	7062110000	18/02/2025	18/02/2025	LA PERIODE DU 01-JAN-2025 AU 31-DEC-2025	AVOIR	Y	-38756.49	AHENNI	1	Liaison Spécialisée Internet 20 Mbps	Mois	0	100.000,00		0,00		0,00	0,00		0,00
AT_SIEGE	DCC	1	CM	18/02/2025	1152	AMBASSADE DE BRESIL		DZD	Facture d'avoir sur la TVA pour la facture N°201/CORP/2025 (Attestation d'éxoneration TVA)	7068200000	18/02/2025	18/02/2025	LA PERIODE DU 01-JAN-2025 AU 31-DEC-2025	AVOIR	Y	-38756.49	AHENNI	2	Location Support Fibre Optique 1<D<=3 KM (Engagement de 36 Mois)	Mois	0	16.998,46		0,00		0,00	0,00		0,00
AT_SIEGE	DINR	1	CM	10/03/2025	2988	Wataniya Telecom Algerie SPA		DZD	Facture d'annulation sur la facture N°125/DINR/2025	7067411000	10/03/2025	10/03/2025	LA PERIODE DU 01-JAN-2025 AU 31-JAN-2025	Convention d'Interconnexion du 02-08-2022	Y	-4390000.83	AMENANI	1	Trafic d'interconnexion national	Minute	-6601505	3,50		-23.105.267,50		-4.390.000,82	-27.495.268,32		-23.105.267,50
AT_SIEGE	DII	1	INV	02/01/2025	177393	Gateway Communications S.A.S	30 NET	EUR	Facture à établir	7002000000	02/01/2025	02/01/2025	LA PERIODE DU 01-DEC-2024 AU 31-DEC-2024	BC	Y	0	YDAHMANI	1	MPLS pour le client  AMBASSADE ESPAGNE 04 Mbits SMW4 Alger-Marseille	Mois	1	2.412,00	141,20	2.412,00		0,00	2.412,00		340.573,68
AT_SIEGE	DII	1	INV	02/01/2025	177393	Gateway Communications S.A.S	30 NET	EUR	Facture à établir	7002000000	02/01/2025	02/01/2025	LA PERIODE DU 01-DEC-2024 AU 31-DEC-2024	BC	Y	0	YDAHMANI	2	MPLS pour le client  AMBASSADE ESPAGNE 04 Mbits SMW4 Alger-Marseille	Mois	1	3.092,00	141,20	3.092,00		0,00	3.092,00		436.589,47
  Description Cpt Comptable : 
     Cpt Comptable 	Description Cpt Comptable	AUT_BDG	AUT_IMP	TYPE_CPTE	AUXIL	LET
 7 	COMPTES DE PRODUITS	Non	Non	Produits	Non	Non
 70 	VENTES DE MARCHANDISES ET DE PRODUITS FABRIQUÉS, VENTES DE PRESTATIONS DE SERVICE ET PRODUITS ANNEXES	Non	Non	Produits	Non	Non
 700 	VENTES DE MARCHANDISES	Non	Non	Produits	Non	Non
 7,001 	APPAREILS TELEPHONIQUES	Non	Non	Produits	Non	Non
 700100000A 	APPAREILS TELEPHONIQUES	Oui	Oui	Produits	Non	Oui   
  Objectif C.A : 
    DOT	 Objectif C.A 
ADRAR	 150,000,000.00 
AIN DEFLA	 30,000,000.00 
AIN TEMOUCHENT	 30,000,000.00 
ALGER CENTRE	 61,000,000.00 
ALGER EST	 120,000,000.00 
ALGER OUEST	 120,000,000.00 
ANNABA	 120,000,000.00  
3-Encaissement AR DOT : 
  AT___Etat_des_Factures_AR_et_e_120525 2024 :
    Organisation	Source	N Fact	Typ Fact	Date Fact	Client	N Client	Obj Fact	Periode	Ref	Termine Flag	Creer Par	Montant Ht	Montant Taxe	Montant Ttc	Chiffre Aff Exe	Encaissement	N Rglt	Date Rglt	Facture Avoir / Annulation
AT_SIEGE	DCC	‭1‬	INV	18/02/2024	AMBASSADE DU SENEGAL	1179	Redevance de la Location de l'équipement Firewall	LA PERIODE DU 16-JAN-2024 AU 15-FEV-2024	Bon de Commande	Y	AHENNI	14000	2660	16660	14000	16660	4980077	21 févr. 24	
AT_SIEGE	DII	‭1‬	INV	04/01/2024	WEBHELP SPA ALGERIE	2993	Redevence mensuelle liaison louée internationale LLI	LA PERIODE DU 01-DEC-2023 AU 31-DEC-2023	BC	Y	YDAHMANI	2450000	465500	2915500	2450000	2915500	8_VRI99058631	24 janv. 24	
AT_SIEGE	DII	‭1‬	CM	11/02/2024	Orange International Carriers	2392	Trafic International Mensuel	LA PERIODE DU 01-JAN-2024 AU 31-JAN-2024	Rate Sheets Q1/2024	Y	YDAHMANI	-807046.07	0	-807046.07	-807046.07	0			0
AT_SIEGE	DINR	‭1‬	CM	22/01/2024	Optimum Télécom Algérie	176380	AVOIR	LA PERIODE DU 01-DEC-2023 AU 31-DEC-2023	Convention d'Interconnexion du 02-08-2022	Y	AMENANI	-6064949.6	-1152340.42	-7217290.02	-6064949.6	0			0
AT_SIEGE	DCC	‭1‬	CM	11/03/2024	CENTRE DE DEVELOPPEMENT DES TECHNOLOGIES AVANCEES CDTA	1386	Annulation partiel dont le marché à commande ne comrend pas l'article de la location support FO		Client professionnel	Y	LOULKADI	-50995.38	-9689.12	-60684.5	-50995.38	0			0  
  AT___Etat_des_Factures_AR_et_e_120525 2025 : 
    Organisation	Source	N Fact	Typ Fact	Date Fact	Client	N Client	Obj Fact	Periode	Ref	Termine Flag	Creer Par	Montant Ht	Montant Taxe	Montant Ttc	Chiffre Aff Exe	Encaissement	N Rglt	Date Rglt	Facture Avoir / Annulation
AT_SIEGE	DCC	‭1‬	CM	18/02/2025	AMBASSADE DE BRESIL	1152	Facture d'avoir sur la TVA pour la facture N°201/CORP/2025 (Attestation d'éxoneration TVA)	LA PERIODE DU 01-JAN-2025 AU 31-DEC-2025	AVOIR	Y	AHENNI	0	-38756.49	-38756.49	0	0			0
AT_SIEGE	DII	‭1‬	INV	02/01/2025	Gateway Communications S.A.S	177393	Facture à établir	LA PERIODE DU 01-DEC-2024 AU 31-DEC-2024	BC	Y	YDAHMANI	22599	0	22599	22599				22599
AT_SIEGE	DINR	‭1‬	INV	02/01/2025	SARL OFFSHORE INSHORE SERVICE TELECOM	2372	FACTURATION	LA PERIODE DU 01-DEC-2024 AU 31-DEC-2024	30/11/2022	Y	SBEHLOUL	77760	0	77760	77760	77760	900002_VR668371	27 janv. 25	
AT_SIEGE	DINR	‭1‬	CM	10/03/2025	Wataniya Telecom Algerie SPA	2988	Facture d'annulation sur la facture N°125/DINR/2025	LA PERIODE DU 01-JAN-2025 AU 31-JAN-2025	Convention d'Interconnexion du 02-08-2022	Y	AMENANI	-23105267.5	-4390000.83	-27495268.33	-23105267.5	0			0
DOT_ADRAR	16_STANDARD FACTURES	‭1‬	CM	21/01/2025	APC TIMMI	229447	AVOIR SUR FACTURE RATTACHEMENT SUPPORT FO DES ANNEXES APC		06/SDC/DC/DO-1/2025	Y	RHARROUZ	-662732.01	0	-662732.01	-662732.01	0			0    
4-Créance Périodique DOT : 
  DOT;ACTEL;MOIS;ANNEE;SUBS_STATUS;PRODUIT;CUST_LEV1;CUST_LEV2;CUST_LEV3;INVOICE_AMT;OPEN_AMT;TAX_AMT;INVOICE_AMT_HT;DISPUTE_AMT;DISPUTE_TAX_AMT;DISPUTE_NET_AMT;CREANCE_BRUT;CREANCE_NET;CREANCE_HT			
Setif;43|ACTEL El Eulma (43);02;2025;;;Corporate;KMS;KMS;287	54;286	93;45	91;241
Alger_Ouest;71|ACTEL Cheraga (71);03;2024;B02;PSTN;Residential;"Client Ordinaire ";Résidentiel;22059	42;21684	42;3522	09;18537
Jijel;L1|ACTEL Taher (L1);03;2025;;;Corporate;KMS;KMS;1875	79;1875	79;299	5;1576
Mostaganem;N8|ACTEL Mesra(N8);05;2024;B03;PSTN;Startup PME TPE;TPE;"Non-profit association ";357;357;57;300;0;0;0;357;357;300			
Timimoune;90|ACTEL Timimoune;07;2023;B03;PSTN;Residential;Client Exceptionnel;Conventionné DGSN;1428;1428;228;1200;0;0;0;1428;1428;1200			
  i need u to read it line by line make a detailed todo list then start working systimaticly



  Todos
  ☐ Collect headers and sample data for all 4 dashboard source files
  ☐ Map Park dashboard data flow and dependencies
  ☐ Map Chiffre d'Affaires dashboard data flow (Journal_du_Chiffre_d_affa file)
  ☐ Map Encaissement AR DOT dashboard data flow (2 Etat_des_Factures files)
  ☐ Map Créance Périodique DOT dashboard data flow (canva_creance file)
  ☐ Document complete data lineage for all dashboards





1-Parc Corporate NGBSS 
    rules (Traitement à faire Parc Corporate NGBSS (Après traitement)) :
      Parc Corporate NGBSS: 

1-Les Relations :

DOT et Actel Code
Code Customer L2 et Code Customer L3
Subscriber status, Telecom Type et Offer name

2-Traitement à faire:

Actel Code: « 2B|Centre Algérie Télécom pour les Entreprises HASSI MESSAOUD (2B) », la rattacher à DOT : « DOT OUARGLA »
Actel Code: « 99|Grand Compte », la rattacher à DOT : « DOT SIEGE »
Code Customer L3 : Supprimer toutes les lignes ayant pour catégorie 5 et 57
Offer Type : Supprimer toutes les lignes ayant comme offre Supplementary Offer
Si Offer name contenant Moohtarif la mettre comme anomalie Parc Corporate NGBSS
Offer name : Supprimer toutes les lignes contenant Moohtarif et Solutions Hébergements
Subscriber status : Supprimer toutes les lignes ayant pour catégorie Predeactivated 

3-Colonne :

OVERVIEW
BY DOT
BY Telecom Type
BY Code Customer L2
BY Code Customer L3
PREVIEW DATA

4-Filtre : (All, recherche et Checkbox) :

DOT
Actel Code
Subscriber status 
Telecom type
Offer Name
Code Customer L2
Code Customer L3









5-Visualisation :

OVERVIEW :



BY DOT :

BY Telecom type :


BY Code Customer L2 :


BY Code Customer L3 :


2-Chiffre d'Affaires AR DOT
  rules(Traitement à faire Chiffre d'affaires AR DOT) :
    Chiffre d’affaires AR DOT : 

1-Les Relations :

DOT (Org Name) et Taux de réalisation C.A (Chiffre Aff Exe Dzd /Objectif) 
Mois (Date GL) et Taux de réalisation C.A (Chiffre Aff Exe Dzd /Objectif) 

2-Traitement à faire : (Il faut respecter l’ordre) :

Garder que le tableau
Org Name : Supprimer toutes les lignes contenant AT_SIEGE
Org Name : Remplacer DOT_ par vide 
Org Name : Remplacer – et _ par espace
Trier par Org Name, Type Fact et N Fact
Si Cpt Comptable contenant la lettre A et Description (ligne de produit) ne commence pas par @ la mettre comme Anomalie Chiffre d’Affaires AR DOT
Cpt Comptable : Supprimer toutes les lignes contenant la lettre A
Date GL : Garder les lignes ayant l’année la plus récente et supprimer les autres
Prix Uni : Supprimer le « . »
Mnt Ht : Supprimer le « . »
Mnt Tax : Supprimer le « . »
Mnt Ttc : Supprimer le « . »
Chiffre Aff Exe Dzd : Supprimer le « . »
Mettre le séparateur de millier avec deux chiffres après la virgule
Ajouter une colonne TVA (=Mnt Ttc/Mnt Ht) et remplacer l’erreur #DIV/0! Par 0,00
Ajouter une colonne Chiffre Aff Exe Dzd TTC (=Chiffre Aff Exe Dzd * TVA)
Matcher la situation Journal du Chiffre d’Affaires avec la situation Description Cpt Comptable
Faire un TCD (tableau croisée dynamique)
Matcher la situation Journal du Chiffre d’Affaires la situations Objectif C.A
Ajouter une colonne Taux de réalisation C.A (Chiffre Aff Exe Dzd /Objectif) 

3-Colonne :

OVERVIEW
BY Org Name
BY Description Cpt Comptable
BY Date GL
BY Taux de réalisation C.A

4-Filtre : (All, recherche et Checkbox) :

DOT (Org Name)
Mois (Date GL)
Taux de réalisation C.A (Chiffre Aff Exe Dzd /Objectif) 



5-Visualisation :

OVERVIEW


Histogramme combiné (C.A et Objectif par mois de Date GL) :


Histogramme (Description Cpt Comptable) :





Histogramme (DOT et Taux de réalisation C.A) :
3-Encaissement AR DOT 
  rules(Traitement à faire Encaissement AR DOT) :
    Encaissement AR DOT : 

1-Les Relations :

DOT (Organisation) et Taux d’encaissement (Encaissement /Montant Ttc) 
Mois (Date Date Fact) et Taux d’encaissement (Encaissement /Montant Ttc) 

2-Traitement à faire : (Il faut respecter l’ordre) :

Garder que le tableau
Org Name : Supprimer toutes les lignes contenant AT_SIEGE
Org Name : Remplacer DOT_ par vide
Org Name : Remplacer – et _ par espace 
N FACT : Convertir les cellules en format Nombre (sans virgule)
Trier par Org Name, Typ Fact et N Fact
Ajouter une colonne (Organisation& N Fact& Typ Fact)
Les doublons Organisation& N Fact& Typ Fact :  Remplacer par 0,00 le montant des celulles Montant Ht, Montant Taxe, Montant Ttc, Chiffre Aff Exe
Montant Ht : Remplacer . par ,
Montant Taxe : Remplacer . par ,
Montant Ttc : Remplacer . par ,
Chiffre Aff Exe : Remplacer . par ,
Encaissement : Remplacer . par ,
Mettre le séparateur de millier avec deux chiffres après la virgule

3-Colonne :

OVERVIEW
BY Organisation
BY Date Fact
BY Taux d’encaissement

4-Filtre : (All, recherche et Checkbox) :

DOT (Organisation)
Mois (Date Fact)
Taux d’encaissement (Encaissement /Montant Ttc) 











5-Visualisation :

OVERVIEW


Histogramme combiné (Encaissement et Montant TTC par mois de Date fact) :


Secteur 3D (encaissement / mois) :



Histogramme (DOT et Taux d’encaissement) :

4-Créance Périodique DOT:
  rules (Traitement à faire Créance DOT Périodique) :
    Créance Périodique DOT : 

1-Les Relations :

DOT et ACTEL
ANNEE et MOIS
Produit et CUST_LEV1 et CUST_LEV2 et CUST_LEV3

2-Traitement à faire : (Il faut respecter l’ordre) :

DOT : Remplacer _ par espace
CUST_LEV1 : Supprimer toutes les lignes contenant Residential, Startup PME TPE et VIP-AT
CUST_LEV2 : Supprimer toutes les lignes contenant Scolaires, Convention, KMS, PME
CUST_LEV2 : Remplacer Ã© par e
CUST_LEV3 : Supprimer toutes les lignes contenant Ligne d'exploitation AT, 
CUST_LEV3 : Remplacer Ã© par e 
PRODUIT : Supprimer toutes les lignes contenant ADSL, FTTX, PSTN, VOIP, X25, XDSL
PRODUIT : Remplacer LS par Specialized Line
INVOICE_AMT : Mettre le séparateur de millier
OPEN_AMT : Mettre le séparateur de millier
TAX_AMT : Mettre le séparateur de millier
INVOICE_AMT_HT : Mettre le séparateur de millier
CREANCE_BRUT : Mettre le séparateur de millier
CREANCE_NET : Mettre le séparateur de millier
CREANCE_HT : Mettre le séparateur de millier
Mettre les cellules vides dans DOT, ACTEL, CUST_LEV1, CUST_LEV2, CUST_LEV3 et PRODUIT comme Anomalie Créance Périodique DOT

3-Colonne :

OVERVIEW
BY DOT
BY ANNEE
BY PRODUIT
BY CUST_LEV2

4-Filtre : (All, recherche et Checkbox) :
DOT
ACTEL
ANNEE
MOIS
PRODUIT
CUST_LEV1
CUST_LEV2
CUST_LEV3



5-Visualisation :

OVERVIEW


BY DOT : Histogramme (DOT et CRANCE_NET) :







BY ANNEE : Histogramme (ANNEE et CRANCE_NET) :





BY PRODUIT Histogramme (PRODUIT et CRANCE_NET) :






BY CUST_LEV2 : Histogramme (CUST_LEV2 et CRANCE_NET) :



