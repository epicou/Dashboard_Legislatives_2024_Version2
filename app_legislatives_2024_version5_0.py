
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

votes_df["Quartier"] = votes_df["Quartier"].astype(str).str.strip().str.lower()
iris_df["Quartier"] = iris_df["Quartier"].astype(str).str.strip().str.lower()

partis = ['% RN', '% LFI', '% LR', '% ENS', '% DVG', '% REC', '% ECO',
          '% DVC', '% DVD', '% UDI', '% EXG', '% DIV', '% PS']

st.title("Carte interactive - Législatives 2024 Paris (Version 5.0)")
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
    'DVG': 'orange',
    'DVC': 'purple',
    'DVD': 'cyan',
    'EXG': 'darkred',
    'DIV': 'lightgrey',
    'Autre': 'beige'
}

votes_agg_pct['couleur'] = votes_agg_pct['Parti dominant'].map(couleurs_partis)

votes_plot = votes_filtered.merge(
    votes_agg_pct[['Quartier', 'Parti dominant', 'couleur'] + partis],
    on="Quartier", how="left"
)

votes_plot["LAT"] = pd.to_numeric(votes_plot["LAT"], errors="coerce")
votes_plot["LON"] = pd.to_numeric(votes_plot["LON"], errors="coerce")

votes_plot = votes_plot.dropna(subset=["LAT", "LON"])

votes_plot['Parti dominant'] = votes_plot['Parti dominant'].fillna("Autre").astype(str)
votes_plot.loc[votes_plot['Parti dominant'] == "nan", 'Parti dominant'] = "Autre"

colonnes_existantes = [p for p in partis if p in votes_plot.columns and p.replace('% ', '') in parti_selection]

if colonnes_existantes and not votes_plot[colonnes_existantes].empty:
    taille_points = votes_plot[colonnes_existantes].max(axis=1)
    taille_points = taille_points.fillna(10)
else:
    taille_points = pd.Series([10] * len(votes_plot))

taille_points = pd.to_numeric(taille_points, errors="coerce").fillna(10)

taille_points = taille_points.reset_index(drop=True)
votes_plot = votes_plot.reset_index(drop=True)

votes_plot["taille_points"] = taille_points.values

if len(votes_plot) == 0:
    st.warning("Aucune donnée disponible pour les filtres sélectionnés ou les quartiers choisis.")
else:
    hover_data = {
        "Quartier": True,
        "ID_BVOTE": True,
        "LAT": False,
        "LON": False,
        "taille_points": False
    }
    for p in partis:
        if p in votes_plot.columns:
            hover_data[p] = votes_plot[p].round(1)

    # Construction du GeoJSON avec noms de quartiers forcement en minuscules
    geojson_dict = {"type": "FeatureCollection", "features": []}
    for _, row in iris_df[iris_df["Quartier"].isin(quartier_selection)].iterrows():
        if pd.notnull(row["Geo"]):
            try:
                geometry = json.loads(row["Geo"])
                feature = {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": {
                        "Quartier": str(row["Quartier"]).strip().lower(),
                        "Valeur": row[indicateur_selection]
                    }
                }
                geojson_dict["features"].append(feature)
            except Exception:
                pass

    valeurs = iris_df[iris_df["Quartier"].isin(quartier_selection)][indicateur_selection].dropna()
    min_val = float(valeurs.min()) if not valeurs.empty else 0
    max_val = float(valeurs.max()) if not valeurs.empty else min_val + 1

    fig = px.choropleth_mapbox(
        iris_df[iris_df['Quartier'].isin(quartier_selection)],
        geojson=geojson_dict,
        locations="Quartier",
        featureidkey="properties.Quartier",
        color=indicateur_selection,
        color_continuous_scale="YlOrRd",
        range_color=(min_val, max_val) if min_val != max_val else (min_val, min_val + 1),
        mapbox_style="carto-positron",
        opacity=0.5,
        center={"lat": 48.8566, "lon": 2.3522},
        zoom=11,
        labels={indicateur_selection: indicateur_selection},
    )

    scatter = px.scatter_mapbox(
        votes_plot,
        lat="LAT",
        lon="LON",
        color="Parti dominant",
        color_discrete_map=couleurs_partis,
        size="taille_points",
        size_max=20,
        zoom=11,
        mapbox_style="carto-positron",
        hover_name="Quartier",
        hover_data=hover_data
    )

    for trace in scatter.data:
        fig.add_trace(trace)

    st.plotly_chart(fig, use_container_width=True)

st.header("Résultats détaillés")
for quartier in quartier_selection:
    st.subheader(f"Quartier : {quartier.capitalize()}")
    vote_row = votes_agg_pct[votes_agg_pct['Quartier'] == quartier]
    iris_row = iris_df[iris_df['Quartier'] == quartier]

    if not vote_row.empty:
        for p in partis:
            if p.replace('% ', '') in parti_selection:
                st.write(f"{p} : {vote_row.iloc[0][p]} %")

    if not iris_row.empty:
        ind_value = iris_row.iloc[0][indicateur_selection]
        st.write(f"{indicateur_selection} : {ind_value if pd.notnull(ind_value) else 'N/A'}%")
