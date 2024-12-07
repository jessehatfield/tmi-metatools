#!/usr/bin/env python

from metatools.archetypes import ArchetypeParser
from metatools.database import session, getTournaments

import argparse

def update_tournament_archetypes(session, t_id, parser):
    matching_tournaments = getTournaments(tids=[t_id])
    if len(matching_tournaments) == 0:
        raise Exception(f"No tournament found with T_ID={t_id}")
    elif len(matching_tournaments) > 1:
        raise Exception(f"Multiple tournaments found with T_ID={t_id}")
    tourney = matching_tournaments[0]
    n_skipped = 0
    n_updated = 0
    n_unchanged = 0
    for deck in tourney.decks:
        deck.loadContents()
        if not deck.maindeck or deck.count() < 50:
            n_skipped += 1
            continue
        main, sub = parser.classify(deck)
        updated = False
        if main is not None and deck.archetype != main:
            print(f"Updating {deck}: archetype {deck.archetype} -> {main}")
            deck.archetype = main
            updated = True
        if sub is not None and deck.subarchetype != sub:
            print(f"Updating {deck}: subarchetype {deck.subarchetype} -> {sub}")
            deck.subarchetype = sub
            updated = True
        if updated:
            n_updated += 1
        else:
            n_unchanged += 1
    n_total = n_skipped + n_updated + n_unchanged
    print(f"Processed {n_total} decks: {n_updated} updated, {n_unchanged} unchanged, {n_skipped} skipped.")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Re-run archetype classification on one or more "
            "existing tournament(s), assuming decklists are in the database.")
    p.add_argument("archetype_dir", help="Path to a directory containing archetype definitions.")
    p.add_argument("-D", "--dry_run", action="store_true",
            help="Perform a dry run: process the data, but don't commit any changes to the database")
    p.add_argument("t_ids", type=int, nargs="+", help="One or more database IDs pointing to tournaments to process.")
    args = p.parse_args()

    archetype_parser = ArchetypeParser(args.archetype_dir)
    for t_id in args.t_ids:
        update_tournament_archetypes(session, t_id, archetype_parser)
    if args.dry_run:
        print('(Not committing; dry run.)')
    else:
        session.commit()
