import io
import zipfile
from pathlib import Path
from datetime import date
import os
from dotenv import load_dotenv
import requests
import mysql.connector
 
load_dotenv()
 
URL = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/prix-des-carburants-en-france-flux-instantane-v2/exports/csv"
 
# Coordonnées du domicile et rayon de recherche par défaut.

MA_LAT = 48.8566
MA_LON = 2.7800
RAYON_DEFAUT = 15
 
 
REQUETE_STATION = """
INSERT INTO station (id, latitude, longitude, code_postal, pop, adresse, ville)
SELECT id, latitude, longitude, code_postal, pop, adresse, ville
FROM (
    SELECT
        CAST(TRIM(id) AS UNSIGNED)                          AS id,
        CAST(TRIM(latitude)  AS DECIMAL(15,6)) / 100000     AS latitude,
        CAST(TRIM(longitude) AS DECIMAL(15,6)) / 100000     AS longitude,
        TRIM(`code_postal`)                                 AS code_postal,
        TRIM(pop)                                           AS pop,
        TRIM(Adresse)                                       AS adresse,
        TRIM(Ville)                                         AS ville,
        ROW_NUMBER() OVER (PARTITION BY TRIM(id) ORDER BY id) AS rn
    FROM carburants_table
    WHERE TRIM(id)        <> ''
      AND TRIM(latitude)  <> ''
      AND TRIM(longitude) <> ''
) AS classed
WHERE rn = 1
ON DUPLICATE KEY UPDATE
    latitude    = VALUES(latitude),
    longitude   = VALUES(longitude),
    code_postal = VALUES(code_postal),
    pop         = VALUES(pop),
    adresse     = VALUES(adresse),
    ville       = VALUES(ville)
"""
 
REQUETE_RELEVE = """
INSERT INTO releve (station_id, carburant, jour, prix, prix_maj_station)
SELECT CAST(TRIM(id) AS UNSIGNED), 'Gazole', CURDATE(),
       CAST(TRIM(prix_gazole) AS DECIMAL(6,3)),
       STR_TO_DATE(LEFT(NULLIF(TRIM(prix_gazole_maj), ''), 19), '%Y-%m-%dT%H:%i:%s')
FROM carburants_table
WHERE prix_gazole IS NOT NULL AND TRIM(prix_gazole) <> ''
UNION ALL
SELECT CAST(TRIM(id) AS UNSIGNED), 'SP95', CURDATE(),
       CAST(TRIM(prix_sp95) AS DECIMAL(6,3)),
       STR_TO_DATE(LEFT(NULLIF(TRIM(prix_sp95_maj), ''), 19), '%Y-%m-%dT%H:%i:%s')
FROM carburants_table
WHERE prix_sp95 IS NOT NULL AND TRIM(prix_sp95) <> ''
UNION ALL
SELECT CAST(TRIM(id) AS UNSIGNED), 'E85', CURDATE(),
       CAST(TRIM(prix_e85) AS DECIMAL(6,3)),
       STR_TO_DATE(LEFT(NULLIF(TRIM(prix_e85_maj), ''), 19), '%Y-%m-%dT%H:%i:%s')
FROM carburants_table
WHERE prix_e85 IS NOT NULL AND TRIM(prix_e85) <> ''
UNION ALL
SELECT CAST(TRIM(id) AS UNSIGNED), 'GPLc', CURDATE(),
       CAST(TRIM(prix_gplc) AS DECIMAL(6,3)),
       STR_TO_DATE(LEFT(NULLIF(TRIM(prix_gplc_maj), ''), 19), '%Y-%m-%dT%H:%i:%s')
FROM carburants_table
WHERE prix_gplc IS NOT NULL AND TRIM(prix_gplc) <> ''
UNION ALL
SELECT CAST(TRIM(id) AS UNSIGNED), 'E10', CURDATE(),
       CAST(TRIM(prix_e10) AS DECIMAL(6,3)),
       STR_TO_DATE(LEFT(NULLIF(TRIM(prix_e10_maj), ''), 19), '%Y-%m-%dT%H:%i:%s')
FROM carburants_table
WHERE prix_e10 IS NOT NULL AND TRIM(prix_e10) <> ''
UNION ALL
SELECT CAST(TRIM(id) AS UNSIGNED), 'SP98', CURDATE(),
       CAST(TRIM(prix_sp98) AS DECIMAL(6,3)),
       STR_TO_DATE(LEFT(NULLIF(TRIM(prix_sp98_maj), ''), 19), '%Y-%m-%dT%H:%i:%s')
FROM carburants_table
WHERE prix_sp98 IS NOT NULL AND TRIM(prix_sp98) <> ''
ON DUPLICATE KEY UPDATE
    prix             = VALUES(prix),
    prix_maj_station = VALUES(prix_maj_station),
    releve_le        = CURRENT_TIMESTAMP
"""
 
 
 
def se_connecter():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        allow_local_infile=True,
    )
 
 
def telecharger(jour):
    """Télécharge le snapshot du jour (avec cache local)."""
    dossier = Path("data/snapshots")
    dossier.mkdir(parents=True, exist_ok=True)
    cible = dossier / f"{jour.isoformat()}.csv"
 
    if cible.exists():
        print("Déjà présent :", cible.name)
        return cible
 
    print("Téléchargement...")
    r = requests.get(URL, timeout=120)
    r.raise_for_status()
 
    contenu = r.content
    if contenu[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(contenu)) as z:
            nom_interne = z.namelist()[0]
            contenu = z.read(nom_interne)
 
    cible.write_bytes(contenu)
    print("Enregistré :", cible.name)
    return cible
 
def charger_dans_mysql(conn, chemin):
    """Charge le CSV dans carburants_table, puis station et releve."""
    cursor = conn.cursor()
 
  
    cursor.execute("TRUNCATE TABLE carburants_table")
 
 
    cursor.execute(f"""
        LOAD DATA LOCAL INFILE '{chemin.as_posix()}'
        INTO TABLE carburants_table
        CHARACTER SET utf8mb4
        FIELDS TERMINATED BY ';' OPTIONALLY ENCLOSED BY '"'
        LINES TERMINATED BY '\\n'
        IGNORE 1 LINES
        (id, latitude, longitude, code_postal, pop, adresse, ville,
         horaires, services, prix, rupture, geom,
         prix_gazole_maj, prix_gazole,
         prix_sp95_maj,   prix_sp95,
         prix_e85_maj,    prix_e85,
         prix_gplc_maj,   prix_gplc,
         prix_e10_maj,    prix_e10,
         prix_sp98_maj,   prix_sp98,
         debut_rupture_e10,  type_rupture_e10,
         debut_rupture_sp98, type_rupture_sp98,
         debut_rupture_sp95, type_rupture_sp95,
         debut_rupture_e85,  type_rupture_e85,
         debut_rupture_gplc, type_rupture_gplc,
         debut_rupture_gazole, type_rupture_gazole,
         carburants_disponibles, carburants_indisponibles,
         carburants_rupture_temp, carburants_rupture_def,
         automate_24_24,
         @dummy1, @dummy2, @dummy3, @dummy4, @dummy5, @dummy6)
    """)
    print(f"Chargé : {cursor.rowcount} lignes")
 
 
    cursor.execute(REQUETE_STATION)
    print(f"Station : {cursor.rowcount} lignes affectées")
 
    cursor.execute(REQUETE_RELEVE)
    print(f"Relevé : {cursor.rowcount} lignes affectées")
 
    conn.commit()
    cursor.close()
 
 
def top5(conn, carburant="Gazole", rayon=RAYON_DEFAUT, lat=MA_LAT, lon=MA_LON):
    """Affiche les 5 stations les moins chères dans un rayon donné."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.ville, s.adresse, r.prix,
               ROUND(SQRT(
                   POW((s.latitude  - %s) * 111.32, 2) +
                   POW((s.longitude - %s) * 111.32 * COS(RADIANS(%s)), 2)
               ), 3) AS distance_km
        FROM releve r
        JOIN station s ON s.id = r.station_id
        WHERE r.carburant = %s
          AND r.jour = (SELECT MAX(jour) FROM releve)
        HAVING distance_km <= %s
        ORDER BY r.prix ASC, distance_km ASC
        LIMIT 5
    """, (lat, lon, lat, carburant, rayon))
 
    resultats = cursor.fetchall()
    cursor.close()
 
    if not resultats:
        print(f"Aucune station {carburant} trouvée dans un rayon de {rayon} km.")
        return
 
    print(f"\nTop 5 {carburant} dans un rayon de {rayon} km :\n")
    for ville, adresse, prix, distance in resultats:
        print(f"  {prix:.3f} €  |  {distance:6.2f} km  |  {ville} — {adresse}")
 
    return resultats
 
 
def tendance(conn, carburant="Gazole", rayon=RAYON_DEFAUT, lat=MA_LAT, lon=MA_LON):
    cursor = conn.cursor()
    cursor.execute("""
        WITH quotidien AS (
            SELECT
                r.jour,
                ROUND(AVG(r.prix), 3) AS moyenne_du_jour
            FROM releve r
            JOIN station s ON s.id = r.station_id
            WHERE r.carburant = %s
              AND SQRT(
                    POW((s.latitude - %s) * 111.32, 2) +
                    POW((s.longitude - %s) * 111.32 * COS(RADIANS(%s)), 2)
                  ) <= %s
            GROUP BY r.jour
        )
        SELECT
            jour,
            moyenne_du_jour,
            LAG(moyenne_du_jour) OVER (ORDER BY jour) AS moyenne_veille,
            ROUND(
                moyenne_du_jour - LAG(moyenne_du_jour) OVER (ORDER BY jour),
                3
            ) AS variation
        FROM quotidien
        ORDER BY jour
    """, (carburant, lat, lon, lat, rayon))
    resultats = cursor.fetchall()
    cursor.close()
 
    return resultats
 
def notifier(texte, titre="Prix carburants", topic="carburants_marc-antoine-2k26"):
    requests.post(
        f"https://ntfy.sh/{topic}",
        data=texte.encode("utf-8"),
        headers={"Title": titre}
    )
 
 
 
 
 
 
if __name__ == "__main__":
   
    chemin = telecharger(date.today())
 
    
    conn = se_connecter()
 
    
    charger_dans_mysql(conn, chemin)
 
   
    resultats = top5(conn, carburant="Gazole", rayon=RAYON_DEFAUT)
 
    if resultats:   
        lignes = [f"{prix:.3f} € - {ville} ({distance:.1f} km)" 
              for ville, adresse, prix, distance in resultats]
        texte = "\n".join(lignes)
        notifier(texte, titre="Top 5 Gazole")
    
    
     
    print("\nTendance du prix moyen :")
    for jour, moyenne, veille, variation in tendance(conn, "Gazole", RAYON_DEFAUT):
        fleche = "↑" if variation and variation > 0 else ("↓" if variation and variation is not None else "")
        print(f"  {jour}  {moyenne:.3f} €  {fleche} {variation if variation is not None else '—'}")
 
  
    conn.close()
