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
# PAGE D'ACCUEIL
# =====================
st.sidebar.success(f"Bienvenue {st.session_state['name']} 👋")
if st.sidebar.button("Déconnexion"):
    st.session_state["login"] = False
    st.experimental_rerun()

# Définition des modules et icônes
modules = [
    "Présentation", "DATA EDITION", "SOCLE EDITION", "VISION EDITION",
    "ISBN VIEW", "CASH EDITION", "ROYALTIES EDITION", "RETURNS EDITION"
]
module_icons = {
    "Présentation": "🏠", "DATA EDITION": "📂", "SOCLE EDITION": "🛠️", 
    "VISION EDITION": "📈", "ISBN VIEW": "💼", "CASH EDITION": "💰",
    "ROYALTIES EDITION": "✍️", "RETURNS EDITION": "🔄"
}

selection = st.sidebar.selectbox("Choisissez un module", modules)

if selection == "Présentation":
    st.title("🏠 Bienvenue dans l'outil d'aide à la gestion des maisons d’édition")
    st.markdown("""
    Cet outil est destiné aux experts-comptables pour faciliter :
    - Le suivi analytique par ISBN ou collection
    - La génération de tableaux de bord interactifs
    - La prévision de trésorerie
    - La gestion automatisée des droits d’auteurs
    - La gestion des retours de livres
    """)
    st.info("Sélectionnez un module dans le menu à gauche pour commencer.")

# =====================
# MODULE 1 : DATA EDITION
# =====================
elif selection == "DATA EDITION":
    st.header(f"{module_icons['DATA EDITION']} DATA EDITION - Import des données comptables")
    fichier_comptables = st.file_uploader("📂 Sélectionnez votre fichier Excel Pennylane Connect", type=["xlsx"])
    if fichier_comptables:
        try:
            df = pd.read_excel(fichier_comptables)
            df.columns = df.columns.str.strip()
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
elif selection == "SOCLE EDITION":
    st.header(f"{module_icons['SOCLE EDITION']} SOCLE EDITION - Pivot analytique universel")
    if "df_comptables" not in st.session_state:
        st.warning("⚠️ Importer d'abord les données comptables via DATA EDITION.")
    else:
        df = st.session_state["df_comptables"].copy()
        if st.button("Générer le SOCLE EDITION"):
            try:
                for col in ["Famille_Analytique", "Code_Analytique"]:
                    if col not in df.columns: df[col] = ""
                    else: df[col] = df[col].fillna("")
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                pivot = df.groupby(
                    ["Compte", "Famille_Analytique", "Code_Analytique", "Date"],
                    as_index=False
                ).agg({"Débit":"sum","Crédit":"sum"})
                st.session_state["df_pivot"] = pivot
                st.success("✅ SOCLE EDITION généré avec toutes les lignes")
                st.dataframe(pivot.head(20))
            except Exception as e:
                st.error(f"❌ Erreur lors de la génération du SOCLE EDITION : {e}")

# =====================
# MODULE 3 : VISION EDITION
# =====================
elif selection == "VISION EDITION":
    st.header(f"{module_icons['VISION EDITION']} VISION EDITION - Dashboard analytique")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df_pivot = st.session_state["df_pivot"]
        df_pivot["Résultat"] = df_pivot["Crédit"] - df_pivot["Débit"]
        top_isbn = df_pivot.groupby("Code_Analytique", as_index=False)["Résultat"].sum()
        top_isbn = top_isbn.sort_values(by="Résultat", ascending=False).head(10)
        st.dataframe(top_isbn)
        fig = px.bar(top_isbn, x="Code_Analytique", y="Résultat", title="Top 10 ISBN par résultat net", labels={"Code_Analytique":"ISBN","Résultat":"Résultat net"})
        st.plotly_chart(fig, use_container_width=True)

# =====================
# MODULE 4 : ISBN VIEW
# =====================
elif selection == "ISBN VIEW":
    st.header(f"{module_icons['ISBN VIEW']} ISBN VIEW - Mini compte de résultat par ISBN")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df_cr = st.session_state["df_pivot"].groupby("Code_Analytique", as_index=False).agg({"Débit":"sum","Crédit":"sum"})
        df_cr["Résultat"] = df_cr["Crédit"] - df_cr["Débit"]
        st.dataframe(df_cr)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_cr.to_excel(writer, index=False, sheet_name="Mini_CR_ISBN")
        buffer.seek(0)
        st.download_button("📥 Télécharger le mini compte de résultat par ISBN", buffer, "Mini_Compte_Resultat_ISBN.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =====================
# MODULE 5 : CASH EDITION
# =====================
elif selection == "CASH EDITION":
    st.header(f"{module_icons['CASH EDITION']} CASH EDITION - Trésorerie prévisionnelle")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df_pivot = st.session_state["df_pivot"].copy()
        date_debut = st.date_input("Date de départ de la trésorerie", pd.to_datetime("2025-04-01"))
        df_pivot["Débit"] = pd.to_numeric(df_pivot["Débit"], errors="coerce").fillna(0)
        df_pivot["Crédit"] = pd.to_numeric(df_pivot["Crédit"], errors="coerce").fillna(0)
        comptes_bancaires = df_pivot[df_pivot["Compte"].astype(str).str.startswith("5")]
        solde_depart_df = comptes_bancaires[comptes_bancaires["Date"] <= pd.to_datetime(date_debut)]
        solde_depart_total = solde_depart_df["Crédit"].sum() - solde_depart_df["Débit"].sum()
        st.info(f"Solde de départ : {solde_depart_total:,.2f} €")
        horizon = st.slider("Horizon de projection (mois)", 3, 24, 12)
        croissance_ca = st.number_input("Croissance mensuelle du CA (%)", value=2.0)/100
        evolution_charges = st.number_input("Évolution mensuelle des charges (%)", value=1.0)/100
        df_flux = df_pivot[~df_pivot["Compte"].astype(str).str.startswith("5")].copy()
        df_flux = df_flux[df_flux["Date"] >= pd.to_datetime(date_debut)]
        df_flux["Mois"] = df_flux["Date"].dt.to_period("M").astype(str)
        flux_mensuel = df_flux.groupby("Mois").agg({"Débit":"sum","Crédit":"sum"}).reset_index()
        flux_mensuel["Solde_mensuel"] = flux_mensuel["Crédit"] - flux_mensuel["Débit"]
        flux_mensuel = flux_mensuel.sort_values("Mois")
        dernier_mois = pd.Period(flux_mensuel["Mois"].max(), freq="M") if not flux_mensuel.empty else pd.Period(date_debut, freq="M")
        previsions = []
        ca_actuel = flux_mensuel["Crédit"].iloc[-1] if not flux_mensuel.empty else 0
        charges_actuelles = flux_mensuel["Débit"].iloc[-1] if not flux_mensuel.empty else 0
        for i in range(1, horizon+1):
            prochain_mois = (dernier_mois+i).strftime("%Y-%m")
            ca_actuel *= (1+croissance_ca)
            charges_actuelles *= (1+evolution_charges)
            solde_prevu = ca_actuel - charges_actuelles
            previsions.append({"Mois":prochain_mois,"Débit":charges_actuelles,"Crédit":ca_actuel,"Solde_mensuel":solde_prevu})
        df_prev = pd.DataFrame(previsions)
        df_tresorerie = pd.concat([flux_mensuel, df_prev], ignore_index=True)
        df_tresorerie["Trésorerie_cumulée"] = solde_depart_total + df_tresorerie["Solde_mensuel"].cumsum()
        fig = px.line(df_tresorerie, x="Mois", y="Trésorerie_cumulée", title="📈 Évolution prévisionnelle de la trésorerie", markers=True)
        fig.update_layout(xaxis_title="Mois", yaxis_title="Trésorerie (€)")
        st.plotly_chart(fig, use_container_width=True)
        st.subheader("📋 Détail mensuel")
        st.dataframe(df_tresorerie.style.format({"Débit":"{:,.0f}","Crédit":"{:,.0f}","Solde_mensuel":"{:,.0f}","Trésorerie_cumulée":"{:,.0f}"}))

# =====================
# MODULE 6 : ROYALTIES EDITION
# =====================
elif selection == "ROYALTIES EDITION":
    st.header(f"{module_icons['ROYALTIES EDITION']} ROYALTIES EDITION - Droits d’auteurs livres")
    fichier_royalties = st.file_uploader("📂 Importer le fichier BLDD ou ventes nettes", type=["xlsx"])
    mode_taux = st.radio("Choix du mode de calcul des droits d’auteurs", ["Taux fixe", "Taux par auteur"])
    if fichier_royalties:
        df = pd.read_excel(fichier_royalties)
        df.columns = df.columns.str.strip()
        df["Net"] = pd.to_numeric(df["Net"], errors="coerce").fillna(0)
        df["Auteur"] = df["Auteur"].astype(str).fillna("Inconnu")
        if mode_taux == "Taux fixe":
            taux = st.number_input("Taux fixe (%)", value=10.0)/100
            df["Droits_auteur"] = (df["Net"] * taux).round(2)
        else:
            auteurs = df["Auteur"].unique()
            taux_dict = {}
            st.write("Saisissez le taux pour chaque auteur (%) :")
            for a in auteurs:
                taux_dict[a] = st.number_input(f"{a}", value=10.0)/100
            df["Droits_auteur"] = (df["Net"] * df["Auteur"].map(taux_dict)).round(2)
        st.dataframe(df[["ISBN","Auteur","Net","Droits_auteur"]])
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Royalties")
        buffer.seek(0)
        st.download_button("📥 Télécharger le fichier droits d’auteurs", buffer, "Royalties.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =====================
# MODULE 7 : RETURNS EDITION
# =====================
elif selection == "RETURNS EDITION":
    st.header(f"{module_icons['RETURNS EDITION']} RETURNS EDITION - Gestion des retours de livres")
    fichier_returns = st.file_uploader("📂 Importer le fichier ventes/BLDD", type=["xlsx"])
    mode_returns = st.radio("Mode de retour", ["Historique (%)", "Saisie manuelle (%)"])
    if fichier_returns:
        df = pd.read_excel(fichier_returns)
        df.columns = df.columns.str.strip()
        df["Vente"] = pd.to_numeric(df["Vente"], errors="coerce").fillna(0)
        df["ISBN"] = df["ISBN"].astype(str).str.strip()
        if mode_returns == "Historique (%)":
            historique = st.number_input("Pourcentage moyen de retour (%)", value=5.0)/100
            df["Retour"] = (df["Vente"] * historique).round(2)
        else:
            df["Retour"] = 0.0
            st.write("Saisir le pourcentage de retour pour chaque ISBN :")
            for idx, isbn in enumerate(df["ISBN"]):
                val = st.number_input(f"{isbn}", value=5.0)/100
                df.at[idx, "Retour"] = (df.at[idx, "Vente"] * val).round(2)
        st.dataframe(df[["ISBN","Vente","Retour"]])
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Returns")
        buffer.seek(0)
        st.download_button("📥 Télécharger le fichier retours", buffer, "Returns.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
