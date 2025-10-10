import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import plotly.express as px

# =====================
# AUTHENTIFICATION
# =====================
if "login" not in st.session_state:
    st.session_state["login"] = False

def login(username, password):
    users = {"aurore": {"password": "12345", "name": "Aurore Demoulin"}}
    if username in users and password == users[username]["password"]:
        st.session_state["login"] = True
        st.session_state["username"] = username
        st.session_state["name"] = users[username]["name"]
        return True
    return False

if not st.session_state["login"]:
    st.title("🔑 Connexion espace expert-comptable")
    username_input = st.text_input("Identifiant")
    password_input = st.text_input("Mot de passe", type="password")
    if st.button("Connexion"):
        if login(username_input, password_input):
            st.success(f"Bienvenue {st.session_state['name']} 👋")
        else:
            st.error("❌ Identifiants incorrects")
    st.stop()

# =====================
# HEADER NOM UTILISATEUR
# =====================
st.sidebar.success(f"👤 {st.session_state['name']}")

# =====================
# MENU PRINCIPAL
# =====================
pages = ["Accueil", "DATA EDITION", "SOCLE EDITION", "REPARTITION CHARGES FIXES",
         "VISION EDITION", "ISBN VIEW", "ROYALTIES EDITION", "RETURNS EDITION",
         "CASH EDITION", "SYNTHESE GLOBALE"]
page = st.sidebar.selectbox("📂 Menu principal", pages)
if st.sidebar.button("Déconnexion"):
    st.session_state["login"] = False
    st.experimental_rerun()

# =====================
# ACCUEIL
# =====================
if page == "Accueil":
    st.title("👋 Bienvenue dans votre outil d'accompagnement éditorial")
    st.markdown("""
    Cet outil permet de :
    - Importer vos données comptables analytiques (**DATA EDITION**)  
    - Générer un socle pivot multi-logiciels (**SOCLE EDITION**)  
    - Répartir les charges fixes (**REPARTITION CHARGES FIXES**)  
    - Analyser vos ventes et résultats par ISBN (**VISION EDITION & ISBN VIEW**)  
    - Suivre la trésorerie (**CASH EDITION**)  
    - Piloter les droits d’auteurs sur vos livres (**ROYALTIES EDITION**)  
    - Gérer les retours éditeurs/distributeurs (**RETURNS EDITION**)  
    - Obtenir une synthèse globale (**SYNTHESE GLOBALE**)  
    """)

# =====================
# DATA EDITION
# =====================
elif page == "DATA EDITION":
    st.header("📂 DATA EDITION - Import des données analytiques")
    fichier_comptables = st.file_uploader("Sélectionnez votre fichier Excel", type=["xlsx"])
    if fichier_comptables:
        try:
            df = pd.read_excel(fichier_comptables, header=0)
            df.columns = df.columns.str.strip()
            st.write("Colonnes détectées :", list(df.columns))
            st.session_state["df_comptables"] = df
            st.success(f"✅ Fichier chargé : {df.shape[0]} lignes")
            st.dataframe(df.head())
        except Exception as e:
            st.error(f"❌ Erreur lors de l'importation : {e}")

# =====================
# SOCLE EDITION
# =====================
elif page == "SOCLE EDITION":
    st.header("🛠️ SOCLE EDITION - Génération du pivot analytique")
    if "df_comptables" not in st.session_state:
        st.warning("⚠️ Importer d'abord les données via DATA EDITION.")
    else:
        df = st.session_state["df_comptables"].copy()
        
        st.subheader("⚙️ Paramétrage des colonnes du fichier")
        col_compte = st.selectbox("Colonne des comptes", df.columns)
        col_debit = st.selectbox("Colonne Débit", df.columns)
        col_credit = st.selectbox("Colonne Crédit", df.columns)
        col_date = st.selectbox("Colonne Date", df.columns)
        col_famille = st.selectbox("Colonne Famille analytique", df.columns)
        col_code = st.selectbox("Colonne Code analytique / ISBN", df.columns)
        
        col_mapping = {
            col_compte: "Compte",
            col_debit: "Débit",
            col_credit: "Crédit",
            col_date: "Date",
            col_famille: "Famille_Analytique",
            col_code: "Code_Analytique"
        }
        df.rename(columns=col_mapping, inplace=True)
        
        st.subheader("⚙️ Paramétrage des comptes clés")
        comptes_ventes = st.text_input("Numéros de comptes VENTES (ex: 701,706)", "701")
        comptes_retours = st.text_input("Numéros de comptes RETOURS (ex:7097,7098)", "709")
        comptes_remises = st.text_input("Numéros de comptes REMISES LIBRAIRES (ex:7091)", "7091")
        comptes_banques = st.text_input("Numéros de comptes BANQUES (ex:512)", "512")
        comptes_charges = st.text_input("Numéros de comptes CHARGES (ex:6)", "6")
        
        if st.button("Générer le SOCLE"):
            for col in ["Famille_Analytique","Code_Analytique"]:
                if col not in df.columns: df[col] = ""
                else: df[col] = df[col].fillna("")
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            
            pivot = df.groupby(["Compte","Famille_Analytique","Code_Analytique","Date"], as_index=False).agg({"Débit":"sum","Crédit":"sum"})
            st.session_state["df_pivot"] = pivot
            st.session_state["param_comptes"] = {
                "ventes": [x.strip() for x in comptes_ventes.split(",")],
                "retours": [x.strip() for x in comptes_retours.split(",")],
                "remises": [x.strip() for x in comptes_remises.split(",")],
                "banques": [x.strip() for x in comptes_banques.split(",")],
                "charges": [x.strip() for x in comptes_charges.split(",")]
            }
            st.success("✅ SOCLE EDITION généré et comptes paramétrés.")
            st.dataframe(pivot.head(20))

# =====================
# REPARTITION CHARGES FIXES
# =====================
elif page == "REPARTITION CHARGES FIXES":
    st.header("⚙️ Répartition des charges fixes")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        if st.checkbox("J'ai déjà imputé mes charges fixes avec clé de répartition"):
            st.info("Aucune action nécessaire, les charges sont déjà réparties.")
        else:
            st.info("Vous pouvez imputez vos charges fixes ici")
            nb_charges = st.number_input("Nombre de charges fixes à répartir", 1, 20, 1)
            df_charges = []
            for i in range(nb_charges):
                col1, col2 = st.columns(2)
                with col1:
                    libelle = st.text_input(f"Libellé charge {i+1}", f"Charge_{i+1}")
                with col2:
                    montant = st.number_input(f"Montant charge {i+1}", 0.0)
                df_charges.append({"Libelle": libelle, "Montant": montant})
            if st.button("Appliquer répartition"):
                df_charges_df = pd.DataFrame(df_charges)
                st.session_state["df_charges_fixes"] = df_charges_df
                st.success("✅ Répartition des charges appliquée.")

# =====================
# VISION EDITION
# =====================
elif page == "VISION EDITION":
    st.header("📈 VISION EDITION - Dashboard analytique")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        df["Résultat"] = df["Crédit"] - df["Débit"]
        top_isbn = df.groupby("Code_Analytique", as_index=False)["Résultat"].sum().sort_values("Résultat", ascending=False).head(10)
        st.dataframe(top_isbn)
        fig = px.bar(top_isbn, x="Code_Analytique", y="Résultat", title="Top 10 ISBN par résultat net", labels={"Code_Analytique":"ISBN","Résultat":"Résultat net"})
        st.plotly_chart(fig, use_container_width=True)

# =====================
# ISBN VIEW
# =====================
elif page == "ISBN VIEW":
    st.header("💼 ISBN VIEW - Mini compte de résultat par ISBN")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        df_cr = df.groupby("Code_Analytique", as_index=False).agg({"Débit":"sum","Crédit":"sum"})
        df_cr["Résultat"] = df_cr["Crédit"] - df_cr["Débit"]
        st.dataframe(df_cr)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_cr.to_excel(writer, index=False, sheet_name="Mini_CR_ISBN")
        buffer.seek(0)
        st.download_button("📥 Télécharger le mini compte de résultat par ISBN", buffer, file_name="Mini_Compte_Resultat_ISBN.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =====================
# ROYALTIES EDITION
# =====================
elif page == "ROYALTIES EDITION":
    st.header("📚 ROYALTIES EDITION - Droits d’auteurs")
    source = st.radio("Source des données", ["Compta analytique", "Importer fichier BLDD"])
    if source == "Compta analytique":
        st.info("Les données seront récupérées depuis le SOCLE EDITION.")
    else:
        fichier_bldd = st.file_uploader("Importer votre fichier BLDD", type=["xlsx"])
        if fichier_bldd:
            df_bldd = pd.read_excel(fichier_bldd)
            st.session_state["df_bldd"] = df_bldd
            st.success("Fichier BLDD importé.")
    taux_fixe = st.number_input("Taux fixe de droits (%)", value=10.0)
    st.info(f"Taux sélectionné : {taux_fixe}%")

# =====================
# RETURNS EDITION
# =====================
elif page == "RETURNS EDITION":
    st.header("📦 RETURNS EDITION - Gestion des retours")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        param = st.session_state.get("param_comptes", {})
        st.info("⚠️ Assurez-vous que les comptes de ventes, retours et remises sont paramétrés dans SOCLE EDITION.")
        comptes_ventes = param.get("ventes", [])
        comptes_retours = param.get("retours", [])
        comptes_remises = param.get("remises", [])
        
        df = st.session_state["df_pivot"].copy()
        df["Libelle"] = df.get("Libelle", df["Compte"].astype(str))
        
        ca_brut = df[df["Compte"].astype(str).str[:len(comptes_ventes[0])].isin(comptes_ventes)]["Crédit"].sum() if comptes_ventes else 0
        total_retours = df[df["Compte"].astype(str).str[:len(comptes_retours[0])].isin(comptes_retours)]["Débit"].sum() if comptes_retours else 0
        remises = df[df["Compte"].astype(str).str[:len(comptes_remises[0])].isin(comptes_remises)]["Débit"].sum() if comptes_remises else 0
        st.metric("💰 CA Brut", f"{ca_brut:,.0f} €")
        st.metric("📦 Retours", f"{total_retours:,.0f} €")
        st.metric("🏷️ Remises libraires", f"{remises:,.0f} €")
        
        top_retours = df[df["Compte"].astype(str).str[:len(comptes_retours[0])].isin(comptes_retours)].groupby("Code_Analytique", as_index=False)["Débit"].sum().sort_values("Débit", ascending=False)
        st.subheader("Top retours par ISBN")
        st.dataframe(top_retours)

# =====================
# CASH EDITION
# =====================
elif page == "CASH EDITION":
    st.header("💰 CASH EDITION - Trésorerie prévisionnelle")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df_pivot = st.session_state["df_pivot"].copy()

        # Date de départ
        date_debut = st.date_input("Date de départ de la trésorerie", pd.to_datetime("2025-04-01"))

        # Nettoyage et conversion des types
        df_pivot["Compte"] = df_pivot["Compte"].astype(str).str.strip()
        df_pivot["Date"] = pd.to_datetime(df_pivot["Date"], errors="coerce")
        df_pivot["Débit"] = pd.to_numeric(df_pivot["Débit"], errors="coerce").fillna(0)
        df_pivot["Crédit"] = pd.to_numeric(df_pivot["Crédit"], errors="coerce").fillna(0)

        # Calcul du solde de départ (comptes bancaires)
        comptes_bancaires = df_pivot[df_pivot["Compte"].str.startswith("5")]
        solde_depart_df = comptes_bancaires[comptes_bancaires["Date"] <= pd.to_datetime(date_debut)]
        solde_depart_total = solde_depart_df["Crédit"].sum() - solde_depart_df["Débit"].sum()
        st.info(f"Solde de départ : {solde_depart_total:,.2f} €")

        # Paramètres pour prévision
        horizon = st.slider("Horizon de projection (en mois)", 3, 24, 12)
        croissance_ca = st.number_input("Croissance mensuelle du CA (%)", value=2.0) / 100
        evolution_charges = st.number_input("Évolution mensuelle des charges (%)", value=1.0) / 100

        # Flux hors comptes bancaires
        df_flux = df_pivot[~df_pivot["Compte"].str.startswith("5")].copy()
        df_flux = df_flux.dropna(subset=["Date"])
        df_flux = df_flux[df_flux["Date"] >= pd.to_datetime(date_debut)]
        df_flux["Mois"] = df_flux["Date"].dt.to_period("M").astype(str)

        flux_mensuel = df_flux.groupby("Mois").agg({"Débit": "sum", "Crédit": "sum"}).reset_index()
        flux_mensuel["Solde_mensuel"] = flux_mensuel["Crédit"] - flux_mensuel["Débit"]
        flux_mensuel = flux_mensuel.sort_values("Mois")

        dernier_mois = pd.Period(flux_mensuel["Mois"].max(), freq="M") if not flux_mensuel.empty else pd.Period(date_debut, freq="M")
        previsions = []
        ca_actuel = flux_mensuel["Crédit"].iloc[-1] if not flux_mensuel.empty else 0
        charges_actuelles = flux_mensuel["Débit"].iloc[-1] if not flux_mensuel.empty else 0

        for i in range(1, horizon + 1):
            prochain_mois = (dernier_mois + i).strftime("%Y-%m")
            ca_actuel *= (1 + croissance_ca)
            charges_actuelles *= (1 + evolution_charges)
            solde_prevu = ca_actuel - charges_actuelles
            previsions.append({
                "Mois": prochain_mois,
                "Débit": charges_actuelles,
                "Crédit": ca_actuel,
                "Solde_mensuel": solde_prevu
            })

        df_prev = pd.DataFrame(previsions)
        df_tresorerie = pd.concat([flux_mensuel, df_prev], ignore_index=True)
        df_tresorerie["Trésorerie_cumulée"] = solde_depart_total + df_tresorerie["Solde_mensuel"].cumsum()

        fig = px.line(
            df_tresorerie,
            x="Mois",
            y="Trésorerie_cumulée",
            title="📈 Évolution prévisionnelle de la trésorerie",
            markers=True
        )
        fig.update_layout(xaxis_title="Mois", yaxis_title="Trésorerie (€)")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📋 Détail mensuel")
        st.dataframe(df_tresorerie.style.format({
            "Débit": "{:,.0f}",
            "Crédit": "{:,.0f}",
            "Solde_mensuel": "{:,.0f}",
            "Trésorerie_cumulée": "{:,.0f}"
        }))

# =====================
# SYNTHESE GLOBALE
# =====================
elif page == "SYNTHESE GLOBALE":
    st.header("📊 SYNTHESE GLOBALE")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        df["Résultat"] = df["Crédit"] - df["Débit"]
        param = st.session_state.get("param_comptes", {})
        total_ca = df[df["Compte"].astype(str).str.startswith(tuple(param.get("ventes", [])))]["Crédit"].sum() if param else 0
        total_resultat = df["Résultat"].sum()
        st.metric("💰 Chiffre d'affaire total", f"{total_ca:,.0f} €")
        st.metric("📈 Résultat total", f"{total_resultat:,.0f} €")
        st.subheader("Top ISBN par résultat")
        st.dataframe(df.groupby("Code_Analytique", as_index=False)["Résultat"].sum().sort_values("Résultat", ascending=False))

# =====================
# FOOTER - COPYRIGHT
# =====================
st.markdown(
    """
    <style>
    .footer {
        position: fixed;
        bottom: 0;
        width: 100%;
        text-align: center;
        color: #888888;
        font-size: 12px;
        padding: 5px;
        background-color: #f5f5f5;
    }
    </style>
    <div class="footer">
        © 2025 Nicolas CUISSET - Tous droits réservés
    </div>
    """,
    unsafe_allow_html=True
)
