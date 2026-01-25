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
        st.rerun()
    else:
        st.error("❌ Identifiants incorrects")

if not st.session_state["login"]:
    st.set_page_config(page_title="Connexion", layout="centered")
    st.title("🔑 Connexion espace expert-comptable")
    username = st.text_input("Identifiant")
    password = st.text_input("Mot de passe", type="password")
    if st.button("Connexion"):
        login(username, password)
    st.stop()

# ============================================================
# 🎯 PAGE PRINCIPALE
# ============================================================
st.set_page_config(page_title="Générateur écritures ventes", page_icon="📘", layout="centered")
st.title("📘 Générateur d'écritures comptables – Ventes")
st.caption(f"Connecté en tant que **{st.session_state['name']}**")

if st.button("🔓 Déconnexion"):
    st.session_state["login"] = False
    st.rerun()

uploaded_file = st.file_uploader("📂 Fichier Excel Factura", type=["xls", "xlsx"])

# ============================================================
# 🧠 FONCTIONS UTILITAIRES
# ============================================================
def clean_amount(x):
    if pd.isna(x):
        return 0.0
    return float(
        str(x)
        .replace("€", "")
        .replace("%", "")
        .replace(" ", "")
        .replace(",", ".")
    )

def compte_client(nom):
    nom = str(nom).strip().upper()
    lettre = nom[0] if nom and nom[0].isalpha() else "X"
    return f"4110{lettre}0000"

def compte_vente_mono(taux):
    mapping = {
        5.5: "704000000",
        10.0: "704100000",
        20.0: "704200000",
        0.0: "704500000"
    }
    return mapping.get(taux, "704300000")

# ============================================================
# 🚀 TRAITEMENT
# ============================================================
if uploaded_file:
    df = pd.read_excel(uploaded_file, dtype=str)
    df.columns = df.columns.str.strip()

    required_cols = [
        "N° Facture",
        "Date",
        "Nom Facture",
        "Total HT",
        "Taux de tva"
    ]

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"❌ Colonnes manquantes : {', '.join(missing)}")
        st.stop()

    df = df[required_cols]
    df.columns = ["Facture", "Date", "Client", "HT", "Taux"]

    df["HT"] = df["HT"].apply(clean_amount)
    df["Taux"] = df["Taux"].apply(clean_amount)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%d/%m/%Y")

    ecritures = []

    # ========================================================
    # 🔒 BOUCLE UNIQUE PAR FACTURE (ANTI-DOUBLON)
    # ========================================================
    for facture, g in df.groupby("Facture"):

        date = g["Date"].iloc[0]
        client = g["Client"].iloc[0]
        compte_cli = compte_client(client)
        libelle = f"Facture {facture} - {client}"

        ht_facture = g["HT"].max()  # Total HT facture (répété sur lignes)
        taux_uniques = sorted(g["Taux"].dropna().unique())

        if ht_facture == 0:
            continue

        # ====================================================
        # 🧮 CALCUL TVA
        # ====================================================
        if len(taux_uniques) == 1:
            # ----- MONO TVA -----
            taux = taux_uniques[0]
            tva = round(ht_facture * taux / 100, 2)
            ttc = round(ht_facture + tva, 2)

            ecritures.append({
                "Date": date,
                "Journal": "VT",
                "Numéro de compte": compte_cli,
                "Numéro de pièce": facture,
                "Libellé": libelle,
                "Débit": ttc,
                "Crédit": ""
            })

            ecritures.append({
                "Date": date,
                "Journal": "VT",
                "Numéro de compte": compte_vente_mono(taux),
                "Numéro de pièce": facture,
                "Libellé": libelle,
                "Débit": "",
                "Crédit": ht_facture
            })

            if tva != 0:
                ecritures.append({
                    "Date": date,
                    "Journal": "VT",
                    "Numéro de compte": "445740000",
                    "Numéro de pièce": facture,
                    "Libellé": libelle,
                    "Débit": "",
                    "Crédit": tva
                })

        else:
            # ----- MULTI TVA (sécurisé) -----
            tva_totale = 0

            for taux in taux_uniques:
                part_ht = ht_facture * (
                    (g.loc[g["Taux"] == taux, "HT"].count()) / len(g)
                )
                tva_part = round(part_ht * taux / 100, 2)
                tva_totale += tva_part

                if tva_part != 0:
                    ecritures.append({
                        "Date": date,
                        "Journal": "VT",
                        "Numéro de compte": "445740000",
                        "Numéro de pièce": facture,
                        "Libellé": f"{libelle} TVA {taux}%",
                        "Débit": "",
                        "Crédit": tva_part
                    })

            ttc = round(ht_facture + tva_totale, 2)

            ecritures.append({
                "Date": date,
                "Journal": "VT",
                "Numéro de compte": compte_cli,
                "Numéro de pièce": facture,
                "Libellé": libelle,
                "Débit": ttc,
                "Crédit": ""
            })

            ecritures.append({
                "Date": date,
                "Journal": "VT",
                "Numéro de compte": "704300000",
                "Numéro de pièce": facture,
                "Libellé": libelle,
                "Débit": "",
                "Crédit": ht_facture
            })

    # ========================================================
    # 📊 SORTIE
    # ========================================================
    df_out = pd.DataFrame(ecritures)

    st.success(f"✅ {df_out['Numéro de pièce'].nunique()} factures générées")

    total_debit = pd.to_numeric(df_out["Débit"], errors="coerce").sum()
    total_credit = pd.to_numeric(df_out["Crédit"], errors="coerce").sum()

    st.info(
        f"Débit : {total_debit:,.2f} € | "
        f"Crédit : {total_credit:,.2f} € | "
        f"Écart : {total_debit - total_credit:,.2f} €"
    )

    st.dataframe(df_out.head(20))

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_out.to_excel(writer, index=False, sheet_name="Écritures")
    output.seek(0)

    st.download_button(
        "💾 Télécharger les écritures",
        data=output,
        file_name="ecritures_ventes.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("⬆️ Charge un fichier Excel Factura pour commencer")
