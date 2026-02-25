import streamlit as st
import pandas as pd
from io import BytesIO

# ============================================================
# 🔐 AUTHENTIFICATION
# ============================================================

if "login" not in st.session_state:
    st.session_state["login"] = False

def login(username, password):
    users = {
        "aurore": {"password": "12345", "name": "Aurore Demoulin"},
        "laure.froidefond": {"password": "Laure2019$", "name": "Laure Froidefond"},
        "Bruno": {"password": "Toto1963$", "name": "Toto El Gringo"},
        "Manana": {"password": "193827", "name": "Manana"}
    }

    if username in users and password == users[username]["password"]:
        st.session_state["login"] = True
        st.session_state["name"] = users[username]["name"]
        st.success(f"Bienvenue {st.session_state['name']} 👋")
        st.rerun()
    else:
        st.error("❌ Identifiants incorrects")

if not st.session_state["login"]:
    st.title("🔑 Connexion espace expert-comptable")
    username_input = st.text_input("Identifiant")
    password_input = st.text_input("Mot de passe", type="password")
    if st.button("Connexion"):
        login(username_input, password_input)
    st.stop()

# ============================================================
# 🧾 PAGE JOURNAL DE CAISSE
# ============================================================

st.title("🏦 Génération d’écritures comptables - Journal de caisse")

uploaded_file = st.file_uploader(
    "📤 Importer le fichier Excel de caisse",
    type=["xlsx", "xls"]
)

if uploaded_file:
    try:
        # Commencer à lire à partir de la 4ème ligne (index 3)
        df_source = pd.read_excel(uploaded_file, header=None, skiprows=3)

        df_entree = df_source.iloc[:, 0:4].copy()
        df_entree.columns = ["Nom", "Facture", "Date", "Montant"]
        df_entree = df_entree.dropna(subset=["Date", "Montant"])
        df_entree["Date"] = pd.to_datetime(df_entree["Date"], errors="coerce")
        df_entree = df_entree.dropna(subset=["Date"])

        df_sortie = df_source.iloc[:, 5:8].copy()
        df_sortie.columns = ["Nom", "Date", "Montant"]
        df_sortie = df_sortie.dropna(subset=["Date", "Montant"])
        df_sortie["Date"] = pd.to_datetime(df_sortie["Date"], errors="coerce")
        df_sortie = df_sortie.dropna(subset=["Date"])

        data = []

        # ============================================================
        # 🔵 TRAITEMENT ENTREES
        # ============================================================

        for _, row in df_entree.iterrows():
            nom = str(row["Nom"]).strip()
            date = row["Date"]
            try:
                montant = float(str(row["Montant"]).replace(" ", "").replace(",", "."))
            except:
                continue
            if montant == 0:
                continue

            premiere_lettre = nom[0].upper()
            compte_client = f"411{premiere_lettre}0000"

            # Débit caisse
            data.append([date, "CA", "530000000",
                         f"Encaissement {nom}",
                         round(montant, 2), ""])

            # Crédit client
            data.append([date, "CA", compte_client,
                         f"Encaissement {nom}",
                         "", round(montant, 2)])

        # ============================================================
        # 🔴 TRAITEMENT SORTIES
        # ============================================================

        for _, row in df_sortie.iterrows():
            nom = str(row["Nom"]).strip()
            date = row["Date"]
            try:
                montant = float(str(row["Montant"]).replace(" ", "").replace(",", "."))
            except:
                continue
            if montant == 0:
                continue

            nom_lower = nom.lower()
            if "amazon" in nom_lower:
                compte_fournisseur = "401100032"
            elif any(mot in nom_lower for mot in [
                "boulangerie", "restaurant", "resto", "snack",
                "mcdonald", "frite", "hambuscade", "basque"
            ]):
                compte_fournisseur = "401100242"
            else:
                compte_fournisseur = "401CAISSE"

            # Débit fournisseur
            data.append([date, "CA", compte_fournisseur,
                         f"Paiement {nom}",
                         round(montant, 2), ""])

            # Crédit caisse
            data.append([date, "CA", "530000000",
                         f"Paiement {nom}",
                         "", round(montant, 2)])

        # ============================================================
        # 📊 DATAFRAME FINAL
        # ============================================================

        df_ecritures = pd.DataFrame(
            data,
            columns=["Date", "Journal", "Compte", "Libellé", "Débit", "Crédit"]
        )

        debit_total = pd.to_numeric(df_ecritures["Débit"], errors="coerce").sum()
        credit_total = pd.to_numeric(df_ecritures["Crédit"], errors="coerce").sum()

        if round(debit_total, 2) == round(credit_total, 2):
            st.success(f"✅ Écritures équilibrées (Total = {debit_total:.2f} €)")
        else:
            st.error(f"❌ Déséquilibre : Débit={debit_total:.2f} / Crédit={credit_total:.2f}")

        st.dataframe(df_ecritures, use_container_width=True)

        # ============================================================
        # 💾 EXPORT EXCEL
        # ============================================================

        buffer = BytesIO()
        df_ecritures.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        st.download_button(
            "📥 Télécharger les écritures",
            data=buffer,
            file_name="journal_caisse.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"❌ Erreur lors du traitement : {e}")
