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
    users = {
        "aurore": {"password": "12345", "name": "Aurore Demoulin"},
    }
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
# PAGE DE PRÉSENTATION
# =====================
st.sidebar.success(f"Bienvenue {st.session_state['name']} 👋")
if st.sidebar.button("Déconnexion"):
    st.session_state["login"] = False
    st.experimental_rerun()

page = st.sidebar.selectbox(
    "Menu principal",
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

if page == "Présentation":
    st.title("📚 Bienvenue dans l'outil Edition Expert-Comptable")
    st.markdown("""
    Cet outil permet de :
    - Importer et centraliser les données comptables (**DATA EDITION**)
    - Construire le pivot analytique (**SOCLE EDITION**)
    - Visualiser les performances par ISBN (**VISION EDITION**, **ISBN VIEW**)
    - Suivre la trésorerie prévisionnelle (**CASH EDITION**)
    - Calculer et suivre les droits d’auteurs (**ROYALTIES EDITION**)
    - Piloter les retours (**RETURNS EDITION**)
    
    Utilisez le menu à gauche pour accéder directement à chaque module.
    """)
    st.stop()

# =====================
# DATA EDITION - Import compta analytique
# =====================
if page == "DATA EDITION":
    st.header("📂 DATA EDITION - Import des données comptables")
    fichier_comptables = st.file_uploader("📂 Sélectionne ton fichier Excel compta analytique", type=["xlsx"])
    if fichier_comptables:
        df = pd.read_excel(fichier_comptables, header=0)
        df.columns = df.columns.str.strip()
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

# =====================
# SOCLE EDITION - Pivot analytique
# =====================
elif page == "SOCLE EDITION":
    st.header("🛠️ SOCLE EDITION - Construction du pivot analytique")
    if "df_comptables" not in st.session_state:
        st.warning("⚠️ Importer d'abord les données dans DATA EDITION.")
    else:
        df = st.session_state["df_comptables"]
        if st.button("Générer le SOCLE"):
            for col in ["Famille_Analytique", "Code_Analytique"]:
                if col not in df.columns: df[col] = ""
                else: df[col] = df[col].fillna("")
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            pivot = df.groupby(["Compte", "Famille_Analytique", "Code_Analytique", "Date"], as_index=False).agg({"Débit": "sum", "Crédit": "sum"})
            st.session_state["df_pivot"] = pivot
            st.success("✅ SOCLE généré")
            st.dataframe(pivot.head(20))

# =====================
# VISION EDITION - Dashboard analytique
# =====================
elif page == "VISION EDITION":
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        st.subheader("📈 VISION EDITION - Top 10 ISBN par résultat net")
        df_pivot = st.session_state["df_pivot"]
        df_pivot["Résultat"] = df_pivot["Crédit"] - df_pivot["Débit"]
        top_isbn = df_pivot.groupby("Code_Analytique", as_index=False)["Résultat"].sum().sort_values(by="Résultat", ascending=False).head(10)
        st.dataframe(top_isbn)
        fig = px.bar(top_isbn, x="Code_Analytique", y="Résultat",
                     title="Top 10 ISBN par résultat net",
                     labels={"Code_Analytique": "ISBN", "Résultat": "Résultat net"})
        st.plotly_chart(fig, use_container_width=True)

# =====================
# ISBN VIEW - Mini compte de résultat par ISBN
# =====================
elif page == "ISBN VIEW":
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        st.subheader("💼 ISBN VIEW - Mini compte de résultat par ISBN")
        df_pivot = st.session_state["df_pivot"]
        df_cr = df_pivot.groupby("Code_Analytique", as_index=False).agg({"Débit": "sum", "Crédit": "sum"})
        df_cr["Résultat"] = df_cr["Crédit"] - df_cr["Débit"]
        st.dataframe(df_cr)

# =====================
# CASH EDITION - Trésorerie prévisionnelle
# =====================
elif page == "CASH EDITION":
    st.header("💰 CASH EDITION - Trésorerie prévisionnelle")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df_pivot = st.session_state["df_pivot"]
        # (Insérer ici le code complet CASH EDITION corrigé pour datetime et solde_depart_total)
        ...

# =====================
# ROYALTIES EDITION - Gestion des droits d'auteurs
# =====================
elif page == "ROYALTIES EDITION":
    st.header("📚 ROYALTIES EDITION - Gestion des droits d'auteurs")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"]
        # Vérification de la colonne Exemplaires
        if "Exemplaires" not in df.columns:
            st.warning("⚠️ Le nombre d'exemplaires n'est pas présent dans la compta analytique.")
            fichiers_bldd = st.file_uploader(
                "📂 Importer un ou plusieurs fichiers BLDD/diffuseur",
                type=["xlsx"], accept_multiple_files=True
            )
            if fichiers_bldd:
                liste_df = []
                for f in fichiers_bldd:
                    df_temp = pd.read_excel(f, dtype={"ISBN": str})
                    df_temp.columns = df_temp.columns.str.strip()
                    if "Quantité" in df_temp.columns:
                        df_temp = df_temp[["ISBN", "Quantité"]]
                        liste_df.append(df_temp)
                if liste_df:
                    df_exemplaires = pd.concat(liste_df).groupby("ISBN", as_index=False).sum()
                    df = df.merge(df_exemplaires, left_on="Code_Analytique", right_on="ISBN", how="left")
                    df["Exemplaires"] = df["Quantité"].fillna(0)
                    st.session_state["df_pivot"] = df
                    st.success("✅ Données des exemplaires intégrées.")
        taux_royalties = st.number_input("Taux de royalties (%)", value=10.0)/100
        if "Exemplaires" in df.columns:
            df["Montant_Royalties"] = df["Exemplaires"] * df.get("Prix_unitaire", 0) * taux_royalties
            st.dataframe(df[["Code_Analytique", "Exemplaires", "Montant_Royalties"]])

# =====================
# RETURNS EDITION - Gestion des retours
# =====================
elif page == "RETURNS EDITION":
    st.header("📦 RETURNS EDITION - Gestion des retours")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"]
        if "Exemplaires" not in df.columns:
            st.warning("⚠️ Le nombre d'exemplaires n'est pas présent dans la compta analytique.")
            fichiers_bldd = st.file_uploader(
                "📂 Importer un ou plusieurs fichiers BLDD/diffuseur",
                type=["xlsx"], accept_multiple_files=True
            )
            if fichiers_bldd:
                liste_df = []
                for f in fichiers_bldd:
                    df_temp = pd.read_excel(f, dtype={"ISBN": str})
                    df_temp.columns = df_temp.columns.str.strip()
                    if "Quantité" in df_temp.columns:
                        df_temp = df_temp[["ISBN", "Quantité"]]
                        liste_df.append(df_temp)
                if liste_df:
                    df_exemplaires = pd.concat(liste_df).groupby("ISBN", as_index=False).sum()
                    df = df.merge(df_exemplaires, left_on="Code_Analytique", right_on="ISBN", how="left")
                    df["Exemplaires"] = df["Quantité"].fillna(0)
                    st.session_state["df_pivot"] = df
                    st.success("✅ Données des exemplaires intégrées.")
        method = st.selectbox("Méthode de calcul des retours", ["Historique (%)", "Taux fixe par ISBN"])
        taux_retour = st.number_input("Taux de retour (%)", value=5.0)/100
        if "Exemplaires" in df.columns:
            df["Montant_Retours"] = df["Exemplaires"] * taux_retour
            st.dataframe(df[["Code_Analytique", "Exemplaires", "Montant_Retours"]])
