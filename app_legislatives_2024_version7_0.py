
import streamlit as st
import pandas as pd
import json
import folium
from folium import Choropleth, CircleMarker
from streamlit_folium import st_folium

# --- Chargement des données ---
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

# --- Paramètres ---
partis = ['% RN', '% LFI', '% LR', '% ENS', '% DVG', '% REC', '% ECO',
          '% DVC', '% DVD', '% UDI', '% EXG', '% DIV', '% PS']

st.title("Carte interactive - Législatives 2024 Paris (Version 7.0 — Folium)")
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

# Taille des points
votes_plot["% dominant"] = 0
for index, row in votes_plot.iterrows():
    parti_dom = row["Parti dominant"]
    col_parti = f"% {parti_dom}"
    if col_parti in votes_plot.columns:
        votes_plot.at[index, "% dominant"] = row[col_parti]
    else:
        votes_plot.at[index, "% dominant"] = 0

votes_plot["taille_points"] = votes_plot["% dominant"].fillna(0) * 100  # échelle plus grande
votes_plot.loc[votes_plot["taille_points"] < 10, "taille_points"] = 10

# --- Fonctions hover ---
def top3_partis(row):
    scores = {p.replace("% ", ""): row[p] for p in partis if p in row.index}
    top3 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
    txt = ""
    for i, (parti, score) in enumerate(top3):
        txt += f"{i+1}er : {parti} - {round(score*100,1)}%<br>"
    return txt

votes_plot["popup"] = votes_plot.apply(
    lambda row: f"<b>Quartier :</b> {row['Quartier'].capitalize()}<br><b>ID_BVOTE :</b> {row['ID_BVOTE']}<br>{top3_partis(row)}",
    axis=1
)

# --- Création carte Folium ---
m = folium.Map(location=[48.8566, 2.3522], zoom_start=12, tiles="cartodbpositron")

# --- Polygones IRIS ---
geojson_features = []
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
            geojson_features.append(feature)
        except Exception:
            pass

geojson_dict = {"type": "FeatureCollection", "features": geojson_features}

if len(geojson_features) > 0:
    Choropleth(
        geo_data=geojson_dict,
        name="Indicateur social",
        data=iris_df,
        columns=["IRIS", indicateur_selection],
        key_on="feature.properties.IRIS",
        fill_color="YlOrRd",
        fill_opacity=0.5,
        line_opacity=0.2,
        legend_name=indicateur_selection
    ).add_to(m)

# --- Points BV ---
for idx, row in votes_plot.iterrows():
    CircleMarker(
        location=[row["LAT"], row["LON"]],
        radius=row["taille_points"] / 15,  # ajustement visuel
        color=couleurs_partis.get(row["Parti dominant"], "beige"),
        fill=True,
        fill_opacity=0.8,
        popup=folium.Popup(row["popup"], max_width=300)
    ).add_to(m)

# --- Affichage carte ---
st_data = st_folium(m, width=1000, height=600)

# --- Résultats détaillés ---
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
