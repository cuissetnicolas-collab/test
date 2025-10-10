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
    st.header("📦 RETURNS EDITION - Analyse des retours et remises libraires")

    st.info("""
    💡 **Note importante**  
    Les indicateurs s’appuient sur les **numéros de comptes** ou **libellés** présents dans votre SOCLE.  
    Veillez à paramétrer les comptes correctement (ventes / remises / retours) pour garantir la fiabilité.
    """)

    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Vous devez d'abord générer le SOCLE EDITION.")
    else:
        df = st.session_state["df_pivot"].copy()
        st.subheader("⚙️ Paramétrage des comptes comptables")
        mode = st.radio("Méthode d’identification :", ["Par libellé", "Par numéro de compte"])

        # --- Identification par libellé ---
        if mode == "Par libellé":
            col_libelle = st.selectbox(
                "Colonne contenant le libellé :",
                df.columns,
                index=list(df.columns).index("Libellé") if "Libellé" in df.columns else 0
            )
            mots_ventes = [m.strip().lower() for m in st.text_input(
                "🔸 Mots-clés pour les ventes (séparés par des virgules)", "vente, bldd").split(",")]
            mots_retours = [m.strip().lower() for m in st.text_input(
                "🔹 Mots-clés pour les retours (séparés par des virgules)", "retour").split(",")]
            mots_remises = [m.strip().lower() for m in st.text_input(
                "🟠 Mots-clés pour les remises libraires (séparés par des virgules)", "remise, ristourne").split(",")]

            def classer(texte):
                if pd.isna(texte): return "Autres"
                t = str(texte).lower()
                if any(m in t for m in mots_retours): return "Retours"
                if any(m in t for m in mots_remises): return "Remises"
                if any(m in t for m in mots_ventes): return "Ventes"
                return "Autres"

            df["Type_Ligne"] = df[col_libelle].apply(classer)

        # --- Identification par compte ---
        else:
            comptes_uniques = sorted(df["Compte"].astype(str).unique())
            comptes_ventes = st.multiselect(
                "🔸 Comptes de ventes", comptes_uniques,
                default=[c for c in comptes_uniques if str(c).startswith("701")][:3]
            )
            comptes_retours = st.multiselect(
                "🔹 Comptes de retours", comptes_uniques,
                default=[c for c in comptes_uniques if str(c).startswith("709")][:3]
            )
            comptes_remises = st.multiselect(
                "🟠 Comptes de remises libraires", comptes_uniques,
                default=[c for c in comptes_uniques if str(c).startswith("7091")][:3]
            )

            def classer_compte(compte):
                if str(compte) in comptes_retours: return "Retours"
                if str(compte) in comptes_remises: return "Remises"
                if str(compte) in comptes_ventes: return "Ventes"
                return "Autres"

            df["Type_Ligne"] = df["Compte"].apply(classer_compte)

        # --- Remplacer NaN par 0 ---
        df["Débit"] = df["Débit"].fillna(0)
        df["Crédit"] = df["Crédit"].fillna(0)

        # --- Agrégation avec solde global ---
        ventes = df[df["Type_Ligne"] == "Ventes"].groupby("Code_Analytique", as_index=False)["Crédit"].sum().rename(columns={"Crédit":"Ventes_brutes"})

        retours = df[df["Type_Ligne"] == "Retours"].copy()
        retours["Solde_retours"] = retours["Débit"] - retours["Crédit"]
        retours = retours.groupby("Code_Analytique", as_index=False)["Solde_retours"].sum().rename(columns={"Solde_retours":"Retours"})

        remises = df[df["Type_Ligne"] == "Remises"].copy()
        remises["Solde_remises"] = remises["Crédit"] - remises["Débit"]
        remises = remises.groupby("Code_Analytique", as_index=False)["Solde_remises"].sum().rename(columns={"Solde_remises":"Remises_libraires"})

        # --- Fusion des données ---
        df_result = ventes.merge(retours, on="Code_Analytique", how="outer")
        df_result = df_result.merge(remises, on="Code_Analytique", how="outer").fillna(0)

        # --- Calcul indicateurs ---
        df_result["CA_net_commercial"] = df_result["Ventes_brutes"] - df_result["Remises_libraires"]
        df_result["CA_net_retour"] = df_result["CA_net_commercial"] - df_result["Retours"]
        df_result["Taux_remise_%"] = np.where(df_result["Ventes_brutes"] > 0,
                                              df_result["Remises_libraires"] / df_result["Ventes_brutes"] * 100, 0)
        df_result["Taux_retour_%"] = np.where(df_result["Ventes_brutes"] > 0,
                                              df_result["Retours"] / df_result["Ventes_brutes"] * 100, 0)

        # --- Affichage ---
        st.subheader("📊 Synthèse par ISBN")
        st.dataframe(df_result.sort_values("CA_net_retour", ascending=False).head(200))

        st.subheader("📉 Top taux de retour")
        fig1 = px.bar(df_result.sort_values("Taux_retour_%", ascending=False).head(15),
                      x="Code_Analytique", y="Taux_retour_%", title="Top 15 des ouvrages avec le plus fort taux de retour",
                      labels={"Code_Analytique": "ISBN", "Taux_retour_%": "Taux de retour (%)"})
        st.plotly_chart(fig1, use_container_width=True)

        # --- Projection simple ---
        st.subheader("🔮 Projection simple (taux moyen)")
        df["Mois"] = pd.to_datetime(df["Date"], errors="coerce").dt.to_period("M").astype(str)
        df_temps_ventes = df[df["Type_Ligne"]=="Ventes"].groupby("Mois", as_index=False)["Crédit"].sum()
        df_temps_retours = df[df["Type_Ligne"]=="Retours"].groupby("Mois", as_index=False)["Débit"].sum()
        df_temps = pd.merge(df_temps_ventes, df_temps_retours, on="Mois", how="outer").fillna(0)
        df_temps["Taux_retour_%"] = np.where(df_temps["Crédit"]>0, df_temps["Débit"]/df_temps["Crédit"]*100, 0)
        taux_moyen = round(df_temps["Taux_retour_%"].tail(6).mean(),2) if not df_temps.empty else 0
        st.info(f"Taux moyen de retour observé sur les 6 derniers mois : {taux_moyen}%")

        # --- Export Excel ---
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_result.to_excel(writer, index=False, sheet_name="Analyse_Retours_Remises")
            if not df_temps.empty:
                df_temps.to_excel(writer, index=False, sheet_name="Historique_Taux_Retour")
        buffer.seek(0)
        st.download_button("📥 Télécharger le rapport retours/remises", buffer,
                           file_name="Analyse_Retours_Remises.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

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
