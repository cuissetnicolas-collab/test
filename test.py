import streamlit as st
import pandas as pd

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(page_title="Générateur écritures ventes", layout="centered")
st.title("📘 Générateur d'écritures comptables – Ventes")

# ============================================================
# UPLOAD
# ============================================================
uploaded_file = st.file_uploader("📂 Fichier Excel Factura", type=["xls", "xlsx"])

# ============================================================
# FONCTIONS
# ============================================================
def clean_amount(x):
    if pd.isna(x):
        return 0.0
    return float(str(x).replace("€", "").replace("%", "").replace(" ", "").replace(",", "."))

def compte_client(nom):
    nom = str(nom).strip().upper()
    lettre = nom[0] if nom and nom[0].isalpha() else "X"
    return f"4110{lettre}0000"

def compte_vente(taux):
    return {
        5.5: "704000000",
        10.0: "704100000",
        20.0: "704200000",
        0.0: "704500000"
    }.get(taux, "704300000")

# ============================================================
# TRAITEMENT
# ============================================================
if uploaded_file:

    df = pd.read_excel(uploaded_file, dtype=str)
    df.columns = df.columns.str.strip()

    df = df[[
        "N° Facture",
        "Date",
        "Nom Facture",
        "Total HT",
        "Total HT d'origine sur quantité unitaire",
        "Taux de tva"
    ]]

    df.columns = ["Facture", "Date", "Client", "HT_FACTURE", "HT_LIGNE", "Taux"]

    df["HT_FACTURE"] = df["HT_FACTURE"].apply(clean_amount)
    df["HT_LIGNE"] = df["HT_LIGNE"].apply(clean_amount)
    df["Taux"] = df["Taux"].apply(clean_amount)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%d/%m/%Y")

    ecritures = []

    for facture, g in df.groupby("Facture"):

        date = g["Date"].iloc[0]
        client = g["Client"].iloc[0]
        ht_facture = g["HT_FACTURE"].max()
        compte_cli = compte_client(client)
        libelle = f"Facture {facture} - {client}"

        # 🔎 ANALYSE DES LIGNES
        lignes_avec_ht = g[g["HT_LIGNE"] != 0]
        taux_non_nuls = sorted(g.loc[g["Taux"] != 0, "Taux"].unique())

        # ====================================================
        # CAS 1 — HT LIGNE = 0 PARTOUT → RAISONNEMENT FACTURE
        # ====================================================
        if lignes_avec_ht.empty:

            taux_uniques = sorted(g["Taux"].unique())

            # MONO TVA (y compris 0 %)
            if len(taux_uniques) == 1:
                taux = taux_uniques[0]
                tva = round(ht_facture * taux / 100, 2)
                ttc = round(ht_facture + tva, 2)

                ecritures.append({
                    "Date": date, "Journal": "VT", "Numéro de compte": compte_cli,
                    "Numéro de pièce": facture, "Libellé": libelle,
                    "Débit": ttc, "Crédit": ""
                })

                ecritures.append({
                    "Date": date, "Journal": "VT", "Numéro de compte": compte_vente(taux),
                    "Numéro de pièce": facture, "Libellé": libelle,
                    "Débit": "", "Crédit": ht_facture
                })

                if taux != 0:
                    ecritures.append({
                        "Date": date, "Journal": "VT", "Numéro de compte": "445740000",
                        "Numéro de pièce": facture, "Libellé": libelle,
                        "Débit": "", "Crédit": tva
                    })

            else:
                st.warning(f"⚠️ Facture {facture} : plusieurs taux mais HT non ventilé")

        # ====================================================
        # CAS 2 — VRAI MULTI TVA (HT PAR LIGNE)
        # ====================================================
        else:
            if len(taux_non_nuls) <= 1:
                # MONO TVA malgré plusieurs lignes
                taux = taux_non_nuls[0] if taux_non_nuls else 0.0
                tva = round(ht_facture * taux / 100, 2)
                ttc = round(ht_facture + tva, 2)

                ecritures.append({
                    "Date": date, "Journal": "VT", "Numéro de compte": compte_cli,
                    "Numéro de pièce": facture, "Libellé": libelle,
                    "Débit": ttc, "Crédit": ""
                })

                ecritures.append({
                    "Date": date, "Journal": "VT", "Numéro de compte": compte_vente(taux),
                    "Numéro de pièce": facture, "Libellé": libelle,
                    "Débit": "", "Crédit": ht_facture
                })

                if taux != 0:
                    ecritures.append({
                        "Date": date, "Journal": "VT", "Numéro de compte": "445740000",
                        "Numéro de pièce": facture, "Libellé": libelle,
                        "Débit": "", "Crédit": tva
                    })

            else:
                # VRAI MULTI TVA
                tva_totale = 0

                for taux in taux_non_nuls:
                    ht_ligne = lignes_avec_ht.loc[lignes_avec_ht["Taux"] == taux, "HT_LIGNE"].sum()
                    tva = round(ht_ligne * taux / 100, 2)
                    tva_totale += tva

                    ecritures.append({
                        "Date": date, "Journal": "VT", "Numéro de compte": "445740000",
                        "Numéro de pièce": facture,
                        "Libellé": f"{libelle} TVA {taux}%",
                        "Débit": "", "Crédit": tva
                    })

                ttc = round(ht_facture + tva_totale, 2)

                ecritures.append({
                    "Date": date, "Journal": "VT", "Numéro de compte": compte_cli,
                    "Numéro de pièce": facture, "Libellé": libelle,
                    "Débit": ttc, "Crédit": ""
                })

                ecritures.append({
                    "Date": date, "Journal": "VT", "Numéro de compte": "704300000",
                    "Numéro de pièce": facture, "Libellé": libelle,
                    "Débit": "", "Crédit": ht_facture
                })

    # ============================================================
    # SORTIE
    # ============================================================
    df_out = pd.DataFrame(ecritures)
    st.success(f"✅ {df_out['Numéro de pièce'].nunique()} factures générées")
    st.dataframe(df_out)
