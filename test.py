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
# MENU PRINCIPAL
# =====================
st.sidebar.success(f"Bienvenue {st.session_state['name']} 👋")
if st.sidebar.button("Déconnexion"):
    st.session_state["login"] = False
    st.experimental_rerun()

menu = st.sidebar.selectbox(
    "🔹 Choisir un module",
    [
        "Présentation",
        "DATA EDITION",
        "SOCLE EDITION",
        "VISION EDITION",
        "ISBN VIEW",
        "CASH EDITION",
        "ROYALTIES EDITION",
        "RETURNS EDITION"
    ]
)

# =====================
# PAGE DE PRÉSENTATION
# =====================
if menu == "Présentation":
    st.title("📖 Outil de suivi des maisons d’édition")
    st.markdown("""
    Bienvenue dans l’outil global d’analyse et de suivi des activités
    d’une maison d’édition indépendante.  

    Vous pouvez :
    - Importer les données comptables et analytiques (DATA EDITION)  
    - Générer le socle pivot analytique (SOCLE EDITION)  
    - Visualiser les résultats par ISBN (VISION EDITION & ISBN VIEW)  
    - Suivre la trésorerie prévisionnelle (CASH EDITION)  
    - Calculer automatiquement les droits d’auteurs (ROYALTIES EDITION)  
    - Estimer les retours de livres (RETURNS EDITION)  

    Commencez par DATA EDITION pour importer vos fichiers.
    """)

# =====================
# MODULE 1 : DATA EDITION
# =====================
elif menu == "DATA EDITION":
    st.header("📂 DATA EDITION - Importation des données comptables et analytiques")
    
    fichier_comptables = st.file_uploader("Importer le fichier Excel Pennylane Connect ou BLDD", type=["xlsx"])
    
    if fichier_comptables:
        try:
            df = pd.read_excel(fichier_comptables, header=0)
            df.columns = df.columns.str.strip()
            st.write("Colonnes détectées :", list(df.columns))
            
            # Mapping standard
            col_mapping = {}
            if "Numéro de compte" in df.columns: col_mapping["Numéro de compte"] = "Compte"
            if "Débit" in df.columns: col_mapping["Débit"] = "Débit"
            if "Crédit" in df.columns: col_mapping["Crédit"] = "Crédit"
            if "Familles de catégories" in df.columns: col_mapping["Familles de catégories"] = "Famille_Analytique"
            if "Catégories" in df.columns: col_mapping["Catégories"] = "Code_Analytique"
            if "Date" in df.columns: col_mapping["Date"] = "Date"
            elif "Date opération" in df.columns: col_mapping["Date opération"] = "Date"
            
            df.rename(columns=col_mapping, inplace=True)
            st.session_state["df_comptables"] = df
            st.success(f"✅ Fichier chargé : {df.shape[0]} lignes")
            st.dataframe(df.head())
            
        except Exception as e:
            st.error(f"❌ Erreur lors de l'importation : {e}")

# =====================
# MODULE 2 : SOCLE EDITION
# =====================
elif menu == "SOCLE EDITION":
    st.header("🛠️ SOCLE EDITION - Génération du pivot analytique")
    
    if "df_comptables" not in st.session_state:
        st.warning("⚠️ Importer d'abord les données via DATA EDITION.")
    else:
        df = st.session_state["df_comptables"].copy()
        for col in ["Famille_Analytique", "Code_Analytique"]:
            if col not in df.columns: df[col] = ""
            else: df[col] = df[col].fillna("")
        
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        pivot = df.groupby(
            ["Compte", "Famille_Analytique", "Code_Analytique", "Date"],
            as_index=False
        ).agg({"Débit": "sum", "Crédit": "sum"})
        
        st.session_state["df_pivot"] = pivot
        st.success("✅ SOCLE EDITION généré avec toutes les lignes.")
        st.dataframe(pivot.head(20))

# =====================
# MODULE 3 : VISION EDITION
# =====================
elif menu == "VISION EDITION":
    st.header("📊 VISION EDITION - Dashboard analytique")
    
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df_pivot = st.session_state["df_pivot"].copy()
        df_pivot["Résultat"] = df_pivot["Crédit"] - df_pivot["Débit"]
        top_isbn = df_pivot.groupby("Code_Analytique", as_index=False)["Résultat"].sum()
        top_isbn = top_isbn.sort_values(by="Résultat", ascending=False).head(10)
        
        if top_isbn.empty:
            st.warning("⚠️ Aucun résultat disponible pour générer le dashboard.")
        else:
            st.dataframe(top_isbn)
            fig = px.bar(top_isbn, x="Code_Analytique", y="Résultat",
                         title="Top 10 ISBN par résultat net",
                         labels={"Code_Analytique": "ISBN", "Résultat": "Résultat net"})
            st.plotly_chart(fig, use_container_width=True)

# =====================
# MODULE 4 : ISBN VIEW
# =====================
elif menu == "ISBN VIEW":
    st.header("💼 ISBN VIEW - Mini compte de résultat par ISBN")
    
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df_pivot = st.session_state["df_pivot"].copy()
        df_cr = df_pivot.groupby("Code_Analytique", as_index=False).agg({"Débit": "sum", "Crédit": "sum"})
        df_cr["Résultat"] = df_cr["Crédit"] - df_cr["Débit"]
        st.dataframe(df_cr)

# =====================
# MODULE 5 : CASH EDITION
# =====================
elif menu == "CASH EDITION":
    st.header("💰 CASH EDITION - Trésorerie prévisionnelle")
    
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df_pivot = st.session_state["df_pivot"].copy()
        date_debut = st.date_input("Date de départ", pd.to_datetime("2025-04-01"))
        horizon = st.slider("Horizon de projection (mois)", 3, 24, 12)
        croissance_ca = st.number_input("Croissance mensuelle du CA (%)", 2.0)/100
        evolution_charges = st.number_input("Évolution mensuelle des charges (%)", 1.0)/100

        df_pivot["Débit"] = pd.to_numeric(df_pivot["Débit"], errors="coerce").fillna(0)
        df_pivot["Crédit"] = pd.to_numeric(df_pivot["Crédit"], errors="coerce").fillna(0)
        df_pivot["Compte"] = df_pivot["Compte"].astype(str).str.strip()
        df_pivot["Date"] = pd.to_datetime(df_pivot["Date"], errors="coerce")
        
        comptes_bancaires = df_pivot[df_pivot["Compte"].str.startswith("5")]
        solde_depart_total = (comptes_bancaires[comptes_bancaires["Date"] <= date_debut]["Crédit"].sum() - 
                              comptes_bancaires[comptes_bancaires["Date"] <= date_debut]["Débit"].sum())
        st.info(f"Solde de départ : {solde_depart_total:,.2f} €")
        
        df_flux = df_pivot[~df_pivot["Compte"].str.startswith("5")].copy()
        df_flux = df_flux[df_flux["Date"] >= date_debut]
        df_flux["Mois"] = df_flux["Date"].dt.to_period("M").astype(str)
        flux_mensuel = df_flux.groupby("Mois").agg({"Débit": "sum", "Crédit": "sum"}).reset_index()
        flux_mensuel["Solde_mensuel"] = flux_mensuel["Crédit"] - flux_mensuel["Débit"]
        
        dernier_mois = pd.Period(flux_mensuel["Mois"].max(), freq="M") if not flux_mensuel.empty else pd.Period(date_debut, freq="M")
        previsions = []
        ca_actuel = flux_mensuel["Crédit"].iloc[-1] if not flux_mensuel.empty else 0
        charges_actuelles = flux_mensuel["Débit"].iloc[-1] if not flux_mensuel.empty else 0

        for i in range(1, horizon + 1):
            prochain_mois = (dernier_mois + i).strftime("%Y-%m")
            ca_actuel *= (1 + croissance_ca)
            charges_actuelles *= (1 + evolution_charges)
            solde_prevu = ca_actuel - charges_actuelles
            previsions.append({"Mois": prochain_mois, "Débit": charges_actuelles, 
                               "Crédit": ca_actuel, "Solde_mensuel": solde_prevu})
        
        df_prev = pd.DataFrame(previsions)
        df_tresorerie = pd.concat([flux_mensuel, df_prev], ignore_index=True)
        df_tresorerie["Trésorerie_cumulée"] = solde_depart_total + df_tresorerie["Solde_mensuel"].cumsum()
        
        fig = px.line(df_tresorerie, x="Mois", y="Trésorerie_cumulée", title="📈 Évolution prévisionnelle de la trésorerie", markers=True)
        fig.update_layout(xaxis_title="Mois", yaxis_title="Trésorerie (€)")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_tresorerie.style.format({"Débit": "{:,.0f}", "Crédit": "{:,.0f}", 
                                                 "Solde_mensuel": "{:,.0f}", "Trésorerie_cumulée": "{:,.0f}"}))

# =====================
# MODULE 6 : ROYALTIES EDITION
# =====================
elif menu == "ROYALTIES EDITION":
    st.header("📚 ROYALTIES EDITION - Droits d’auteurs par ISBN")
    
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df_pivot = st.session_state["df_pivot"].copy()
        taux_auteur = st.number_input("Taux de droits d'auteurs (%)", value=10.0)/100
        df_royalties = df_pivot.groupby("Code_Analytique", as_index=False)["Crédit"].sum()
        df_royalties["Droits_auteur"] = df_royalties["Crédit"] * taux_auteur
        st.dataframe(df_royalties)

# =====================
# MODULE 7 : RETURNS EDITION
# =====================
elif menu == "RETURNS EDITION":
    st.header("📦 RETURNS EDITION - Estimation des retours de livres")
    
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df_pivot = st.session_state["df_pivot"].copy()
        taux_retour = st.number_input("Taux de retours (%)", value=5.0)/100
        df_returns = df_pivot.groupby("Code_Analytique", as_index=False)["Crédit"].sum()
        df_returns["Montant_retours"] = df_returns["Crédit"] * taux_retour
        st.dataframe(df_returns)
