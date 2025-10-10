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
pages = ["Accueil", "DATA EDITION", "SOCLE EDITION", "VISION EDITION", "ISBN VIEW",
         "CASH EDITION", "ROYALTIES EDITION", "RETURNS EDITION", "SYNTHESE GLOBALE"]
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
    - Analyser vos ventes et résultats par ISBN (**VISION EDITION & ISBN VIEW**)  
    - Suivre la trésorerie (**CASH EDITION**)  
    - Piloter les droits d’auteurs sur vos livres (**ROYALTIES EDITION**)  
    - Gérer les retours éditeurs/distributeurs (**RETURNS EDITION**)  
    - Synthèse globale (**SYNTHESE GLOBALE**)  
    Utilisez le menu à gauche pour naviguer entre les modules.
    """)
    st.stop()

# =====================
# DATA EDITION
# =====================
if page == "DATA EDITION":
    st.header("📂 DATA EDITION - Import des données analytiques")
    fichier_comptables = st.file_uploader("Sélectionnez votre fichier Excel", type=["xlsx"])
    if fichier_comptables:
        try:
            df = pd.read_excel(fichier_comptables, header=0)
            df.columns = df.columns.str.strip()
            st.write("Colonnes détectées :", list(df.columns))
            # Paramétrage des colonnes
            col_mapping = {}
            st.subheader("Paramétrage des colonnes")
            col_mapping["Compte"] = st.selectbox("Colonne compte", options=df.columns)
            col_mapping["Débit"] = st.selectbox("Colonne débit", options=df.columns)
            col_mapping["Crédit"] = st.selectbox("Colonne crédit", options=df.columns)
            col_mapping["Famille_Analytique"] = st.selectbox("Colonne famille analytique", options=df.columns)
            col_mapping["Code_Analytique"] = st.selectbox("Colonne code analytique (ISBN)", options=df.columns)
            col_mapping["Date"] = st.selectbox("Colonne date", options=df.columns)
            
            df.rename(columns=col_mapping, inplace=True)
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
        st.subheader("Paramétrage des comptes clés")
        ventes = st.text_input("Compte(s) ventes brutes (ex: 701000000,701100000)", "701100000")
        retours = st.text_input("Compte(s) retours (ex: 709000000)", "709000000")
        remises = st.text_input("Compte(s) remises libraires (ex: 709100000)", "709100000")
        provisions = st.text_input("Compte(s) provision sur retours (ex: 681000000)", "681000000")
        st.session_state["param_comptes"] = {
            "ventes": [c.strip() for c in ventes.split(",")],
            "retours": [c.strip() for c in retours.split(",")],
            "remises": [c.strip() for c in remises.split(",")],
            "provisions": [c.strip() for c in provisions.split(",")]
        }
        
        if st.button("Générer le SOCLE"):
            for col in ["Famille_Analytique","Code_Analytique"]:
                if col not in df.columns: df[col] = ""
                else: df[col] = df[col].fillna("")
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            pivot = df.groupby(["Compte","Famille_Analytique","Code_Analytique","Date"], as_index=False).agg({"Débit":"sum","Crédit":"sum"})
            st.session_state["df_pivot"] = pivot
            st.success("✅ SOCLE EDITION généré.")
            st.dataframe(pivot.head(20))

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
        st.subheader("Top 10 ISBN par résultat net")
        top_isbn = df.groupby("Code_Analytique", as_index=False)["Résultat"].sum().sort_values("Résultat", ascending=False).head(10)
        st.dataframe(top_isbn)
        fig = px.bar(top_isbn, x="Code_Analytique", y="Résultat", labels={"Code_Analytique":"ISBN","Résultat":"Résultat net"})
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
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        taux_fixe = st.number_input("Taux fixe de droits (%)", value=10.0)
        # Ventes
        ventes_comptes = st.session_state["param_comptes"]["ventes"]
        df_ventes = df[df["Compte"].astype(str).str.strip().isin(ventes_comptes)]
        df_droits = df_ventes.groupby("Code_Analytique", as_index=False)["Crédit"].sum()
        df_droits["Droits"] = df_droits["Crédit"] * taux_fixe / 100
        st.subheader("Droits par ISBN")
        st.dataframe(df_droits.sort_values("Droits", ascending=False))
        # Prévision droits
        horizon = st.slider("Horizon prévision droits (mois)", 3, 24, 12)
        croissance_droits = st.number_input("Croissance mensuelle (%)", 2.0)/100
        previsions_droits = [df_droits["Droits"].sum() * (1 + croissance_droits)**i for i in range(1,horizon+1)]
        df_prev_droits = pd.DataFrame({"Mois":[f"Mois {i}" for i in range(1,horizon+1)],
                                       "Droits prévus": previsions_droits})
        st.subheader("Prévision droits")
        st.dataframe(df_prev_droits.style.format({"Droits prévus":"{:,.0f}"}))

# =====================
# RETURNS EDITION
# =====================
elif page == "RETURNS EDITION":
    st.header("📦 RETURNS EDITION - Gestion des retours")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        param = st.session_state["param_comptes"]
        df["Compte"] = df["Compte"].astype(str).str.strip()
        
        ca_brut = df[df["Compte"].isin(param["ventes"])]["Crédit"].sum()
        total_retours = df[df["Compte"].isin(param["retours"])]["Crédit"].sum()
        total_remises = df[df["Compte"].isin(param["remises"])]["Crédit"].sum()
        total_provisions = df[df["Compte"].isin(param["provisions"])]["Débit"].sum()
        resultat_net = ca_brut - total_retours - total_remises - df["Débit"].sum()
        
        st.metric("CA brut", f"{ca_brut:,.0f} €")
        st.metric("Total retours", f"{total_retours:,.0f} €")
        st.metric("Total remises", f"{total_remises:,.0f} €")
        st.metric("Provision sur retours", f"{total_provisions:,.0f} €")
        st.metric("Résultat net", f"{resultat_net:,.0f} €")
        
        st.subheader("Top ISBN par retours")
        top_isbn_retours = df[df["Compte"].isin(param["retours"])].groupby("Code_Analytique", as_index=False)["Crédit"].sum()
        st.dataframe(top_isbn_retours.sort_values("Crédit", ascending=False))

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
        # Nettoyage et conversion
        df_pivot["Compte"] = df_pivot["Compte"].astype(str).str.strip()
        df_pivot["Date"] = pd.to_datetime(df_pivot["Date"], errors="coerce")
        df_pivot["Débit"] = pd.to_numeric(df_pivot["Débit"], errors="coerce").fillna(0)
        df_pivot["Crédit"] = pd.to_numeric(df_pivot["Crédit"], errors="coerce").fillna(0)
        # Solde départ
        comptes_bancaires = df_pivot[df_pivot["Compte"].str.startswith("5")]
        solde_depart_total = (comptes_bancaires[comptes_bancaires["Date"]<=pd.to_datetime(date_debut)]["Crédit"].sum()
                             - comptes_bancaires[comptes_bancaires["Date"]<=pd.to_datetime(date_debut)]["Débit"].sum())
        st.info(f"Solde de départ : {solde_depart_total:,.0f} €")
        # Paramètres projection
        horizon = st.slider("Horizon de projection (mois)",3,24,12)
        croissance_ca = st.number_input("Croissance mensuelle CA (%)",2.0)/100
        evolution_charges = st.number_input("Evolution mensuelle charges (%)",1.0)/100
        # Flux hors banques
        df_flux = df_pivot[~df_pivot["Compte"].str.startswith("5")].copy()
        df_flux = df_flux.dropna(subset=["Date"])
        df_flux = df_flux[df_flux["Date"]>=pd.to_datetime(date_debut)]
        df_flux["Mois"] = df_flux["Date"].dt.to_period("M").astype(str)
        flux_mensuel = df_flux.groupby("Mois").agg({"Débit":"sum","Crédit":"sum"}).reset_index()
        flux_mensuel["Solde_mensuel"] = flux_mensuel["Crédit"] - flux_mensuel["Débit"]
        flux_mensuel = flux_mensuel.sort_values("Mois")
        # Prévision future
        dernier_mois = pd.Period(flux_mensuel["Mois"].max(),freq="M") if not flux_mensuel.empty else pd.Period(date_debut,freq="M")
        previsions=[]
        ca_actuel = flux_mensuel["Crédit"].iloc[-1] if not flux_mensuel.empty else 0
        charges_actuelles = flux_mensuel["Débit"].iloc[-1] if not flux_mensuel.empty else 0
        for i in range(1,horizon+1):
            prochain_mois=(dernier_mois+i).strftime("%Y-%m")
            ca_actuel*=(1+croissance_ca)
            charges_actuelles*=(1+evolution_charges)
            solde_prevu=ca_actuel-charges_actuelles
            previsions.append({"Mois":prochain_mois,"Débit":charges_actuelles,"Crédit":ca_actuel,"Solde_mensuel":solde_prevu})
        df_prev = pd.DataFrame(previsions)
        df_tresorerie=pd.concat([flux_mensuel,df_prev],ignore_index=True)
        df_tresorerie["Trésorerie_cumulée"] = solde_depart_total + df_tresorerie["Solde_mensuel"].cumsum()
        # Graphique
        fig = px.line(df_tresorerie, x="Mois", y="Trésorerie_cumulée", title="📈 Evolution prévisionnelle de la trésorerie", markers=True)
        fig.update_layout(xaxis_title="Mois", yaxis_title="Trésorerie (€)")
        st.plotly_chart(fig,use_container_width=True)
        st.subheader("📋 Détail mensuel")
        st.dataframe(df_tresorerie.style.format({"Débit":"{:,.0f}","Crédit":"{:,.0f}","Solde_mensuel":"{:,.0f}","Trésorerie_cumulée":"{:,.0f}"}))

# =====================
# SYNTHESE GLOBALE
# =====================
elif page=="SYNTHESE GLOBALE":
    st.header("📊 SYNTHESE GLOBALE")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        param = st.session_state["param_comptes"]
        ca_brut = df[df["Compte"].isin(param["ventes"])]["Crédit"].sum()
        total_retours = df[df["Compte"].isin(param["retours"])]["Crédit"].sum()
        total_remises = df[df["Compte"].isin(param["remises"])]["Crédit"].sum()
        total_provisions = df[df["Compte"].isin(param["provisions"])]["Débit"].sum()
        resultat_net = ca_brut - total_retours - total_remises - df["Débit"].sum()
        st.metric("CA brut", f"{ca_brut:,.0f} €")
        st.metric("Total retours", f"{total_retours:,.0f} €")
        st.metric("Total remises", f"{total_remises:,.0f} €")
        st.metric("Provision sur retours", f"{total_provisions:,.0f} €")
        st.metric("Résultat net", f"{resultat_net:,.0f} €")
        st.subheader("Top 10 ISBN par résultat")
        top_isbn = df.groupby("Code_Analytique",as_index=False).agg({"Crédit":"sum","Débit":"sum"})
        top_isbn["Résultat"]=top_isbn["Crédit"]-top_isbn["Débit"]
        st.dataframe(top_isbn.sort_values("Résultat",ascending=False).head(10))

# =====================
# COPYRIGHT
# =====================
st.markdown("<br><hr><p style='text-align:center;font-size:12px;'>© Nicolas CUISSET</p>", unsafe_allow_html=True)
