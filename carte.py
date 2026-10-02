from carburant import se_connecter
import statistics
import folium
import branca.colormap as cm

def construire_echelle(prix_liste):
    prix_tries = sorted(prix_liste)
    n = len(prix_tries)

    indice_bas = int(n * 0.05)
    indice_haut = int(n * 0.95)

    bas = prix_tries[indice_bas]
    haut = prix_tries[indice_haut]

    return float(bas), float(haut)   

def recuperer_stations(conn, carburant="Gazole"):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.ville, s.adresse, s.latitude, s.longitude, r.prix
        FROM releve r
        JOIN station s ON s.id = r.station_id
        WHERE r.carburant = %s
          AND r.jour = (SELECT MAX(jour) FROM releve)
    """, (carburant,))
    resultats = cursor.fetchall()
    cursor.close()
    return resultats

def construire_carte(stations, bas, haut):
    couleur = cm.LinearColormap(
        colors=["green", "yellow", "orange", "red"],
        vmin=bas,
        vmax=haut
    )

    carte = folium.Map(location=[48.8566, 2.78], zoom_start=11)

    for ville, adresse, lat, lon, prix in stations:
        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color="white",
            weight=1,
            fill=True,
            fill_color=couleur(float(prix)),
            fill_opacity=0.9,
            popup=f"{prix} € — {ville}, {adresse}"
        ).add_to(carte)

        fill_color=couleur(float(prix)),

    return carte



if __name__ == "__main__":
    conn = se_connecter()
    stations = recuperer_stations(conn, carburant="Gazole")
    print(f"{len(stations)} stations récupérées")

    prix_liste = [prix for (ville, adresse, lat, lon, prix) in stations]
    bas, haut = construire_echelle(prix_liste)
    print(f"Échelle : {bas} € (vert) → {haut} € (rouge)")
    print(f"Min réel : {min(prix_liste)} €  |  Max réel : {max(prix_liste)} €")

    carte = construire_carte(stations, bas, haut)
    carte.save("carte_gazole.html")
    conn.close()
