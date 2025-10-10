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
         "CASH EDITION", "ROYALTIES EDITION", "RETURNS EDITION"]
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
# CASH EDITION
# =====================
elif page == "CASH EDITION":
    st.header("💰 CASH EDITION - Trésorerie prévisionnelle")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        # Code complet de projection trésorerie ici (comme dans ton précédent module)
        st.info("Module CASH EDITION prêt. Implémentation des projections de trésorerie...")

# =====================
# ROYALTIES EDITION
# =====================
elif page == "ROYALTIES EDITION":
    st.header("📚 ROYALTIES EDITION - Droits d’auteurs")
    st.markdown("Choisissez la source pour le nombre d'exemplaires vendus :")
    source = st.radio("Source des données", ["Compta analytique", "Importer fichier BLDD"])
    if source == "Compta analytique":
        st.info("Les données seront récupérées depuis le SOCLE EDITION.")
        # Implémenter extraction des exemplaires si présents
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
    st.header("📦 RETURNS EDITION - Analyse des retours et remises libraires")

    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
        st.stop()

    df = st.session_state["df_pivot"].copy()

    # ======================
    # 📝 Note explicative
    # ======================
    with st.expander("ℹ️ Note à l’attention de l’expert-comptable ou du collaborateur"):
        st.markdown("""
        Cette section permet d’analyser les **retours d’ouvrages** et les **remises libraires** afin d’obtenir :
        - Le **chiffre d’affaires brut**  
        - Le **chiffre d’affaires net commercial** (après remises)  
        - Le **chiffre d’affaires net retour** (après retours)  
        - Les **taux de remise et de retour** par ISBN  

        Deux modes de paramétrage sont possibles :
        1. **Par libellé** : l’application identifie automatiquement les lignes selon des mots-clés présents dans le libellé de compte ou d’écriture  
           👉 Il est donc **indispensable que les libellés comptables soient explicites** (ex. “Vente BLDD”, “Retour BLDD”, “Remise librairie”).  
        2. **Par numéro de compte** : l’expert-comptable saisit les comptes correspondants à chaque nature d’opération  
           👉 Cette méthode est **plus fiable** et recommandée dans le cadre d’une production comptable standardisée.

        *Remarque : le paramétrage initial (libellés ou comptes) peut être ajusté une fois pour chaque cabinet et sera valable pour l’ensemble des périodes suivantes.*
        """)

    # ======================
    # ⚙️ Paramétrage des données
    # ======================
    st.subheader("⚙️ Paramétrage des données")
    mode = st.radio("Méthode d’identification :", ["Par libellé", "Par numéro de compte"])

    if mode == "Par libellé":
        col_libelle = st.selectbox("Colonne contenant le libellé :", df.columns)
        mots_ventes = st.text_input("🔸 Mots-clés pour les ventes", "vente, bldd")
        mots_retours = st.text_input("🔹 Mots-clés pour les retours", "retour")
        mots_remises = st.text_input("🟠 Mots-clés pour les remises libraires", "remise, ristourne")

        mots_ventes = [m.strip().lower() for m in mots_ventes.split(",")]
        mots_retours = [m.strip().lower() for m in mots_retours.split(",")]
        mots_remises = [m.strip().lower() for m in mots_remises.split(",")]

        def classer(texte):
            if pd.isna(texte): return "Autres"
            t = str(texte).lower()
            if any(m in t for m in mots_retours): return "Retours"
            if any(m in t for m in mots_remises): return "Remises"
            if any(m in t for m in mots_ventes): return "Ventes"
            return "Autres"

        df["Type_Ligne"] = df[col_libelle].apply(classer)

    else:
        comptes_uniques = sorted(df["Compte"].unique())
        comptes_ventes = st.multiselect("🔸 Comptes de ventes", comptes_uniques)
        comptes_retours = st.multiselect("🔹 Comptes de retours", comptes_uniques)
        comptes_remises = st.multiselect("🟠 Comptes de remises libraires", comptes_uniques)

        def classer_compte(compte):
            if compte in comptes_retours: return "Retours"
            if compte in comptes_remises: return "Remises"
            if compte in comptes_ventes: return "Ventes"
            return "Autres"

        df["Type_Ligne"] = df["Compte"].apply(classer_compte)

    # ======================
    # 📊 Agrégation des indicateurs
    # ======================
    ventes = df[df["Type_Ligne"] == "Ventes"].groupby("Code_Analytique", as_index=False)["Crédit"].sum()
    ventes.rename(columns={"Crédit": "Ventes_brutes"}, inplace=True)

    retours = df[df["Type_Ligne"] == "Retours"].groupby("Code_Analytique", as_index=False)["Débit"].sum()
    retours.rename(columns={"Débit": "Retours"}, inplace=True)

    remises = df[df["Type_Ligne"] == "Remises"].groupby("Code_Analytique", as_index=False)["Débit"].sum()
    remises.rename(columns={"Débit": "Remises_libraires"}, inplace=True)

    df_result = ventes.merge(retours, on="Code_Analytique", how="outer")
    df_result = df_result.merge(remises, on="Code_Analytique", how="outer").fillna(0)

    df_result["CA_net_commercial"] = df_result["Ventes_brutes"] - df_result["Remises_libraires"]
    df_result["CA_net_retour"] = df_result["CA_net_commercial"] - df_result["Retours"]

    df_result["Taux_remise_%"] = np.where(df_result["Ventes_brutes"] > 0,
                                          df_result["Remises_libraires"] / df_result["Ventes_brutes"] * 100, 0)
    df_result["Taux_retour_%"] = np.where(df_result["Ventes_brutes"] > 0,
                                          df_result["Retours"] / df_result["Ventes_brutes"] * 100, 0)

    st.subheader("📈 Indicateurs par ISBN")
    st.dataframe(df_result.sort_values("CA_net_retour", ascending=False))

    # ======================
    # 📉 Graphiques
    # ======================
    fig1 = px.bar(df_result.sort_values("Taux_retour_%", ascending=False).head(10),
                  x="Code_Analytique", y="Taux_retour_%",
                  title="Top 10 ISBN avec le plus fort taux de retour",
                  labels={"Code_Analytique": "ISBN", "Taux_retour_%": "Taux de retour (%)"})
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.bar(df_result.sort_values("Taux_remise_%", ascending=False).head(10),
                  x="Code_Analytique", y="Taux_remise_%",
                  title="Top 10 ISBN avec les plus fortes remises",
                  labels={"Code_Analytique": "ISBN", "Taux_remise_%": "Taux de remise (%)"})
    st.plotly_chart(fig2, use_container_width=True)

    # ======================
    # 🔮 Projection prévisionnelle
    # ======================
    st.subheader("🔮 Projection du CA net après retours (tendance historique)")

    # Agrégation mensuelle globale
    df["Mois"] = pd.to_datetime(df["Date"], errors="coerce").dt.to_period("M").astype(str)
    df_temps_ventes = df[df["Type_Ligne"] == "Ventes"].groupby("Mois", as_index=False)["Crédit"].sum()
    df_temps_retours = df[df["Type_Ligne"] == "Retours"].groupby("Mois", as_index=False)["Débit"].sum()

    df_temps = pd.merge(df_temps_ventes, df_temps_retours, on="Mois", how="outer").fillna(0)
    df_temps["Taux_retour_%"] = np.where(df_temps["Crédit"] > 0,
                                         df_temps["Débit"] / df_temps["Crédit"] * 100, 0)

    taux_moyen = round(df_temps["Taux_retour_%"].tail(6).mean(), 2)
    st.info(f"📊 Taux moyen de retour observé sur les 6 derniers mois : **{taux_moyen}%**")

    # Projection sur 3 mois
    if not df_temps.empty:
        dernier_mois = pd.to_datetime(df_temps["Mois"].max()) + pd.offsets.MonthEnd(1)
        projections = []
        ca_moyen = df_temps["Crédit"].tail(3).mean()

        for i in range(1, 4):
            mois_proj = (dernier_mois + pd.offsets.MonthEnd(i)).strftime("%Y-%m")
            retour_proj = ca_moyen * taux_moyen / 100
            ca_net_proj = ca_moyen - retour_proj
            projections.append([mois_proj, ca_moyen, retour_proj, ca_net_proj])

        df_proj = pd.DataFrame(projections, columns=["Mois", "CA_brut_estimé", "Retours_estimés", "CA_net_estimé"])
        st.dataframe(df_proj)

        fig_proj = px.line(df_proj, x="Mois", y=["CA_brut_estimé", "CA_net_estimé"],
                           title="Projection du CA brut et net après retours (3 prochains mois)")
        st.plotly_chart(fig_proj, use_container_width=True)

    # ======================
    # 📤 Export
    # ======================
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_result.to_excel(writer, index=False, sheet_name="Analyse_Retours_Remises")
        if not df_temps.empty:
            df_temps.to_excel(writer, index=False, sheet_name="Historique_Taux_Retour")
        if 'df_proj' in locals():
            df_proj.to_excel(writer, index=False, sheet_name="Projection_CA")
    buffer.seek(0)
    st.download_button("📥 Télécharger le rapport complet", buffer,
                       file_name="Analyse_Retours_Remises_Projection.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
