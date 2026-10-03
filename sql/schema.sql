
-- À exécuter une seule fois, juste après la création de la base :
--   mysql -uroot prixcarburants < sql/schema.sql

CREATE TABLE IF NOT EXISTS carburants_table (
    id                        VARCHAR(20),
    latitude                  VARCHAR(20),
    longitude                 VARCHAR(20),
    code_postal               VARCHAR(10),
    pop                       VARCHAR(5),
    adresse                   TEXT,
    ville                     VARCHAR(100),
    horaires                  TEXT,
    services                  TEXT,
    prix                      TEXT,
    rupture                   TEXT,
    geom                      VARCHAR(50),
    prix_gazole_maj           VARCHAR(30),
    prix_gazole               VARCHAR(10),
    prix_sp95_maj             VARCHAR(30),
    prix_sp95                 VARCHAR(10),
    prix_e85_maj              VARCHAR(30),
    prix_e85                  VARCHAR(10),
    prix_gplc_maj             VARCHAR(30),
    prix_gplc                 VARCHAR(10),
    prix_e10_maj              VARCHAR(30),
    prix_e10                  VARCHAR(10),
    prix_sp98_maj             VARCHAR(30),
    prix_sp98                 VARCHAR(10),
    debut_rupture_e10         VARCHAR(30),
    type_rupture_e10          VARCHAR(20),
    debut_rupture_sp98        VARCHAR(30),
    type_rupture_sp98         VARCHAR(20),
    debut_rupture_sp95        VARCHAR(30),
    type_rupture_sp95         VARCHAR(20),
    debut_rupture_e85         VARCHAR(30),
    type_rupture_e85          VARCHAR(20),
    debut_rupture_gplc        VARCHAR(30),
    type_rupture_gplc         VARCHAR(20),
    debut_rupture_gazole      VARCHAR(30),
    type_rupture_gazole       VARCHAR(20),
    carburants_disponibles    TEXT,
    carburants_indisponibles  TEXT,
    carburants_rupture_temp   TEXT,
    carburants_rupture_def    TEXT,
    automate_24_24            VARCHAR(5)
);


-- Table des stations : données stables (adresse, coordonnées).
-- Une ligne par station, jamais dupliquée (clé primaire = id).

CREATE TABLE IF NOT EXISTS station (
    id           INT PRIMARY KEY,
    latitude     DECIMAL(9, 6),
    longitude    DECIMAL(9, 6),
    code_postal  VARCHAR(10),
    pop          VARCHAR(10),
    adresse      VARCHAR(255),
    ville        VARCHAR(150)
);


-- Table de l'historique des prix : une ligne par (station, carburant, jour). La clé primaire composite garantit qu'aucun doublon n'est possible, même en cas de


CREATE TABLE IF NOT EXISTS releve (
    station_id        INT            NOT NULL,
    carburant         VARCHAR(10)    NOT NULL,
    jour              DATE           NOT NULL,
    prix              DECIMAL(6,3)   NOT NULL,
    prix_maj_station  DATETIME       NULL,
    releve_le         DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (station_id, carburant, jour),

    CONSTRAINT fk_releve_station
        FOREIGN KEY (station_id) REFERENCES station(id)
        ON DELETE CASCADE,

    CONSTRAINT chk_releve_prix
        CHECK (prix > 0),

    CONSTRAINT chk_releve_carburant
        CHECK (carburant IN ('Gazole', 'SP95', 'E85', 'GPLc', 'E10', 'SP98'))
) ENGINE=InnoDB;
