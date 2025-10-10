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
    - Obtenir une synthèse globale (**SYNTHESE GLOBALE**)  
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
        st.subheader("Mapping des colonnes")
        st.markdown("Mappez les colonnes de votre fichier Excel vers les champs standards utilisés par l'application.")
        columns = list(df.columns)
        compte_col = st.selectbox("Colonne des comptes", columns)
        debit_col = st.selectbox("Colonne Débit", columns)
        credit_col = st.selectbox("Colonne Crédit", columns)
        famille_col = st.selectbox("Colonne Famille analytique (optionnel)", [""]+columns)
        code_col = st.selectbox("Colonne Code analytique / ISBN (optionnel)", [""]+columns)
        date_col = st.selectbox("Colonne Date", columns)

        st.subheader("Paramétrage des comptes clés")
        ventes_comptes = st.text_input("Numéros de comptes ventes (séparés par virgule)", value="701")
        retours_comptes = st.text_input("Numéros de comptes retours", value="709")
        remises_comptes = st.text_input("Numéros de comptes remises", value="7091")
        charges_comptes = st.text_input("Numéros de comptes charges fixes", value="6")

        st.subheader("Charges fixes imputées")
        charges_imputees = st.radio("Les charges fixes ont-elles déjà été imputées par section ?", ["Oui", "Non"])

        if st.button("Générer le SOCLE"):
            mapping = {compte_col:"Compte", debit_col:"Débit", credit_col:"Crédit"}
            if famille_col!="": mapping[famille_col]="Famille_Analytique"
            if code_col!="": mapping[code_col]="Code_Analytique"
            mapping[date_col]="Date"
            df.rename(columns=mapping, inplace=True)
            for col in ["Famille_Analytique","Code_Analytique"]:
                if col not in df.columns: df[col]=""
                else: df[col]=df[col].fillna("")
            df["Date"]=pd.to_datetime(df["Date"], errors="coerce")
            pivot = df.groupby(["Compte","Famille_Analytique","Code_Analytique","Date"], as_index=False).agg({"Débit":"sum","Crédit":"sum"})
            st.session_state["df_pivot"]=pivot
            st.session_state["param_comptes"] = {
                "ventes":[c.strip() for c in ventes_comptes.split(",")],
                "retours":[c.strip() for c in retours_comptes.split(",")],
                "remises":[c.strip() for c in remises_comptes.split(",")],
                "charges":[c.strip() for c in charges_comptes.split(",")],
                "charges_imputees": charges_imputees
            }
            st.success("✅ SOCLE EDITION généré et paramétré.")
            st.dataframe(pivot.head(20))
            st.info("ℹ️ Note : assurez-vous que les colonnes et comptes sont correctement renseignés pour votre logiciel.")

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
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        taux_fixe = st.number_input("Taux fixe de droits (%)", value=10.0)
        ca_brut = df[df["Compte"].astype(str).str.startswith(tuple(st.session_state["param_comptes"]["ventes"]))]["Crédit"].sum()
        droits_auteurs = ca_brut * taux_fixe / 100
        st.info(f"💰 Droits d’auteurs estimés : {droits_auteurs:,.0f} €")

# =====================
# RETURNS EDITION
# =====================
elif page == "RETURNS EDITION":
    st.header("📦 RETURNS EDITION - Gestion des retours")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        ventes = st.session_state["param_comptes"]["ventes"]
        retours = st.session_state["param_comptes"]["retours"]
        remises = st.session_state["param_comptes"]["remises"]

        df["Type"] = df["Compte"].astype(str).apply(lambda x: "Vente" if any(x.startswith(v) for v in ventes)
                                                    else "Retour" if any(x.startswith(r) for r in retours)
                                                    else "Remise" if any(x.startswith(m) for m in remises)
                                                    else "Autre")
        retour_df = df[df["Type"].isin(["Retour","Remise"])].copy()
        st.subheader("Indicateurs de retours")
        total_retours = retour_df[retour_df["Type"]=="Retour"]["Crédit"].sum()
        total_remises = retour_df[retour_df["Type"]=="Remise"]["Crédit"].sum()
        st.metric("Total retours", f"{total_retours:,.0f} €")
        st.metric("Total remises", f"{total_remises:,.0f} €")
        st.dataframe(retour_df.head(20))

# =====================
# CASH EDITION
# =====================
elif page == "CASH EDITION":
    st.header("💰 CASH EDITION - Trésorerie prévisionnelle")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df_pivot = st.session_state["df_pivot"].copy()
        # --- Trésorerie comme tu avais fourni ---
        date_debut = st.date_input("Date de départ de la trésorerie", pd.to_datetime("2025-04-01"))
        df_pivot["Compte"] = df_pivot["Compte"].astype(str).str.strip()
        df_pivot["Date"] = pd.to_datetime(df_pivot["Date"], errors="coerce")
        df_pivot["Débit"] = pd.to_numeric(df_pivot["Débit"], errors="coerce").fillna(0)
        df_pivot["Crédit"] = pd.to_numeric(df_pivot["Crédit"], errors="coerce").fillna(0)
        comptes_bancaires = df_pivot[df_pivot["Compte"].str.startswith("5")]
        solde_depart_total = (comptes_bancaires[comptes_bancaires["Date"] <= pd.to_datetime(date_debut)]["Crédit"].sum() - 
                              comptes_bancaires[comptes_bancaires["Date"] <= pd.to_datetime(date_debut)]["Débit"].sum())
        st.info(f"Solde de départ : {solde_depart_total:,.2f} €")
        horizon = st.slider("Horizon de projection (en mois)", 3, 24, 12)
        croissance_ca = st.number_input("Croissance mensuelle du CA (%)", value=2.0) / 100
        evolution_charges = st.number_input("Évolution mensuelle des charges (%)", value=1.0) / 100
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
            previsions.append({"Mois": prochain_mois, "Débit": charges_actuelles, "Crédit": ca_actuel, "Solde_mensuel": solde_prevu})
        df_prev = pd.DataFrame(previsions)
        df_tresorerie = pd.concat([flux_mensuel, df_prev], ignore_index=True)
        df_tresorerie["Trésorerie_cumulée"] = solde_depart_total + df_tresorerie["Solde_mensuel"].cumsum()
        fig = px.line(df_tresorerie, x="Mois", y="Trésorerie_cumulée", title="📈 Évolution prévisionnelle de la trésorerie", markers=True)
        fig.update_layout(xaxis_title="Mois", yaxis_title="Trésorerie (€)")
        st.plotly_chart(fig, use_container_width=True)
        st.subheader("📋 Détail mensuel")
        st.dataframe(df_tresorerie.style.format({"Débit":"{:,.0f}","Crédit":"{:,.0f}","Solde_mensuel":"{:,.0f}","Trésorerie_cumulée":"{:,.0f}"}))

# =====================
# SYNTHESE GLOBALE
# =====================
elif page == "SYNTHESE GLOBALE":
    st.header("📊 SYNTHESE GLOBALE")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        param = st.session_state["param_comptes"]
        ventes = param["ventes"]
        retours = param["retours"]
        remises = param["remises"]
        ca_brut = df[df["Compte"].astype(str).str.startswith(tuple(ventes))]["Crédit"].sum()
        total_retours = df[df["Compte"].astype(str).str.startswith(tuple(retours))]["Crédit"].sum()
        total_remises = df[df["Compte"].astype(str).str.startswith(tuple(remises))]["Crédit"].sum()
        ca_net = ca_brut - total_retours - total_remises
        taux_droits = 10.0
        droits_auteurs = ca_net * taux_droits / 100
        st.metric("💰 Chiffre d'affaires brut", f"{ca_brut:,.0f} €")
        st.metric("📦 Retours", f"{total_retours:,.0f} €")
        st.metric("🔖 Remises", f"{total_remises:,.0f} €")
        st.metric("📈 Résultat net", f"{ca_net:,.0f} €")
        st.metric("💰 Droits d’auteurs estimés", f"{droits_auteurs:,.0f} €")
        df_ca = pd.DataFrame({"Catégorie":["CA Brut","Retours","Remises","CA Net"],"Montant":[ca_brut,total_retours,total_remises,ca_net]})
        fig1 = px.bar(df_ca, x="Catégorie", y="Montant", title="💹 Synthèse CA et Retours")
        st.plotly_chart(fig1, use_container_width=True)
        df_isbn = df.groupby("Code_Analytique", as_index=False).agg({"Débit":"sum","Crédit":"sum"})
        df_isbn["Résultat"] = df_isbn["Crédit"] - df_isbn["Débit"]
        df_isbn = df_isbn.sort_values("Résultat", ascending=False).head(10)
        fig2 = px.bar(df_isbn, x="Code_Analytique", y="Résultat", title="Top 10 ISBN par Résultat")
        st.plotly_chart(fig2, use_container_width=True)

# =====================
# FOOTER
# =====================
st.markdown("---")
st.markdown("© 2025 Nicolas CUISSET - Créateur de l'application")
