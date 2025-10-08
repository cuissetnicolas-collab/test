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
# MODULE 1 : DATA EDITION
# =====================
if menu == "DATA EDITION":
    st.header("📂 DATA EDITION - Import des données comptables")
    fichier_comptables = st.file_uploader("Sélectionne ton fichier Excel Pennylane Connect", type=["xlsx"])
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
    st.header("🛠️ SOCLE EDITION - Pivot analytique")
    if "df_comptables" not in st.session_state:
        st.warning("⚠️ Importer d'abord les données comptables depuis DATA EDITION.")
    else:
        df = st.session_state["df_comptables"]

        fichier_volumes = st.file_uploader("📂 Fichier volumes vendus (optionnel)", type=["xlsx", "csv"])
        if fichier_volumes is not None:
            try:
                if fichier_volumes.name.endswith(".csv"):
                    df_vol = pd.read_csv(fichier_volumes)
                else:
                    df_vol = pd.read_excel(fichier_volumes)
                st.session_state["df_volumes"] = df_vol
                st.success("✅ Fichier volumes importé")
            except Exception as e:
                st.error(f"❌ Erreur import volumes : {e}")

        if st.button("Générer SOCLE EDITION"):
            try:
                df.fillna({"Famille_Analytique": "", "Code_Analytique": ""}, inplace=True)
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

                pivot = df.groupby(
                    ["Compte", "Famille_Analytique", "Code_Analytique", "Date"],
                    as_index=False
                ).agg({"Débit": "sum", "Crédit": "sum"})

                # Fusion volumes si disponible
                if "df_volumes" in st.session_state:
                    df_vol = st.session_state["df_volumes"]
                    if "ISBN" in df_vol.columns and "Qté_vendue" in df_vol.columns:
                        pivot = pivot.merge(df_vol[["ISBN", "Qté_vendue"]], left_on="Code_Analytique", right_on="ISBN", how="left")
                        pivot["Qté_vendue"] = pivot["Qté_vendue"].fillna(0)
                        pivot.drop(columns=["ISBN"], inplace=True)
                    else:
                        st.warning("⚠️ Colonnes ISBN ou Qté_vendue manquantes dans le fichier volumes.")

                st.session_state["df_pivot"] = pivot
                st.success("✅ SOCLE EDITION généré")
                st.dataframe(pivot.head(20))
            except Exception as e:
                st.error(f"❌ Erreur génération SOCLE EDITION : {e}")

# =====================
# MODULE 3 : VISION EDITION
# =====================
elif menu == "VISION EDITION":
    st.header("📊 VISION EDITION - Dashboard analytique")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer SOCLE EDITION avant de visualiser le dashboard.")
    else:
        df_pivot = st.session_state["df_pivot"]
        df_pivot["Résultat"] = df_pivot["Crédit"] - df_pivot["Débit"]
        top_isbn = df_pivot.groupby("Code_Analytique", as_index=False)["Résultat"].sum().sort_values(by="Résultat", ascending=False).head(10)
        st.dataframe(top_isbn)
        fig = px.bar(top_isbn, x="Code_Analytique", y="Résultat", title="Top 10 ISBN par résultat net", labels={"Code_Analytique": "ISBN", "Résultat": "Résultat net"})
        st.plotly_chart(fig, use_container_width=True)

# =====================
# MODULE 4 : ISBN VIEW
# =====================
elif menu == "ISBN VIEW":
    st.header("💼 ISBN VIEW - Mini comptes de résultat par ISBN")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer SOCLE EDITION avant.")
    else:
        df_cr = st.session_state["df_pivot"].groupby("Code_Analytique", as_index=False).agg({"Débit": "sum","Crédit": "sum"})
        df_cr["Résultat"] = df_cr["Crédit"] - df_cr["Débit"]
        st.dataframe(df_cr)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_cr.to_excel(writer, index=False, sheet_name="Mini_CR_ISBN")
        buffer.seek(0)
        st.download_button("📥 Télécharger mini compte ISBN", data=buffer, file_name="Mini_Compte_ISBN.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =====================
# MODULE 5 : CASH EDITION
# =====================
elif menu == "CASH EDITION":
    st.header("💰 CASH EDITION - Trésorerie prévisionnelle")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer SOCLE EDITION avant.")
    else:
        df_pivot = st.session_state["df_pivot"]
        date_debut = st.date_input("Date de départ de la trésorerie", pd.to_datetime("2025-04-01"))
        horizon = st.slider("Horizon de projection (mois)", 3, 24, 12)
        croissance_ca = st.number_input("Croissance mensuelle du CA (%)", value=2.0)/100
        evolution_charges = st.number_input("Évolution mensuelle des charges (%)", value=1.0)/100

        df_flux = df_pivot[~df_pivot["Compte"].str.startswith("5")].copy()
        df_flux = df_flux[df_flux["Date"] >= pd.to_datetime(date_debut)]
        df_flux["Mois"] = df_flux["Date"].dt.to_period("M").astype(str)
        flux_mensuel = df_flux.groupby("Mois").agg({"Débit":"sum","Crédit":"sum"}).reset_index()
        flux_mensuel["Solde_mensuel"] = flux_mensuel["Crédit"] - flux_mensuel["Débit"]

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
        comptes_bancaires = df_pivot[df_pivot["Compte"].str.startswith("5")]
        solde_depart_total = comptes_bancaires[comptes_bancaires["Date"] <= pd.to_datetime(date_debut)]["Crédit"].sum() - comptes_bancaires[comptes_bancaires["Date"] <= pd.to_datetime(date_debut)]["Débit"].sum()
        df_tresorerie["Trésorerie_cumulée"] = solde_depart_total + df_tresorerie["Solde_mensuel"].cumsum()

        fig = px.line(df_tresorerie, x="Mois", y="Trésorerie_cumulée", title="📈 Trésorerie prévisionnelle", markers=True)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_tresorerie.style.format({"Débit":"{:,.0f}","Crédit":"{:,.0f}","Solde_mensuel":"{:,.0f}","Trésorerie_cumulée":"{:,.0f}"}))

# =====================
# MODULE 6 : ROYALTIES EDITION
# =====================
elif menu == "ROYALTIES EDITION":
    st.header("👩‍🎨 ROYALTIES EDITION - Droits d'auteurs")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer SOCLE EDITION avant.")
    else:
        df = st.session_state["df_pivot"].copy()
        taux_defaut = st.number_input("Taux royalties par défaut (%)", value=10.0)/100
        st.info("Si vous avez un fichier taux par ISBN, il sera utilisé pour écraser le taux par défaut.")

        if "Qté_vendue" not in df.columns:
            st.warning("⚠️ Quantités vendues non disponibles. ROYALTIES EDITION utilisera 0.")
            df["Qté_vendue"] = 0

        df["Droits_auteur"] = df["Qté_vendue"] * df["Crédit"] * taux_defaut
        st.dataframe(df[["Code_Analytique","Qté_vendue","Droits_auteur"]].head(20))

# =====================
# MODULE 7 : RETURNS EDITION
# =====================
elif menu == "RETURNS EDITION":
    st.header("📦 RETURNS EDITION - Gestion des retours")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer SOCLE EDITION avant.")
    else:
        df = st.session_state["df_pivot"].copy()
        taux_retour_defaut = st.number_input("Taux retour (%)", value=5.0)/100
        st.info("Si un historique est disponible, il sera utilisé. Sinon taux par défaut appliqué.")

        if "Qté_vendue" not in df.columns:
            df["Qté_vendue"] = 0

        df["Provisions_retours"] = df["Qté_vendue"] * taux_retour_defaut
        st.dataframe(df[["Code_Analytique","Qté_vendue","Provisions_retours"]].head(20))
