functions {
    int r_i(int w, int l) {
        int k = w+l;
        int base = 1 + (k*(k+1)/2);
        return base + l;
    }
    int m_i(int i, int j) {
        return ((j-2)*(j-1)/2) + i;
    }
    real p_win_match(int d_i, int d_j, real[] matchups);
    real p_win_match(int d_i, int d_j, real[] matchups) {
        if (d_i < d_j) {
            int index = m_i(d_i, d_j);
            return matchups[index];
        }
        else if (d_i > d_j) {
            return 1-p_win_match(d_j, d_i, matchups);
        }
        else {
            return 0.5;
        }
    }
    /**
     * For each deck and number of rounds 0:max, compute the probability
     * distribution of records given that number rounds, parameterized by the
     * base probability of winning a match against each other deck and the
     * probability of getting paired against each deck.
     */
    real[,] record_distribution(int n_decks, int n_rounds, int max_rounds, real[] matchups, vector[] p_deck) {
        // n_records = sum(1 to n_rounds+1)
        int n_records = ((n_rounds+1) * (n_rounds+2)) / 2;
        real p_record[n_records, n_decks];
        for (deck_i in 1:n_decks) {
            // start: 100% chance of 0-0 record, 0% elsewhere
            p_record[1, deck_i] = 1.0;
            for (i in 2:n_records) {
                p_record[i, deck_i] = 0.0;
            }
            // compute probability of record based on probabilities from previous round
            for (matches in 1:n_rounds) {
                int previous = matches-1;
                for (w in 0:previous) {
                    int l = previous - w;
                    int score = w - l;
                    int prev_index = r_i(w, l);
                    int win_index = r_i(w+1, l);
                    int lose_index = r_i(w, l+1);
                    real p = p_record[prev_index, deck_i];
                    real p_win = 0;
                    for (deck_j in 1:n_decks) {
                        real p_pair = p_deck[score + max_rounds + 1][deck_j];
                        real p_pair_win = p_pair * p_win_match(deck_i, deck_j, matchups);
                        //TODO: p_win+p_lose < 1, i.e. p_play < 1 and depends on record?
                        p_win += p_pair_win;
                    }
                    p_record[win_index, deck_i] = p_record[win_index, deck_i] + p*p_win;
                    p_record[lose_index, deck_i] = p_record[lose_index, deck_i] + p*(1-p_win);
                }
            }
        }
        return p_record;
    }
    /**
     * Sum, over all possible records yielding a particular score, of each
     * prior probability of the record given the total number of matches,
     * assuming that the prior probability of winning a match is 1/2:
     *     sum[w,l s.t. w-l=score]{ BinomPDF(n=w+l, p=1/2, k=w) }
     *     == sum[w,l s.t. w-l=score]{ (w+l choose w)/(2^(w+l)) }
     */
    real prior_total(int score, int n) {
        real total = 0.0;
        for (w in 0:n) {
            int l = w - score;
            if (l >= 0 && w+l <= n) {
                total += exp(binomial_lpmf(w | w+l, 0.5));
            }
        }
        return total;
    }
    /**
     * Probability of getting paired against deck X at a specific score, given
     * deck X's base field percentage and matchup percentage against other
     * decks, as well as the maximum number of rounds.
     * P(deck(opp)|score(player)) = P(deck(opp)) * sum[score(opp)]{
     *      P(score(opp)|deck(opp))
     *      P(score(opp)|score(player))
     *      / P(score(player))
     * }
     * where P(deck(opp)) == P(deck) is parameter p_field,
     *  P(score(opp)|deck(opp)) == sum{P(record|deck(opp)) s.t. record yields score(opp)}
     *  P(score(opp)|score(player)) comes from parameter p_pair_score 
     *  P(score(player)) == sum{P(record) s.t. record yields score(player)}
     *      == sum{BinomPDF(p=1/2, n=w+l, k=w) s.t. (w-l)==score(player)}
     *      == sum{ (w+l choose w)/(2^(w+l)) s.t. (w-l)==score(player)}
     */
    vector p_pairdeck_score(int n_decks, vector p_field, real[] matchups, int max_rounds, int score, vector[] p_field_current, real[,] p_pair_score) {
        vector[n_decks] deck_dist;
        int s_i = score + max_rounds + 1;
        int n_scores = 2*max_rounds + 1;
        int n_records = ((max_rounds+1) * (max_rounds+2)) / 2;
        real distribution[max_rounds+1, n_records, n_decks];
        for (n_rounds in 0:max_rounds) {
            int n = ((n_rounds+1) * (n_rounds+2)) / 2;
            real p_record_deck_round[n, n_decks] = record_distribution(n_decks, n_rounds, max_rounds, matchups, p_field_current);
            for (r_i in 1:n) {
                distribution[n_rounds+1, r_i] = p_record_deck_round[r_i];
            }
            for (r_i in (n+1):n_records) {
                for (deck_i in 1:n_decks) {
                    distribution[n_rounds+1, r_i, deck_i] = 0.0;
                }
            }
        }
        for (deck_i in 1:n_decks) {
            real p = 0.0;
            for (s_j in 1:n_scores) {
                int opp_score = s_j - max_rounds - 1;
                real p_score_deck = 0.0;
                real prior_score = prior_total(opp_score, max_rounds);
                for (opp_win in 0:max_rounds) {
                    int opp_loss = opp_win - opp_score;
                    int opp_rounds = opp_win + opp_loss;
                    if (opp_loss >= 0 && opp_rounds <= max_rounds) {
                        int record_index = r_i(opp_win, opp_loss);
                        p_score_deck += distribution[opp_rounds+1, record_index, deck_i];
                    }
                }
                p += p_pair_score[s_i, s_j] * p_score_deck / prior_score;
            }
            deck_dist[deck_i] = p * p_field[deck_i];
        }
        return deck_dist;
    }
    /**
     * Probability of getting paired against deck X given each possible score,
     * determined by deck X's base field percentage and matchup percentage
     * against other decks, as well as the maximum number of rounds.
     */
    vector[] p_pairdeck_scores(int n_decks, vector p_field, real[] matchups, int max_rounds, real[,] p_pair_score) {
        int max_iterations = 10;
        real epsilon = 0.0000000001;
        int n_scores = 2*max_rounds + 1;
        vector[n_decks] current[n_scores];
        for (i in 1:n_scores) {
            current[i] = p_field;
        }
        for (i in 1:max_iterations) {
            real diff = 0.0;
            vector[n_decks] next[n_scores];
            for (s_i in 1:n_scores) {
                int score = s_i - max_rounds - 1;
                next[s_i] = p_pairdeck_score(n_decks, p_field, matchups, max_rounds, score, current, p_pair_score);
            }
            for (s_i in 1:n_scores) {
                for (d_i in 1:n_decks) {
                    diff += fabs(next[s_i][d_i] - current[s_i][d_i]);
                }
                current[s_i] = next[s_i];
            }
            if (diff <= epsilon) {
                break;
            }
        }
        return current;
    }
    /**
     * Probability of getting paired against deck X given each possible score,
     * determined by deck X's base field percentage and matchup percentage
     * against other decks, as well as the maximum number of rounds, assuming
     * that decks can only get paired against decks with the same score.
     */
    vector[] p_pairdeck_samescore(int ndecks, vector p_field, real[] matchups, int max_rounds) {
        int n_scores = 2*max_rounds + 1;
        real p_pair_score[n_scores,n_scores];
        vector[ndecks] result[n_scores];
        vector[ndecks] normalized[n_scores];
        for (i in 1:n_scores) {
            for (j in 1:n_scores) {
                if (i == j) {
                    p_pair_score[i,j] = 1.0;
                }
                else {
                    p_pair_score[i,j] = 0.0;
                }
            }
        }
        result = p_pairdeck_scores(ndecks, p_field, matchups, max_rounds, p_pair_score);
        for (i in 1:n_scores) {
            normalized[i] = result[i] / sum(result[i]);
        }
        return normalized;
    }
}
data {
    int n_decks;
    int n_rounds;
    int deck[((2*n_rounds)+1), n_decks];
}
parameters {
    simplex[n_decks] pdeck;
    real<lower=0, upper=1> matchups[n_decks*(n_decks-1)/2];
}
transformed parameters {
    vector[n_decks] pdeck_score[(2*n_rounds)+1];
    pdeck_score = p_pairdeck_samescore(n_decks, pdeck, matchups, n_rounds);
}
model {
    real alpha = 11; // Beta(11,11) prior on matchup percentage inferred from old TMI data
    pdeck ~ dirichlet(rep_vector(1.0, n_decks));
    for (i in 1:(n_decks*(n_decks-1)/2)) {
        matchups[i] ~ beta(alpha, alpha);
    }
    for (i in 1:((2*n_rounds)+1)) {
        deck[i] ~ multinomial(pdeck_score[i]);
    }
}
generated quantities {
    real pwin_deck[n_decks];
    for (i in 1:n_decks) {
        pwin_deck[i] = 0.0;
        for (j in 1:n_decks) {
            pwin_deck[i] += pdeck[j] * p_win_match(i, j, matchups);
        }
    }
}
