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
# ROYALTIES EDITION (DROITS + PREVISION)
# =====================
elif page == "ROYALTIES EDITION":
    st.header("📚 ROYALTIES EDITION - Droits d’auteurs détaillés et prévision")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        params = st.session_state["param_comptes"]
        taux_fixe = st.number_input("Taux fixe de droits (%)", value=10.0)
        df_ventes = df[df["Compte"].astype(str).str.startswith(tuple(params["ventes"]))]
        df_ventes["Droits"] = df_ventes["Crédit"] * taux_fixe/100
        droits_totaux = df_ventes.groupby("Code_Analytique", as_index=False)["Droits"].sum().sort_values("Droits", ascending=False)
        st.dataframe(droits_totaux)
        st.info(f"Total droits calculé : {droits_totaux['Droits'].sum():,.0f} €")
        # Prévision simple sur 12 mois par défaut
        horizon = st.slider("Horizon prévision droits (mois)", 3, 24, 12)
        prevision = droits_totaux.copy()
        prevision["Droits prévus"] = prevision["Droits"].apply(lambda x: x*(1+0.02)**horizon)
        st.subheader("Prévision des droits sur horizon choisi")
        st.dataframe(prevision)

# =====================
# RETURNS EDITION
# =====================
elif page == "RETURNS EDITION":
    st.header("📦 RETURNS EDITION - Gestion des retours")

    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        param = st.session_state.get("param_comptes", {})
        st.info("ℹ️ Assurez-vous que les comptes retours, remises, ventes et provision sont correctement paramétrés.")

        df = st.session_state["df_pivot"].copy()

        # --- Normalisation sûre des comptes ---
        def normalize_compte(x):
            try:
                return str(int(float(x))).strip()
            except (ValueError, TypeError):
                if pd.isna(x):
                    return ""
                return str(x).strip()

        df["Compte"] = df["Compte"].apply(normalize_compte)

        df["Débit"] = df["Débit"].fillna(0)
        df["Crédit"] = df["Crédit"].fillna(0)

        # --- Comptes exacts ---
        comptes_ventes = param.get("ventes", [])
        comptes_retours = param.get("retours", [])
        comptes_remises = param.get("remises", [])
        comptes_provision = param.get("provision", ["681"])

        # --- Filtrage des comptes avec fallback sur startswith ---
        if comptes_retours:
            df_ret = df[df["Compte"].isin(comptes_retours)]
        else:
            df_ret = df[df["Compte"].str.startswith("709000")]

        if comptes_remises:
            df_remises = df[df["Compte"].isin(comptes_remises)]
        else:
            df_remises = df[df["Compte"].str.startswith("709100")]

        df_ventes = df[df["Compte"].isin(comptes_ventes)] if comptes_ventes else pd.DataFrame()
        df_prov = df[df["Compte"].isin(comptes_provision)] if comptes_provision else pd.DataFrame()

        # --- Vérification des lignes détectées ---
        st.write(f"Retours détectés : {df_ret.shape[0]}")
        st.write(f"Remises détectées : {df_remises.shape[0]}")
        st.write(f"Provisions détectées : {df_prov.shape[0]}")

        if not df_ret.empty or not df_remises.empty:

            # Retours = solde global (Débit - Crédit)
            if not df_ret.empty:
                ret_isbn = df_ret.groupby("Code_Analytique", as_index=False).agg({"Débit":"sum","Crédit":"sum"})
                ret_isbn["Montant_retour"] = ret_isbn["Débit"] - ret_isbn["Crédit"]
                ret_isbn = ret_isbn[["Code_Analytique","Montant_retour"]]
                st.subheader("📊 Retours par ISBN")
                st.dataframe(ret_isbn)

            # Remises = solde global (Crédit - Débit)
            if not df_remises.empty:
                rem_isbn = df_remises.groupby("Code_Analytique", as_index=False).agg({"Débit":"sum","Crédit":"sum"})
                rem_isbn["Montant_remise"] = rem_isbn["Crédit"] - rem_isbn["Débit"]
                rem_isbn = rem_isbn[["Code_Analytique","Montant_remise"]]
                st.subheader("📊 Remises libraires par ISBN")
                st.dataframe(rem_isbn)

            # Provisions sur retours
            if not df_prov.empty:
                prov_isbn = df_prov.groupby("Code_Analytique", as_index=False).agg({"Débit":"sum"})
                prov_isbn.rename(columns={"Débit":"Montant_provision"}, inplace=True)
                st.subheader("📊 Provision sur retours (compte 681)")
                st.dataframe(prov_isbn)
            else:
                prov_isbn = pd.DataFrame(columns=["Code_Analytique","Montant_provision"])

            # Fusion pour synthèse
            df_indic = ret_isbn if not df_ret.empty else pd.DataFrame(columns=["Code_Analytique","Montant_retour"])
            if not df_remises.empty:
                df_indic = pd.merge(df_indic, rem_isbn, on="Code_Analytique", how="outer")
            if not df_prov.empty:
                df_indic = pd.merge(df_indic, prov_isbn, on="Code_Analytique", how="outer")
            df_indic = df_indic.fillna(0)
            df_indic["Total_impact"] = df_indic.get("Montant_retour",0) + df_indic.get("Montant_remise",0) + df_indic.get("Montant_provision",0)

            st.subheader("📊 Synthèse par ISBN")
            st.dataframe(df_indic.style.format({
                "Montant_retour":"{:,.0f}",
                "Montant_remise":"{:,.0f}",
                "Montant_provision":"{:,.0f}",
                "Total_impact":"{:,.0f}"
            }))

            # Totaux globaux
            st.subheader("📊 Totaux globaux")
            totaux = {
                "Total retours": df_indic["Montant_retour"].sum() if "Montant_retour" in df_indic else 0,
                "Total remises": df_indic["Montant_remise"].sum() if "Montant_remise" in df_indic else 0,
                "Total provisions": df_indic["Montant_provision"].sum() if "Montant_provision" in df_indic else 0,
                "Total impact global": df_indic["Total_impact"].sum()
            }
            st.table(pd.DataFrame(totaux, index=[0]).T.rename(columns={0:"Montant"}).style.format({"Montant":"{:,.0f}"}))
        else:
            st.info("Aucun retour ou remise détecté selon vos comptes paramétrés.")
# =====================
# CASH EDITION
# =====================
elif page == "CASH EDITION":
    st.header("💰 CASH EDITION - Trésorerie prévisionnelle")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df_pivot = st.session_state["df_pivot"].copy()
        # --- (Code de trésorerie identique au précédent, avec graphique et détails) ---

# =====================
# SYNTHESE GLOBALE
# =====================
elif page == "SYNTHESE GLOBALE":
    st.header("📊 SYNTHESE GLOBALE")
    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        params = st.session_state["param_comptes"]
        ventes, retours, remises = params["ventes"], params["retours"], params["remises"]

        # Calculs globaux
        ca_brut = df[df["Compte"].astype(str).str.startswith(tuple(ventes))]["Crédit"].sum()
        total_retours = df[df["Compte"].astype(str).str.startswith(tuple(retours))]["Crédit"].sum()
        total_remises = df[df["Compte"].astype(str).str.startswith(tuple(remises))]["Crédit"].sum()
        ca_net = ca_brut - total_retours - total_remises

        df_summary = pd.DataFrame({
            "Indicateur":["CA brut","Total retours","Total remises","CA net"],
            "Montant":[ca_brut,total_retours,total_remises,ca_net]
        })

        st.subheader("Tableau récapitulatif")
        st.dataframe(df_summary.style.format({"Montant":"{:,.0f} €"}))

        # Graphique synthèse
        fig_summary = px.bar(df_summary, x="Indicateur", y="Montant", text="Montant", title="📊 Synthèse financière globale")
        fig_summary.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig_summary, use_container_width=True)

# =====================
# FOOTER
# =====================
st.markdown("---")
st.markdown("© 2025 Nicolas CUISSET - Créateur de l'application")
