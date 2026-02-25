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
        # Lecture à partir de la 4ème ligne
        df_source = pd.read_excel(uploaded_file, header=None, skiprows=3)

        # Entrées
        df_entree = df_source.iloc[:, 0:4].copy()
        df_entree.columns = ["Nom", "Facture", "Date", "Montant"]
        df_entree = df_entree.dropna(subset=["Date", "Montant"])
        df_entree["Date"] = pd.to_datetime(df_entree["Date"], errors="coerce")
        df_entree = df_entree.dropna(subset=["Date"])

        # Sorties
        df_sortie = df_source.iloc[:, 5:8].copy()
        df_sortie.columns = ["Nom", "Date", "Montant"]
        df_sortie = df_sortie.dropna(subset=["Date", "Montant"])
        df_sortie["Date"] = pd.to_datetime(df_sortie["Date"], errors="coerce")
        df_sortie = df_sortie.dropna(subset=["Date"])

        # Construction des écritures
        data = []

        # 🔵 TRAITEMENT ENTRÉES
        for _, row in df_entree.iterrows():
            nom_val = row["Nom"]
            facture_val = row["Facture"]
            date = row["Date"]

            try:
                montant = float(str(row["Montant"]).replace(" ", "").replace(",", "."))
            except:
                continue
            if montant == 0:
                continue

            # Libellé par défaut si Nom vide
            if pd.isna(nom_val) or str(nom_val).strip() == "":
                libelle = "Encaissement client"
                premiere_lettre = "X"
            else:
                nom = str(nom_val).strip()
                premiere_lettre = nom[0].upper()
                if pd.isna(facture_val) or str(facture_val).strip() == "":
                    libelle = f"Encaissement {nom}"
                else:
                    libelle = f"Encaissement {nom} - Facture {facture_val}"

            compte_client = f"411{premiere_lettre}0000"

            # Débit caisse
            data.append([date, "CA", "530000000", libelle, round(montant, 2), ""])
            # Crédit client
            data.append([date, "CA", compte_client, libelle, "", round(montant, 2)])

        # 🔴 TRAITEMENT SORTIES
        repas_list = [
            "fonseca", "et patati", "la chaumiere", "les tuileries",
            "le relai d'alcy", "ange", "miss delices", "auguste&ferdinand",
            "le soleil du midi", "chez auriane et tanguy",
            "carrefour express", "la taverne des gaulois",
            "au coin de la reine", "burger king", "au fournil d'arras, lille",
            "tao bento", "paul", "ch'ti boucanier", "cerrefour express"
        ]

        for _, row in df_sortie.iterrows():
            nom_val = row["Nom"]
            date = row["Date"]

            try:
                montant = float(str(row["Montant"]).replace(" ", "").replace(",", "."))
            except:
                continue
            if montant == 0:
                continue

            # Libellé par défaut si Nom vide
            if pd.isna(nom_val) or str(nom_val).strip() == "":
                libelle = "Paiement fournisseur"
                nom_lower = ""
            else:
                nom = str(nom_val).strip()
                libelle = f"Paiement {nom}"
                nom_lower = nom.lower()

            # Comptes fournisseurs
            if "amazon" in nom_lower:
                compte_fournisseur = "401100032"
            elif any(mot in nom_lower for mot in [
                "boulangerie", "restaurant", "resto", "snack",
                "mcdonald", "frite", "hambuscade", "basque"
            ] + repas_list):
                compte_fournisseur = "401100242"
            else:
                compte_fournisseur = "401CAISSE"

            # Débit fournisseur
            data.append([date, "CA", compte_fournisseur, libelle, round(montant, 2), ""])
            # Crédit caisse
            data.append([date, "CA", "530000000", libelle, "", round(montant, 2)])

        # 📊 DATAFRAME FINAL
        df_ecritures = pd.DataFrame(
            data,
            columns=["Date", "Journal", "Compte", "Libellé", "Débit", "Crédit"]
        )

        # Formater date courte
        df_ecritures["Date"] = pd.to_datetime(df_ecritures["Date"]).dt.strftime("%d/%m/%Y")

        # Vérification équilibre
        debit_total = pd.to_numeric(df_ecritures["Débit"], errors="coerce").sum()
        credit_total = pd.to_numeric(df_ecritures["Crédit"], errors="coerce").sum()
        if round(debit_total, 2) == round(credit_total, 2):
            st.success(f"✅ Écritures équilibrées (Total = {debit_total:.2f} €)")
        else:
            st.error(f"❌ Déséquilibre : Débit={debit_total:.2f} / Crédit={credit_total:.2f}")

        # Affichage
        st.dataframe(df_ecritures, use_container_width=True)

        # 💾 EXPORT EXCEL
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
