
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
iris_df["IRIS"] = iris_df["IRIS"].astype(str).str.strip()

partis = ['% RN', '% LFI', '% LR', '% ENS', '% DVG', '% REC', '% ECO',
          '% DVC', '% DVD', '% UDI', '% EXG', '% DIV', '% PS']

st.title("Carte interactive - Législatives 2024 Paris (Version 5.6)")
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

# Taille proportionnelle
votes_plot["% dominant"] = 0
for index, row in votes_plot.iterrows():
    parti_dom = row["Parti dominant"]
    col_parti = f"% {parti_dom}"
    if col_parti in votes_plot.columns:
        votes_plot.at[index, "% dominant"] = row[col_parti]
    else:
        votes_plot.at[index, "% dominant"] = 0

votes_plot["taille_points"] = votes_plot["% dominant"].fillna(0) * 50
votes_plot.loc[votes_plot["taille_points"] < 5, "taille_points"] = 5

# -------------------------
# Info-bulle = top 3 partis
# -------------------------
def top3_partis(row):
    scores = {p.replace("% ", ""): row[p] for p in partis if p in row.index}
    top3 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
    txt = ""
    for i, (parti, score) in enumerate(top3):
        txt += f"{i+1}er : {parti} - {round(score*100,1)}%<br>"
    return txt

votes_plot["custom_hover"] = votes_plot.apply(
    lambda row: f"Quartier : {row['Quartier'].capitalize()}<br>ID_BVOTE : {row['ID_BVOTE']}<br>{top3_partis(row)}",
    axis=1
)

# ------------------------------
# GeoJSON IRIS
# ------------------------------

geojson_dict = {"type": "FeatureCollection", "features": []}
for _, row in iris_df[iris_df["Quartier"].isin(quartier_selection)].iterrows():
    if pd.notnull(row["Geo"]):
        try:
            geometry = json.loads(row["Geo"])
            feature = {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "IRIS": row["IRIS"],
                    "Valeur": row[indicateur_selection]
                }
            }
            geojson_dict["features"].append(feature)
        except Exception:
            pass

valeurs = iris_df[iris_df["Quartier"].isin(quartier_selection)][indicateur_selection].dropna()
min_val = float(valeurs.min()) if not valeurs.empty else 0
max_val = float(valeurs.max()) if not valeurs.empty else min_val + 1

# Choroplèthe
fig = px.choropleth_mapbox(
    iris_df[iris_df['Quartier'].isin(quartier_selection)],
    geojson=geojson_dict,
    locations="IRIS",
    featureidkey="properties.IRIS",
    color=indicateur_selection,
    color_continuous_scale="YlOrRd",
    range_color=(min_val, max_val) if min_val != max_val else (min_val, min_val + 1),
    mapbox_style="carto-positron",
    opacity=0.5,
    center={"lat": 48.8566, "lon": 2.3522},
    zoom=11
)

# Points BV avec customdata
scatter = px.scatter_mapbox(
    votes_plot,
    lat="LAT",
    lon="LON",
    color="Parti dominant",
    color_discrete_map=couleurs_partis,
    size="taille_points",
    size_max=40,
    zoom=11,
    mapbox_style="carto-positron",
    custom_data=["custom_hover"]
)

for trace in scatter.data:
    trace.hovertemplate = "%{customdata[0]}<extra></extra>"
    fig.add_trace(trace)

st.plotly_chart(fig, use_container_width=True)

st.header("Résultats détaillés")
for quartier in quartier_selection:
    st.subheader(f"Quartier : {quartier.capitalize()}")
    vote_row = votes_agg_pct[votes_agg_pct['Quartier'] == quartier]
    iris_rows = iris_df[iris_df['Quartier'] == quartier]

    if not vote_row.empty:
        for p in partis:
            if p.replace('% ', '') in parti_selection:
                st.write(f"{p} : {vote_row.iloc[0][p]} %")

    if not iris_rows.empty:
        for idx, row in iris_rows.iterrows():
            ind_value = row[indicateur_selection]
            st.write(f"IRIS {row['IRIS']} — {indicateur_selection} : {ind_value if pd.notnull(ind_value) else 'N/A'}%")
