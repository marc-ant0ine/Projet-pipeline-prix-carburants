import streamlit as st
import pandas as pd
from carburant import se_connecter, tendance
from carte import recuperer_stations

st.title("Prix des carburants")

@st.cache_data(ttl=3600)
def charger_stations(carburant):
    conn = se_connecter()
    stations = recuperer_stations(conn, carburant=carburant)
    conn.close()
    return stations

carburants_disponibles = ["Gazole", "SP95", "SP98", "E10", "E85", "GPLc"]
carburant = st.selectbox("Choisis un carburant", carburants_disponibles)

stations = charger_stations(carburant)

st.write(f"{len(stations)} stations trouvées pour {carburant}")

df = pd.DataFrame(stations, columns=["ville", "adresse", "latitude", "longitude", "prix"])
st.dataframe(
    df[["ville", "adresse", "prix"]].sort_values("prix"),
    hide_index=True
)



@st.cache_data(ttl=3600)
def charger_tendance(carburant):
    conn = se_connecter()
    resultats = tendance(conn, carburant=carburant, rayon=15)
    conn.close()
    return resultats

st.subheader("Évolution du prix moyen")

historique = charger_tendance(carburant)

if not historique:
    st.warning("Aucune donnée de tendance disponible.")
else:
    df_tendance = pd.DataFrame(
        historique,
        columns=["jour", "moyenne", "veille", "variation"]
    )

    if len(df_tendance) < 2:
        st.info("Pas encore assez de données pour tracer une courbe (minimum 2 jours).")
    else:
        st.line_chart(df_tendance.set_index("jour")["moyenne"])

    st.dataframe(
        df_tendance.style.format({
            "moyenne": "{:.3f} €",
            "veille":  "{:.3f} €",
            "variation": "{:+.3f} €",
        }, na_rep="—")
)

    if len(df_tendance) < 7:
        st.caption(
            f"{len(df_tendance)} jour(s) de données — "
            f"la courbe s'enrichira automatiquement chaque jour grâce au cron."
        )

