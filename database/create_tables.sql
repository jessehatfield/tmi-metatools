PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "Tournament" (
  "T_ID" INTEGER PRIMARY KEY,
  "T_NAME" varchar(255) DEFAULT NULL,
  "PLAYERS" int(11) DEFAULT NULL,
  "CITY" varchar(255) DEFAULT NULL,
  "STATE" varchar(255) DEFAULT NULL,
  "COUNTRY" varchar(255) DEFAULT NULL,
  "T_DATE" date DEFAULT NULL,
  "FORMAT" varchar(255) DEFAULT NULL,
  "SOURCE" varchar(255) DEFAULT NULL,
  "PLACE_INVALID" tinyint(1) DEFAULT '0'
);
CREATE TABLE IF NOT EXISTS "Deck" (
  "DECK_ID" INTEGER PRIMARY KEY,
  "T_ID" int(64) DEFAULT NULL,
  "PLAYER_NAME" varchar(255) DEFAULT NULL,
  "DECK_NAME" varchar(255) DEFAULT 'Unknown',
  "PLACE" int(11) DEFAULT NULL,
  "SPLIT" varchar(15) DEFAULT NULL,
  "ORIGINAL" varchar(255) DEFAULT NULL,
  "QUALIFIER" varchar(255) DEFAULT '',
  "RECORD" varchar(255) DEFAULT NULL,
  "POINTS" int(11) DEFAULT NULL,
  FOREIGN KEY ("T_ID") REFERENCES Tournament("T_ID") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "Matches" (
  "MATCH_ID" INTEGER PRIMARY KEY,
  "DECK_1" int(64) NOT NULL,
  "WIN" smallint(5)  NOT NULL DEFAULT '0',
  "LOSS" smallint(5)  NOT NULL DEFAULT '0',
  "DRAW" smallint(5)  NOT NULL DEFAULT '0',
  "DECK_2" int(64)  NOT NULL,
  "T_ID" int(64)  NOT NULL,
  "ROUND" varchar(255) NOT NULL DEFAULT '0',
  "TABLE_NUM" int(11) DEFAULT NULL,
  FOREIGN KEY ("T_ID") REFERENCES Tournament("T_ID") ON DELETE CASCADE,
  FOREIGN KEY ("DECK_1") REFERENCES Deck("DECK_ID") ON DELETE CASCADE,
  FOREIGN KEY ("DECK_2") REFERENCES Deck("DECK_ID") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "Contents" (
  "DECK_ID" int(64)  NOT NULL DEFAULT '0',
  "CARD_NAME" varchar(255) NOT NULL DEFAULT '',
  "NUM_MAIN" int(11) DEFAULT '0',
  "NUM_SIDE" int(11) DEFAULT '0',
  FOREIGN KEY ("DECK_ID") REFERENCES Deck("DECK_ID") ON DELETE CASCADE,
  PRIMARY KEY ("DECK_ID","CARD_NAME")
);
CREATE TABLE IF NOT EXISTS "Card" (
  "CARD_NAME" varchar(255) NOT NULL DEFAULT '',
  "COST" varchar(64) DEFAULT NULL,
  "TEXT" blob,
  "EDITIONS" varchar(512) DEFAULT NULL,
  "POWER" varchar(16) DEFAULT NULL,
  "TOUGHNESS" varchar(16) DEFAULT NULL,
  "LOYALTY" varchar(8) DEFAULT NULL,
  "HANDCHANGE" varchar(8) DEFAULT NULL,
  "LIFECHANGE" varchar(8) DEFAULT NULL,
  PRIMARY KEY ("CARD_NAME")
);
CREATE INDEX "Deck_t_id" ON "Deck" ("T_ID");
CREATE INDEX "Deck_playerIndex" ON "Deck" ("PLAYER_NAME");
CREATE INDEX "Deck_archetypeIndex" ON "Deck" ("DECK_NAME");
CREATE INDEX "Deck_subarchetype" ON "Deck" ("QUALIFIER");
CREATE INDEX "Matches_t_id" ON "Matches" ("T_ID");
CREATE INDEX "Matches_deck_id" ON "Matches" ("DECK_1");
CREATE VIEW `deck1Match` AS
    select
        `Matches`.`MATCH_ID` AS `MATCH_ID`,
        `Matches`.`T_ID` AS `T_ID`,
        `Matches`.`ROUND` AS `ROUND`,
        `Matches`.`TABLE_NUM` AS `TABLE_NUM`,
        `Matches`.`WIN` AS `WIN`,
        `Matches`.`LOSS` AS `LOSS`,
        `Matches`.`DRAW` AS `DRAW`,
        `Deck`.`DECK_ID` AS `DECK_ID`,
        `Deck`.`PLAYER_NAME` AS `PLAYER_NAME`,
        `Deck`.`DECK_NAME` AS `DECK_NAME`,
        `Deck`.`QUALIFIER` AS `QUALIFIER`,
        `Deck`.`PLACE` AS `PLACE`,
        `Deck`.`SPLIT` AS `SPLIT`,
        case when Matches.WIN>Matches.LOSS then 1 else 0 end AS MATCH_WIN,
        case when Matches.WIN<Matches.LOSS then 1 else 0 end AS MATCH_LOSS,
        case when Matches.WIN=Matches.LOSS then 1 else 0 end AS MATCH_DRAW
    from (`Deck` join `Matches`)
    where (`Deck`.`DECK_ID` = `Matches`.`DECK_1`);
CREATE VIEW `deck2Match` AS
    select
        `Matches`.`MATCH_ID` AS `MATCH_ID`,
        `Matches`.`DECK_2` AS `DECK_2`,
        `Deck`.`PLAYER_NAME` AS `PLAYER_2`,
        `Deck`.`DECK_NAME` AS `DECK_NAME_2`,
        `Deck`.`QUALIFIER` AS `QUALIFIER_2`,
        `Deck`.`PLACE` AS `PLACE_2`,
        `Deck`.`SPLIT` AS `SPLIT_2`
    from (`Deck` join `Matches`)
    where (`Deck`.`DECK_ID` = `Matches`.`DECK_2`);
CREATE VIEW `MatchesSCG` AS
    select
        `deck1Match`.`MATCH_ID` AS `MATCH_ID`,
        `deck1Match`.`T_ID` AS `T_ID`,
        `deck1Match`.`ROUND` AS `ROUND`,
        `deck1Match`.`TABLE_NUM` AS `TABLE_NUM`,
        `deck1Match`.`DECK_NAME` AS `DECK_NAME`,
        `deck1Match`.`QUALIFIER` AS `QUALIFIER`,
        `deck2Match`.`DECK_NAME_2` AS `DECK_NAME_2`,
        `deck2Match`.`QUALIFIER_2` AS `QUALIFIER_2`,
        `deck1Match`.`WIN` AS `WIN`,
        `deck1Match`.`LOSS` AS `LOSS`,
        `deck1Match`.`DRAW` AS `DRAW`,
        CASE WHEN deck1Match.WIN > deck1Match.LOSS THEN 1 ELSE 0 end AS MATCH_WIN,
        CASE WHEN deck1Match.WIN < deck1Match.LOSS THEN 1 ELSE 0 end AS MATCH_LOSS,
        CASE WHEN deck1Match.WIN = deck1Match.LOSS THEN 1 ELSE 0 end AS MATCH_DRAW,
        `deck1Match`.`DECK_ID` AS `DECK_ID`,
        `deck2Match`.`DECK_2` AS `DECK_2`,
        `deck1Match`.`PLAYER_NAME` AS `PLAYER_NAME`,
        `deck2Match`.`PLAYER_2` AS `PLAYER_2`,
        `deck1Match`.`PLACE` AS `PLACE`,
        `deck2Match`.`PLACE_2` AS `PLACE_2`,
        `deck1Match`.`SPLIT` AS `SPLIT`,
        `deck2Match`.`SPLIT_2` AS `SPLIT_2`
    from
        ((`deck1Match` join `deck2Match` on((`deck1Match`.`MATCH_ID` = `deck2Match`.`MATCH_ID`)))
        join `Tournament` on((`deck1Match`.`T_ID` = `Tournament`.`T_ID`)));
COMMIT;
