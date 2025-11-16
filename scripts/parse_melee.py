#!/usr/bin/env python

import argparse
import csv
import json
import re
import requests
import sys

import bs4


def fetch_html(url, allow_redirects=True):
    """Fetch using GET and return a BeautifulSoup object representing the HTML content."""
    headers = {
        'User-Agent': 'curl/7.61.1',
        'cache-control': 'no-cache',
        'Accept': '*/*'
    }
    response = requests.get(url, headers=headers, allow_redirects=allow_redirects)
    return bs4.BeautifulSoup(response.text, 'html.parser')

def fetch_json(url, payload):
    """Fetch using POST, passing the payload as the body, and return a JSON object."""
    headers = {
        'User-Agent': 'curl/7.61.1'
    }
    response = requests.post(url, headers=headers, data=payload, allow_redirects=False)
    json_data = response.json()
    return json_data

def get_round_info(tournament_id, allow_incomplete=False):
    rounds = []
    soup = fetch_html(f"https://melee.gg/Tournament/View/{tournament_id}")
    standings = soup.find('div', id='standings')
    buttons = standings.find_all('button')
    i = 1
    for button in buttons:
        round_props = {
            'id': int(button.get('data-id')),
            'name': button.get('data-name'),
            'complete': button.get('data-is-completed', 'false').lower() == 'true'
        }
        match = re.compile('^round ([\d]+)$').match(round_props['name'].strip().lower())
        if match:
            round_props['index'] = int(match.group(1))
        elif round_props['name'].strip().lower() == 'quarterfinals':
            round_props['index'] = -1
        elif round_props['name'].strip().lower() == 'semifinals':
            round_props['index'] = -2
        elif round_props['name'].strip().lower() == 'finals':
            round_props['index'] = -3
        else:
            raise Exception(f"Doesn't know how to handle round name {round_props['name']}")
        for k in round_props:
            if round_props[k] is None:
                raise Exception(f"Round property {k} not found in: {button}" )
        if not round_props['complete']:
            if allow_incomplete:
                print(f'Skipping incomplete round: {round_props}', file=sys.stderr)
                continue
            else:
                raise Exception(f"Round {round_props['name']} ({round_props['id']}) not complete")
        rounds.append(round_props)
    last_round = max(props['index'] for props in rounds)
    for i in range(len(rounds)):
        if rounds[i]['index'] < 0:
            rounds[i]['index'] = last_round - rounds[i]['index']
    rounds.sort(key=lambda p: p['index'])
    return rounds

def fetch_standings(round_id, page_size=25):
    payload = {
        'roundId': round_id,
        'columns[0][data]': 'Rank',
        'columns[0][name]': 'Rank',
        'order[0][dir]': 'asc',
        'order[0][column]': '0',
        "length": str(page_size)
    }
    player_data = []
    page = 0
    total_players = 0
    while page == 0 or page * page_size < total_players:
        payload['start'] = str(page * page_size)
        content = fetch_json("https://melee.gg/Standing/GetRoundStandings", payload)
        total_players = content['recordsTotal']
        if total_players == 0:
            return None
        player_data.extend(content['data'])
        page += 1
    return player_data

def fetch_round_results(round_id, page_size=25):
    page = 0
    payload = {
        "columns[0][data]": "TableNumber",
        "columns[0][name]": "TableNumber",
        "order[0][column]": "0",
        "order[0][dir]": "asc",
        "length": str(page_size)
    }
    records = []
    page = 0
    total_records = 0
    while page == 0 or page * page_size < total_records:
        payload['start'] = str(page * page_size)
        content = fetch_json(f"https://melee.gg/Match/GetRoundMatches/{round_id}", payload)
        total_records = content['recordsTotal']
        records.extend(content['data'])
        page += 1
    return records

def fetch_decklist(deck_id):
    """Fetches decklist and returns it in the form of a string:
    '4 Card Name 3\r\nCard Name 2\r\n...4 Card Name N\r\n\r\nSideboard\r\n3 Sideboard Card 1\r\n...\r\n3 Sideboard Card M'
    """
    decklist_url = f"https://melee.gg/Decklist/View/{deck_id}"
    soup = fetch_html(decklist_url)
    copy_button = soup.find('button', class_='decklist-builder-copy-button')
    if copy_button is not None:
        decklist = copy_button['data-clipboard-text']
        return re.sub('^Deck\r?\n', '', decklist)
    decklist_container = soup.find('div', class_='decklist-container')
    if decklist_container is not None:
        maindeck = []
        sideboard = []
        for category in decklist_container.find_all('div', class_='decklist-category'):
            title = category.find('div', class_='decklist-category-title')
            entries = category.find_all('div', class_='decklist-record')
            is_sideboard = title is not None and title.text is not None and \
                    (title.text.strip().startswith('Sideboard' ) or title.text.strip().startswith('Companion' ))
            for entry in entries:
                quantity = entry.find('span', class_='decklist-record-quantity')
                card_name = entry.find('a', class_='decklist-record-name')
                if quantity is None or card_name is None or quantity.text is None or card_name.text is None:
                    print(f"WARNING: can't parse decklist entry: {entry}")
                    continue
                entry_string = quantity.text.strip() + ' ' + card_name.text.strip()
                if is_sideboard:
                    sideboard.append(entry_string)
                else:
                    maindeck.append(entry_string)
        if len(maindeck) > 0:
            all_entries = maindeck + ['', 'Sideboard'] + sideboard + ['']
            return '\r\n'.join(all_entries)
    print(f"WARNING: Unable to find decklist in {decklist_url}", file=sys.stderr)
    return None

def fetch_player_data(rounds, allow_incomplete=True, forward=False):
    player_data = []
    for i in range(len(rounds)):
        index = i if forward else len(rounds)-1-i
        player_data = fetch_standings(rounds[index]['id'])
        if player_data is not None and len(player_data) > 0:
            break
    return player_data

def fetch_tournament(tournament_id, player_output=None, match_output=None, allow_incomplete=False,
        decklists=None):
    data = {}
    players = []
    rounds = get_round_info(tournament_id, allow_incomplete)
    player_data = fetch_player_data(rounds, allow_incomplete=allow_incomplete)
    for entry in player_data:
        player_record = {
                'place': entry['Rank'],
                'archetype': 'Unknown',
                'player': entry['Team']['Players'][0]['DisplayName'],
                'id': entry['Team']['Players'][0]['ID']
        }
        if len(entry['Decklists']) > 0:
            player_record['archetype'] = entry['Decklists'][0]['DecklistName']
            if decklists:
                deck_id = entry['Decklists'][0]['DecklistId']
                player_record['decklist'] = fetch_decklist(deck_id)
                if player_record['decklist'] is None:
                    print(f"WARNING: couldn't fetch decklist: {player_record}", file=sys.stderr)
        players.append(player_record)
    distinct_names = set()
    for i in range(len(players)):
        if players[i]['player'] in distinct_names:
            j = 2
            while f'{players[i]["player"]}{j}' in distinct_names:
                j += 1
            players[i]["player"] = f'{players[i]["player"]}{j}'
        distinct_names.add(players[i]["player"])
    if decklists is not None:
        with open(decklists, 'a') as file:
            json.dump(players, file, indent=4, ensure_ascii=False)
    player_names = {metadata['id']: metadata['player'] for metadata in players}
    player_records = {metadata['id']: {} for metadata in players}
    opponents = {metadata['player']: {} for metadata in players}
    for round_metadata in rounds:
        round_index = round_metadata['index']
        round_data = fetch_round_results(round_metadata['id'])
        for entry in round_data:
            game_counts = {}
            competitors = entry['Competitors']
            if len(competitors) == 1:
                p1 = competitors[0]['Team']['Players'][0]['ID']
                if p1 in player_records:
                    player_records[p1][round_index] = ['', f"Bye"]
                else:
                    name = competitors[0]['Team']['Players'][0]['DisplayName']
                    print(f'WARNING: round {round_index}: player {p1} "{name}" not found in {len(player_records)} records', file=sys.stderr)
            elif len(competitors) == 2:
                p1 = competitors[0]['Team']['Players'][0]['ID']
                p2 = competitors[1]['Team']['Players'][0]['ID']
                w1 = int(competitors[0]['GameWinsAndGameByes'])
                l1 = int(competitors[1]['GameWinsAndGameByes'])
                if p1 in player_names and p2 in player_names:
                    player_records[p1][round_index] = [player_names.get(p2, ''), f"{w1}-{l1}"]
                    player_records[p2][round_index] = [player_names.get(p1, ''), f"{l1}-{w1}"]
                else:
                    if p1 not in player_records:
                        p1name = competitors[0]['Team']['Players'][0]['DisplayName']
                        print(f'WARNING: round {round_index}: player {p1} "{p1name}" not found in {len(player_names)} standings', file=sys.stderr)
                    if p2 not in player_names:
                        p2name = competitors[1]['Team']['Players'][0]['DisplayName']
                        print(f'WARNING: round {round_index}: player {p2} "{p2name}" not found in {len(player_names)} standings', file=sys.stderr)
            else:
                raise Exception(f"Doesn't know how to handle other than two 'Competitors': {competitors}")
    rows = []
    for player in players:
        player_name = player['player']
        player_id = player['id']
        row = [player_name, player['archetype']]
        for i in range(len(rounds)):
            pass
        for round_metadata in rounds:
            round_index = round_metadata['index']
            if round_index in player_records[player_id]:
                row.extend(player_records[player_id][round_index])
            else:
                row.extend(['', ''])
        rows.append(row)
    header = ['Player', 'Archetype']
    for round_metadata in rounds:
        header.append(f'Round {round_metadata["index"]}')
        header.append('')
    return rows, header

if __name__ == "__main__":
    p = argparse.ArgumentParser("Download an MTGMelee tournament.")
    p.add_argument("tournament_id", type=int, help="Tournament ID in melee.gg")
    p.add_argument("-d", "--delimiter", default='\t', help="Field delimiter for output")
    p.add_argument("-i", "--incomplete", action="store_true", help="Proceed even if some rounds are marked as incomplete")
    p.add_argument("-l", "--lists", help="Write decklists to a JSON file with this path")
    p.add_argument("-p", "--players", action="store_true", help="Just fetch player data and exit")
    args = p.parse_args()
    if args.players:
        rounds = get_round_info(args.tournament_id, allow_incomplete=True)
        player_data = fetch_player_data(rounds, forward=True)
        print(json.dumps(player_data))
        sys.exit(0)
    rows, header = fetch_tournament(args.tournament_id, allow_incomplete=args.incomplete,
            decklists=args.lists)
    writer = csv.writer(sys.stdout, delimiter=args.delimiter)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
