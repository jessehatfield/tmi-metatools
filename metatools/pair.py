def pair(players, matches, alreadyPlayed, i=0):
    """Recursive function. Determines pairings.

       Pre: <players> is a list of players to pair, in preferred order.
            <matches> is an empty list.
            alreadyPlayed is a function (p1, p2) defined for the objects in <players>.
       Post: <matches> is a list of players in paired order.
             matches[0] vs. matches[1]
             matches[1] vs. matches[2], etc.
       Returns: True if all players were successfully paired. False otherwise."""

    success = False #Will be set to true when pairings are completed.
    p1 = players[i] #Pair the next player in the list
    i += 1 #Then move on.

    if p1 in matches: 
        #If this player has already been paired, move to the next one.
        success = pair(players, matches, alreadyPlayed, i)
        return success
    for p2 in players:
        #Iterate through the list of players looking for suitable opponents.
        if p2 in matches:
            #If this one has already been paired, move to the next one.
            continue
        if p2 == p1:
            #If this one is the same object we are attempting to pair, move on.
            continue
        if alreadyPlayed(p1, p2):
            #If the two players have already played, move on.
            continue

        #If we've reached this point, there is no reason the players should not
        #be paired. Add this match to <matches>.
        matches.append(p1)
        matches.append(p2)

        if len(matches) < len(players):
            #If there are more players left, attempt to pair the next player.
            success = pair(players, matches, alreadyPlayed, i)
        else:
            #If all players have been paired, the pairing has succeeded.
            success = True

        if success == False:
            #If we failed to pair the remaining players, remove the pairing we
            #just made and continue through the loop.
            del matches[(len(matches) - 2):]
        else:
            #If we successfully paired all the players, terminate the loop.
            break
    #If success is true, terminate recursion.
    #If success is false, pairing this player is currently impossible.
    #Back up to the previous pairing. If this is the first call to the
    #function, we can't back up any more, so there are no possible pairings.
    return success
