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
# PAGE D’ACCUEIL
# =====================
st.sidebar.success(f"Bienvenue {st.session_state['name']} 👋")
if st.sidebar.button("Déconnexion"):
    st.session_state["login"] = False
    st.experimental_rerun()

page_accueil = st.sidebar.checkbox("🏠 Accueil / Présentation", value=True)

if page_accueil:
    st.title("📚 Bienvenue dans l'outil global Edition")
    st.markdown("""
    Cet outil permet de piloter l'activité d'une petite maison d'édition en centralisant :
    - L'import des données comptables analytiques (**DATA EDITION**)
    - La génération d'un socle pivot analytique (**SOCLE EDITION**)
    - Les dashboards et mini comptes de résultat (**VISION EDITION & ISBN VIEW**)
    - Le suivi de trésorerie prévisionnelle (**CASH EDITION**)
    - Le suivi des droits d'auteurs (**ROYALTIES EDITION**)
    - La gestion des retours (**RETURNS EDITION**)
    
    Sélectionnez un module dans le menu ci-dessous pour commencer.
    """)
    st.stop()

# =====================
# MENU PRINCIPAL
# =====================
menu = st.sidebar.selectbox(
    "Sélectionner le module",
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
# MODULE 1 : DATA EDITION
# =====================
if menu == "DATA EDITION":
    st.header("📂 DATA EDITION - Import données comptables")
    fichier_comptables = st.file_uploader("Importer le fichier Excel comptable", type=["xlsx"])
    if fichier_comptables is not None:
        try:
            df = pd.read_excel(fichier_comptables, header=0)
            df.columns = df.columns.str.strip()
            st.write("Colonnes détectées :", list(df.columns))

            # Mapping standard
            col_mapping = {}
            if "Numéro de compte" in df.columns: col_mapping["Numéro de compte"] = "Compte"
            if "Débit" in df.columns: col_mapping["Débit"] = "Débit"
            if "Crédit" in df.columns: col_mapping["Crédit"] = "Crédit"
            if "Familles de catégories" in df.columns: col_mapping["Famille_Analytique"] = "Famille_Analytique"
            if "Catégories" in df.columns: col_mapping["Code_Analytique"] = "Code_Analytique"
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
    st.header("🛠️ SOCLE EDITION - Socle pivot analytique")
    if "df_comptables" not in st.session_state:
        st.warning("⚠️ Importer d'abord les données comptables dans DATA EDITION.")
    else:
        df = st.session_state["df_comptables"]
        # Remplir colonnes analytiques manquantes
        for col in ["Famille_Analytique", "Code_Analytique"]:
            if col not in df.columns:
                df[col] = ""
            else:
                df[col] = df[col].fillna("")
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        pivot = df.groupby(["Compte", "Famille_Analytique", "Code_Analytique", "Date"], as_index=False).agg({"Débit": "sum", "Crédit": "sum"})
        st.session_state["df_pivot"] = pivot
        st.success("✅ Socle pivot généré")
        st.dataframe(pivot.head(20))

# =====================
# MODULE 3 : VISION EDITION
# =====================
elif menu == "VISION EDITION":
    st.header("📊 VISION EDITION - Dashboard analytique")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df_pivot = st.session_state["df_pivot"]
        df_pivot["Résultat"] = df_pivot["Crédit"] - df_pivot["Débit"]
        top_isbn = df_pivot.groupby("Code_Analytique", as_index=False)["Résultat"].sum().sort_values(by="Résultat", ascending=False).head(10)
        st.dataframe(top_isbn)
        fig = px.bar(top_isbn, x="Code_Analytique", y="Résultat", title="Top 10 ISBN par résultat net", labels={"Code_Analytique":"ISBN", "Résultat":"Résultat net"})
        st.plotly_chart(fig, use_container_width=True)

# =====================
# MODULE 4 : ISBN VIEW
# =====================
elif menu == "ISBN VIEW":
    st.header("💼 ISBN VIEW - Mini compte de résultat par ISBN")
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
        st.download_button("📥 Télécharger le mini compte de résultat par ISBN", data=buffer, file_name="Mini_Compte_Resultat_ISBN.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =====================
# MODULE 5 : CASH EDITION
# =====================
elif menu == "CASH EDITION":
    st.header("💰 CASH EDITION - Trésorerie prévisionnelle")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df_pivot = st.session_state["df_pivot"]
        df_pivot["Compte"] = df_pivot["Compte"].astype(str).str.strip()
        df_pivot["Date"] = pd.to_datetime(df_pivot["Date"], errors="coerce")
        df_pivot["Débit"] = pd.to_numeric(df_pivot["Débit"], errors="coerce").fillna(0)
        df_pivot["Crédit"] = pd.to_numeric(df_pivot["Crédit"], errors="coerce").fillna(0)

        date_debut = st.date_input("Date de départ de la trésorerie", pd.to_datetime("2025-04-01"))
        comptes_bancaires = df_pivot[df_pivot["Compte"].str.startswith("5")]
        solde_depart_total = (comptes_bancaires[comptes_bancaires["Date"] <= pd.to_datetime(date_debut)]["Crédit"].sum()
                              - comptes_bancaires[comptes_bancaires["Date"] <= pd.to_datetime(date_debut)]["Débit"].sum())
        st.info(f"Solde de départ : {solde_depart_total:,.2f} €")

        horizon = st.slider("Horizon de projection (mois)", 3, 24, 12)
        croissance_ca = st.number_input("Croissance mensuelle du CA (%)", value=2.0)/100
        evolution_charges = st.number_input("Évolution mensuelle des charges (%)", value=1.0)/100

        df_flux = df_pivot[~df_pivot["Compte"].str.startswith("5")].copy()
        df_flux = df_flux.dropna(subset=["Date"])
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
            prochain_mois = (dernier_mois + i).strftime("%Y-%m")
            ca_actuel *= (1 + croissance_ca)
            charges_actuelles *= (1 + evolution_charges)
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
# MODULE 6 & 7 : ROYALTIES EDITION & RETURNS EDITION
# =====================
elif menu in ["ROYALTIES EDITION", "RETURNS EDITION"]:
    st.header(f"📚 {menu}")

    # Initialisation mémoire BLDD
    if "df_bldd" not in st.session_state:
        st.session_state["df_bldd"] = {}

    mois_selection = st.selectbox("Sélection du mois pour les données BLDD", ["2025-04","2025-05","2025-06"])
    if mois_selection not in st.session_state["df_bldd"]:
        fichier_bldd = st.file_uploader(f"Importer le BLDD du mois {mois_selection}", type=["xlsx"], key=f"bldd_{mois_selection}")
        if fichier_bldd is not None:
            df_bldd = pd.read_excel(fichier_bldd, header=9, dtype={"ISBN": str})
            df_bldd.columns = df_bldd.columns.str.strip()
            df_bldd = df_bldd.dropna(subset=["ISBN"])
            df_bldd["ISBN"] = df_bldd["ISBN"].astype(str).str.replace(r'\.0$', '', regex=True).str.replace('-', '').str.replace(' ', '')
            for c in ["Vente","Net","Facture"]:
                df_bldd[c] = pd.to_numeric(df_bldd[c], errors="coerce").fillna(0).round(2)
            st.session_state["df_bldd"][mois_selection] = df_bldd
            st.success(f"✅ BLDD du mois {mois_selection} importé et stocké")
    else:
        df_bldd = st.session_state["df_bldd"][mois_selection]
        st.info(f"BLDD du mois {mois_selection} déjà en mémoire")

    if df_bldd is not None and "df_pivot" in st.session_state:
        df_socle = st.session_state["df_pivot"]
        df_merge = df_socle.merge(df_bldd[["ISBN","Vente","Net","Facture"]], left_on="Code_Analytique", right_on="ISBN", how="left")

        if menu == "ROYALTIES EDITION":
            taux_royalties = st.number_input("Taux de droits d'auteurs (%)", value=10.0)/100
            df_merge["Droits_auteurs"] = df_merge["Vente"] * taux_royalties
            st.subheader("💰 Calcul des droits d'auteurs par ISBN")
            st.dataframe(df_merge[["Code_Analytique","Vente","Droits_auteurs"]])
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_merge[["Code_Analytique","Vente","Droits_auteurs"]].to_excel(writer, index=False, sheet_name="Royalties")
            buffer.seek(0)
            st.download_button("📥 Télécharger le fichier ROYALTIES EDITION", data=buffer, file_name=f"Royalties_{mois_selection}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        elif menu == "RETURNS EDITION":
            st.subheader("📦 Gestion des retours prévisionnels")
            coeff_retour = st.number_input("Coefficient de prévision des retours (%)", value=5.0)/100
            df_merge["Prévision_retours"] = df_merge["Vente"] * coeff_retour
            st.dataframe(df_merge[["Code_Analytique","Vente","Prévision_retours"]])
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_merge[["Code_Analytique","Vente","Prévision_retours"]].to_excel(writer, index=False, sheet_name="Returns")
            buffer.seek(0)
            st.download_button("📥 Télécharger le fichier RETURNS EDITION", data=buffer, file_name=f"Returns_{mois_selection}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
