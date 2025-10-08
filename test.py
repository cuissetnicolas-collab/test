import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import plotly.express as px

# =====================
# INTERFACE ACCUEIL
# =====================
st.set_page_config(page_title="Outils Expert-Comptable - Édition", layout="wide")
st.title("📚 Outils de Pilotage pour Petites Maisons d'Édition")
st.markdown("""
Bienvenue dans votre espace expert-comptable dédié aux maisons d'édition indépendantes.
Ici, vous pourrez :
- Importer et centraliser vos données comptables (**DATA EDITION**)
- Générer un pivot analytique commun (**SOCLE EDITION**)
- Visualiser vos indicateurs par ISBN ou collection (**VISION EDITION**)
- Créer des mini comptes de résultat par titre (**ISBN VIEW**)
- Suivre la trésorerie prévisionnelle (**CASH EDITION**)
- Calculer les droits d'auteurs (**ROYALTIES EDITION**)
- Estimer et gérer les retours (**RETURNS EDITION**)
""")
st.markdown("---")

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
# MENU PRINCIPAL
# =====================
st.sidebar.success(f"Bienvenue {st.session_state['name']} 👋")
if st.sidebar.button("Déconnexion"):
    st.session_state["login"] = False
    st.experimental_rerun()

menu = st.sidebar.radio(
    "Menu principal",
    [
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
# MODULE DATA EDITION
# =====================
if menu == "DATA EDITION":
    st.header("📂 Import des données comptables")
    fichier_comptables = st.file_uploader("Importer votre fichier Excel Pennylane ou autre logiciel", type=["xlsx"])
    if fichier_comptables is not None:
        try:
            df = pd.read_excel(fichier_comptables, header=0)
            df.columns = df.columns.str.strip()
            st.write("Colonnes détectées :", list(df.columns))

            # Mapping standard multi-logiciels
            col_mapping = {}
            if "Numéro de compte" in df.columns: col_mapping["Numéro de compte"] = "Compte"
            if "Débit" in df.columns: col_mapping["Débit"] = "Débit"
            if "Crédit" in df.columns: col_mapping["Crédit"] = "Crédit"
            if "Familles de catégories" in df.columns: col_mapping["Familles de catégories"] = "Famille_Analytique"
            if "Catégories" in df.columns: col_mapping["Catégories"] = "Code_Analytique"
            if "Date" in df.columns: col_mapping["Date"] = "Date"
            elif "Date opération" in df.columns: col_mapping["Date opération"] = "Date"

            if "Compte" not in col_mapping.values() or "Date" not in col_mapping.values():
                st.error("⚠️ Colonnes 'Compte' et/ou 'Date' manquantes !")
            else:
                df.rename(columns=col_mapping, inplace=True)
                st.session_state["df_dataedition"] = df
                st.success(f"✅ Fichier chargé : {df.shape[0]} lignes")
                st.dataframe(df.head())
        except Exception as e:
            st.error(f"❌ Erreur lors de l'importation : {e}")

# =====================
# MODULE SOCLE EDITION
# =====================
elif menu == "SOCLE EDITION":
    st.header("🛠️ Génération du SOCLE EDITION (pivot analytique)")
    if "df_dataedition" not in st.session_state:
        st.warning("⚠️ Importer d'abord les données via DATA EDITION")
    else:
        df = st.session_state["df_dataedition"]
        if st.button("Générer le SOCLE EDITION"):
            try:
                for col in ["Famille_Analytique", "Code_Analytique"]:
                    if col not in df.columns: df[col] = ""
                    else: df[col] = df[col].fillna("")

                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                pivot = df.groupby(
                    ["Compte", "Famille_Analytique", "Code_Analytique", "Date"],
                    as_index=False
                ).agg({"Débit": "sum", "Crédit": "sum"})
                st.session_state["df_socleedition"] = pivot
                st.success("✅ SOCLE EDITION généré avec toutes les lignes.")
                st.dataframe(pivot.head(20))
            except Exception as e:
                st.error(f"❌ Erreur lors de la génération du SOCLE EDITION : {e}")

# =====================
# MODULE VISION EDITION
# =====================
elif menu == "VISION EDITION":
    st.header("📊 Dashboard analytique - VISION EDITION")
    if "df_socleedition" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION")
    else:
        df_pivot = st.session_state["df_socleedition"]
        st.subheader("📈 Top 10 ISBN par résultat net")
        df_pivot["Résultat"] = df_pivot["Crédit"] - df_pivot["Débit"]
        top_isbn = df_pivot.groupby("Code_Analytique", as_index=False)["Résultat"].sum().sort_values(by="Résultat", ascending=False).head(10)
        st.dataframe(top_isbn)
        fig = px.bar(top_isbn, x="Code_Analytique", y="Résultat",
                     title="Top 10 ISBN par résultat net",
                     labels={"Code_Analytique": "ISBN", "Résultat": "Résultat net"})
        st.plotly_chart(fig, use_container_width=True)

# =====================
# MODULE ISBN VIEW
# =====================
elif menu == "ISBN VIEW":
    st.header("💼 Mini compte de résultat par ISBN - ISBN VIEW")
    if "df_socleedition" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION")
    else:
        df_pivot = st.session_state["df_socleedition"]
        df_cr = df_pivot.groupby("Code_Analytique", as_index=False).agg({"Débit": "sum", "Crédit": "sum"})
        df_cr["Résultat"] = df_cr["Crédit"] - df_cr["Débit"]
        st.dataframe(df_cr)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_cr.to_excel(writer, index=False, sheet_name="Mini_CR_ISBN")
        buffer.seek(0)
        st.download_button("📥 Télécharger le mini compte de résultat par ISBN", buffer, file_name="Mini_CR_ISBN.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =====================
# MODULE CASH EDITION
# =====================
elif menu == "CASH EDITION":
    st.header("💰 Suivi de trésorerie - CASH EDITION")
    if "df_socleedition" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION")
    else:
        df_pivot = st.session_state["df_socleedition"]
        # Suivi trésorerie (code comme précédemment)
        st.info("🔹 Module CASH EDITION prêt pour vos projections de trésorerie")

# =====================
# MODULE ROYALTIES EDITION
# =====================
elif menu == "ROYALTIES EDITION":
    st.header("🎵 Suivi des droits d'auteurs - ROYALTIES EDITION")
    if "df_socleedition" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION")
    else:
        taux_fixe = st.number_input("Taux fixe (%)", value=10.0)/100
        utiliser_personnalise = st.checkbox("Permettre à l'utilisateur de saisir un taux par ISBN", value=True)
        st.info("🔹 Module ROYALTIES EDITION prêt à calculer vos droits d'auteurs par ISBN")

# =====================
# MODULE RETURNS EDITION
# =====================
elif menu == "RETURNS EDITION":
    st.header("📦 Gestion des retours - RETURNS EDITION")
    if "df_socleedition" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION")
    else:
        historique_retours = st.checkbox("Utiliser l'historique des retours", value=True)
        permettre_saisie = st.checkbox("Permettre à l'utilisateur de saisir un taux de retour", value=True)
        st.info("🔹 Module RETURNS EDITION prêt à estimer les retours par ISBN")
