# RETURNS EDITION
# =====================
elif page == "RETURNS EDITION":
    st.header("📦 RETURNS EDITION - Gestion des retours automatiques")

    if "df_pivot" not in st.session_state:
        st.warning("⚠️ Générer d'abord le SOCLE EDITION.")
    else:
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

        # --- Détection automatique des comptes ---
        comptes_retours = [c for c in df["Compte"].unique() if c.startswith("709000")]
        comptes_remises = [c for c in df["Compte"].unique() if c.startswith("709100")]
        comptes_provision = [c for c in df["Compte"].unique() if c.startswith("681")]

        st.write("ℹ️ Comptes détectés automatiquement :")
        st.write(f"Retours : {comptes_retours}")
        st.write(f"Remises : {comptes_remises}")
        st.write(f"Provisions : {comptes_provision}")

        # --- Filtrage ---
        df_ret = df[df["Compte"].isin(comptes_retours)]
        df_remises = df[df["Compte"].isin(comptes_remises)]
        df_prov = df[df["Compte"].isin(comptes_provision)]

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
            st.info("Aucun retour ou remise détecté selon vos comptes présents dans le SOCLE.")
