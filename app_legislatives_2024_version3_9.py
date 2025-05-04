
import streamlit as st
import pandas as pd
import json
import plotly.express as px

votes_df = pd.read_excel("Legislatives_2024_Geo_v1.0.xlsx", sheet_name="Votes")
iris_df = pd.read_excel("Legislatives_2024_Geo_v1.0.xlsx", sheet_name="IRIS_DISP")

iris_df = iris_df.rename(columns={
    "Taux de pauvreté au seuil de 60 % (%)": "Pauvre",
    "dont part des indemnités de chômage (%)": "Chomage",
    "Part des pensions, retraites et rentes (%)": "Pensions",
    "Part de l'ensemble des prestations sociales (%)": "Prestations",
    "dont part des prestations logement (%)": "Prestations_logement"
})

for col in ["Pauvre", "Chomage", "Pensions", "Prestations", "Prestations_logement"]:
    iris_df[col] = iris_df[col].astype(str).str.replace(",", ".").str.extract('([\d\.]+)').astype(float)

partis = ['% ENS', '% LFI', '% RN', '% ECO', '% LR', '% PS', '% UDI', '% REC']

st.title("Carte interactive - Législatives 2024 Paris (Version 3.9)")
st.sidebar.header("Filtres")

parti_selection = st.sidebar.multiselect(
    "Sélectionnez le ou les partis :",
    [p.replace('% ', '') for p in partis],
    default=[p.replace('% ', '') for p in partis]
)

indicateur_selection = st.sidebar.selectbox(
    "Sélectionnez un indicateur social :",
    ["Pauvre", "Chomage", "Pensions", "Prestations", "Prestations_logement"]
)

quartiers = sorted(votes_df['Quartier'].dropna().unique())
quartier_selection = st.sidebar.multiselect(
    "Sélectionnez un ou plusieurs quartiers :",
    quartiers,
    default=quartiers
)

votes_filtered = votes_df[votes_df['Quartier'].isin(quartier_selection)]

votes_agg = votes_filtered.groupby("Quartier")[partis].mean().reset_index()
votes_agg['Parti dominant'] = votes_agg[partis].idxmax(axis=1).str.replace('% ', '')

votes_agg_pct = votes_agg.copy()
for p in partis:
    votes_agg_pct[p] = (votes_agg_pct[p] * 100).round(1)

couleurs_partis = {
    'ENS': '#ADD8E6',
    'LFI': 'red',
    'RN': 'black',
    'ECO': 'green',
    'LR': 'darkblue',
    'PS': 'pink',
    'UDI': 'gray',
    'REC': 'brown',
    'Autre': 'lightgrey'
}

votes_agg_pct['couleur'] = votes_agg_pct['Parti dominant'].map(couleurs_partis)

votes_plot = votes_filtered.merge(
    votes_agg_pct[['Quartier', 'Parti dominant', 'couleur'] + partis],
    on="Quartier", how="left"
)

votes_plot["LAT"] = pd.to_numeric(votes_plot["LAT"], errors="coerce")
votes_plot["LON"] = pd.to_numeric(votes_plot["LON"], errors="coerce")

votes_plot = votes_plot.dropna(subset=["LAT", "LON"])

# ⚠ Correction finale : remplacer les Parti dominant vides ou NaN par "Autre"
votes_plot['Parti dominant'] = votes_plot['Parti dominant'].fillna("Autre").astype(str)
votes_plot.loc[votes_plot['Parti dominant'] == "nan", 'Parti dominant'] = "Autre"

colonnes_existantes = [f"% {p}" for p in parti_selection if f"% {p}" in votes_plot.columns]

if colonnes_existantes and not votes_plot[colonnes_existantes].empty:
    taille_points = votes_plot[colonnes_existantes].max(axis=1)
    taille_points = taille_points.fillna(10)
else:
    taille_points = pd.Series([10] * len(votes_plot))

taille_points = pd.to_numeric(taille_points, errors="coerce").fillna(10)

taille_points = taille_points.reset_index(drop=True)
votes_plot = votes_plot.reset_index(drop=True)

if len(taille_points) != len(votes_plot):
    st.error("Erreur : taille des points et données non alignées.")
elif votes_plot.empty:
    st.warning("Aucune donnée disponible pour les filtres sélectionnés ou les quartiers choisis.")
else:
    fig = px.scatter_mapbox(
        votes_plot,
        lat="LAT",
        lon="LON",
        color=votes_plot['Parti dominant'],
        color_discrete_map=couleurs_partis,
        size=taille_points,
        size_max=20,
        zoom=11,
        mapbox_style="carto-positron",
        hover_name="Quartier",
        hover_data={
            p: (votes_plot[p] * 100).round(1) if p in votes_plot.columns else None
            for p in partis
        }
    )

    fig.update_traces(marker=dict(opacity=0.9))

    geojson_dict = {"type": "FeatureCollection", "features": []}
    for _, row in iris_df.iterrows():
        if pd.notnull(row["Geo"]) and row["Quartier"] in quartier_selection:
            try:
                geometry = json.loads(row["Geo"])
                feature = {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": {
                        "Quartier": row["Quartier"],
                        "Valeur": row[indicateur_selection]
                    }
                }
                geojson_dict["features"].append(feature)
            except Exception:
                pass

    if len(geojson_dict["features"]) > 0:
        fig_choropleth = px.choropleth_mapbox(
            iris_df[iris_df['Quartier'].isin(quartier_selection)],
            geojson=geojson_dict,
            locations="Quartier",
            featureidkey="properties.Quartier",
            color=indicateur_selection,
            color_continuous_scale="YlOrRd",
            range_color=(iris_df[indicateur_selection].min(), iris_df[indicateur_selection].max()),
            mapbox_style="carto-positron",
            opacity=0.4,
            center={"lat": 48.8566, "lon": 2.3522},
            zoom=11
        )
        for trace in fig_choropleth.data:
            fig.add_trace(trace)

    st.plotly_chart(fig, use_container_width=True)

st.header("Résultats détaillés")
for quartier in quartier_selection:
    st.subheader(f"Quartier : {quartier}")
    vote_row = votes_agg_pct[votes_agg_pct['Quartier'] == quartier]
    iris_row = iris_df[iris_df['Quartier'] == quartier]

    if not vote_row.empty:
        for p in partis:
            if p.replace('% ', '') in parti_selection:
                st.write(f"{p} : {vote_row.iloc[0][p]} %")

    if not iris_row.empty:
        ind_value = iris_row.iloc[0][indicateur_selection]
        st.write(f"{indicateur_selection} : {ind_value if pd.notnull(ind_value) else 'N/A'}%")
