functions {
// Helper functions for computing individual probabilities
    /**
     * Probability of having a certain record given a total number of matches
     * played and no other information:
     *      P(w,l|n=w+l) = BinomPDF(p=1/2, n=(w+l), k=w)
     */
    real p_record_given_nmatches(int w, int l) {
        int n = w + l;
        return exp(binomial_lpmf(w | n, 0.5));
    }
    /**
     * Prior probability of playing a certain number of matches, given a
     * maximum number of matches played. Assumed uniform over [0,n].
     */
    real p_nmatches(int n, int max) {
        return 1.0 / (max + 1.0);
    }
    /**
     * Prior probability of having a certain record.
     */
    real record_prior(int w, int l, int max) {
        return p_record_given_nmatches(w, l) * p_nmatches(w + l, max);
    }
    /**
     * Extract a given matchup percentage from the matchup parameter vector,
     * i.e., P(win | deck(player)==deck[i], deck(opponent)==deck[j])
     */
    real p_win_match(int d_i, int d_j, real[] matchups);
    real p_win_match(int d_i, int d_j, real[] matchups) {
        if (d_i < d_j) {
            int index = ((d_j-2)*(d_j-1)/2) + d_i;
            return matchups[index];
        }
        else if (d_i > d_j) {
            return 1-p_win_match(d_j, d_i, matchups);
        }
        else {
            return 0.5;
        }
    }
// Helper functions for computing parameter indices
    /**
     * Convert a (win, loss) record into the equivalent numeric index.
     */
    int r_index(int w, int l) {
        int k = w+l;
        int base = 1 + (k*(k+1)/2);
        return base + l;
    }
// Functions for constructing intermediate vectors and matrices
    /**
     * Construct a vector containing the prior probability of each record.
     */
    vector record_prior_vector(int max_rounds) {
        int n_records = ((max_rounds+1) * (max_rounds+2)) / 2;
        vector[n_records] vec;
        for (w in 0:max_rounds) {
            for (l in 0:(max_rounds-w)) {
                int r_i = r_index(w, l);
                vec[r_i] = record_prior(w, l, max_rounds);
            }
        }
        return vec;
    }
    /**
     * Construct a matrix whose entries are all 0.
     */
    matrix zero_matrix(int rows, int columns) {
        matrix[rows, columns] Z;
        for (j in 1:columns) {
            for (i in 1:rows) {
                Z[i, j] = 0;
            }
        }
        return Z;
    }
    /**
     * Construct a matchup matrix M given a vector of sufficient free
     * parameters. Input vector should contain matchup percentages:
     *
     *   [ m(1, 2), m(1, 3), m(1, 4), ... m(1, n),
     *     m(2, 3), m(2, 4), ... m(2, n),
     *     m(3, 4), ... m(3, n),
     *     ...
     *     m(n-2, n-1), m(n-2, n),
     *     m(n-1, n) ]
     *
     * where m(i, j) is the probability of winning a match, given that the
     * player is playing deck i and the opponent is playing deck j. The
     * resulting matrix is an n x n matrix M, such that:
     *   M[i,j] = m(i,j) = (1-M[j,i]) for i<j
     *   M[i,i] = 1/2
     *   M = (1-M')
     */
    matrix matchup_matrix(real[] matchup_vector, int n) {
        matrix[n,n] matchup_matrix;
        for (j in 1:n) {
            int base = (j-2)*(j-1)/2;
            for (i in 1:(j-1)) {
                matchup_matrix[i, j] = matchup_vector[base + i];
            }
            matchup_matrix[j, j] = 0.5;
        }
        for (j in 1:n) {
            for (i in (j+1):n) {
                matchup_matrix[i, j] = 1 - matchup_matrix[j, i];
            }
        }
        return matchup_matrix;
    }
    /**
     * Construct U[n_records, n_scores]: the prior distribution of records given
     *      a score. u(i,j) is the probability of having record i, given that
     *      the player has some record whose corresponding score is score j.
     */
    matrix record_score_matrix(int max_rounds) {
        int n_scores = 2*max_rounds + 1;
        int n_records = ((max_rounds+1) * (max_rounds+2)) / 2;
        matrix[n_records, n_scores] U_nonorm = zero_matrix(n_records, n_scores);
        matrix[n_records, n_scores] U;
        for (w_i in 0:max_rounds) {
            for (l_i in 0:(max_rounds-w_i)) {
                int score = w_i - l_i;
                int r_i = r_index(w_i, l_i);
                int s_j = score + max_rounds + 1;
                // U[i,j] = P(r(i) | s(j))
                //      = P(r(i)) * P(s(j) | r(i)) / P(s(j))
                //      = P(r(i)) * 1 / P(s(j))
                //      = P(r(i)) / sum{r=>s(j)}(P(r))
                U_nonorm[r_i, s_j] = record_prior(w_i, l_i, max_rounds);
            }
        }
        // Normalize columns of U
        for (j in 1:n_scores) {
            real total = sum(col(U_nonorm, j));
            for (i in 1:n_records) {
                U[i, j] = U_nonorm[i, j] / total;
            }
        }
        return U;
    }
    /**
     * Construct B[n_scores, n_records]: the prior distribution of scores given
     *      a record, i.e. b(i,j) is 1 when record j implies score i and zero
     *      elsewhere.
     */
    matrix score_record_matrix(int max_rounds) {
        int n_scores = 2*max_rounds + 1;
        int n_records = ((max_rounds+1) * (max_rounds+2)) / 2;
        matrix[n_scores, n_records] B = zero_matrix(n_scores, n_records);
        for (w_j in 0:max_rounds) {
            for (l_j in 0:(max_rounds-w_j)) {
                int score = w_j - l_j;
                int s_i = score + max_rounds + 1;
                int r_j = r_index(w_j, l_j);
                B[s_i, r_j] = 1.0;
            }
        }
        return B;
    }
    /**
     * Construct a score pairing matrix S under the assumption that players are
     * always paired against individuals with the same score.
     */
    matrix score_matrix_same(int max_rounds) {
        int n_scores = 2*max_rounds + 1;
        matrix[n_scores, n_scores] S = zero_matrix(n_scores, n_scores);
        for (i in 1:n_scores) {
            S[i,i] = 1.0;
        }
        return S;
    }
    /**
     * Construct a score pairing matrix S under the assumption that players are
     * paired against individuals within a certain delta of the same score,
     * according to the prior distribution of scores within that range.
     */
    matrix score_matrix_k(int max_rounds, int delta) {
        int n_scores = 2*max_rounds + 1;
        matrix[n_scores, n_scores] S = zero_matrix(n_scores, n_scores);
        vector[n_scores] score_prior = score_record_matrix(max_rounds) * record_prior_vector(max_rounds);
        for (i in 1:n_scores) {
            // S[s'] = P(opp.score=s' | pl.score=i, delta)
            //       = P(s') / sum[d=-delta...delta]{P(i+d)} if s' in range
            real total = 0.0;
            for (j in (i-delta):(i+delta)) {
                if (j > 0 && j <= n_scores) {
                    total += score_prior[j];
                }
            }
            for (j in (i-delta):(i+delta)) {
                if (j > 0 && j <= n_scores) {
                    S[j, i] = score_prior[j] / total;
                }
            }
        }
        return S;
    }
    /**
     * Get the probability of finding an opponent in the relevant time window
     * whose score is within a certain delta of yours.
     */
    matrix find_opponent_matrix(int max_rounds, real wait_time) {
        int n_scores = 2*max_rounds + 1;
        matrix[n_scores, n_scores] p_find = zero_matrix(n_scores, n_scores);
        vector[n_scores] score_prior = score_record_matrix(max_rounds) * record_prior_vector(max_rounds);
        for (delta in 0:(n_scores-1)) {
            for (i in 1:n_scores) {
                real p = 0.0;
                for (j in (i-delta):(i+delta)) {
                    if (j > 0 && j <= n_scores) {
                        p += score_prior[j];
                    }
                }
                p_find[i, delta+1] = 1 - exp(-p / wait_time);
            }
        }
        return p_find;
    }
    /**
     * Construct a score pairing matrix S under the assumption that players can
     * be scored any distance away if necessary.
     */
    matrix score_matrix_full(int max_rounds, real wait_time) {
        int n_scores = 2*max_rounds + 1;
        matrix[n_scores, n_scores] p_success = find_opponent_matrix(max_rounds, wait_time);
        matrix[n_scores, n_scores] S = zero_matrix(n_scores, n_scores);
        for (delta in 0:(n_scores-1)) {
            matrix[n_scores, n_scores] p_oppscore = score_matrix_k(max_rounds, delta);
            vector[n_scores] p_find;
            for (i in 1:n_scores) {
                real p_unpaired = 1.0 - sum(col(S, i));
                p_find[i] = p_unpaired * p_success[i, delta+1];
            }
            S += diag_post_multiply(p_oppscore, p_find);
        }
        for (j in 1:n_scores) {
            real total = sum(col(S, j));
            if (total != 1 && total != 0) {
                for (i in 1:n_scores) {
                    S[i,j] = S[i,j] / total;
                }
            }
        }
        return S;
    }
    /**
     * Construct a score pairing matrix S under the assumption that players are
     * always paired against individuals with score up to one away in either
     * direction.
     *
     * An opponent with the exact same score is selected if they come along
     * within an acceptable amount of time, which is modeled as a Poisson
     * process, whose rate is the average number of players with the appropriate
     * score to arrive within the allowed time period, which is in turn the base
     * rate for players to arrive times the probability that a player has the
     * appropriate record. Or alternately, define the scale of the distribution
     * as the expected wait time relative to the max wait time:
     *
     *      P(find opp. | pl.score=s, tolerance=0)
     *          = 1-PoissonPMF(k=0, rate(s+-0))
     *          = 1-PoissonPMF(k=0, base_rate * P(score=s))
     *          = ExponentialCDF(x=1, rate = base_rate * P(score=s))
     *          = 1-exp(-base_rate * P(score=s))
     *          = ExponentialCDF(x=1, scale = 1/(base_rate * P(score=s)))
     *          = ExponentialCDF(x=1, scale = wait_time / P(score=s))
     *          = ExponentialCDF(x=1, rate = P(score=s) / wait_time)
     *          = 1-exp(-P(score=s) / wait_time)
     *      P(opp.score=s' | pl.score=s, tolerance=0, find opp.) = (s'==s)
     *
     * If this doesn't happen, select the first opponent with score within +- 1:
     *
     *      P(opp.score=s' | pl.score=s, tolerance=1, find opp.)
     *          = P(score=s') / (P(score=s-1) + P(score=s) + P(score=s+1))
     *              when s' in {s-1, s, s+1}; 0 otherwise
     *              (and P(score=s')=0 when s' < min_score or s' > max_score)
     *
     * Let S0: P(opp.score=s' | pl.score=s, tolerance=0, find opp.) = I
     *     S1: P(opp.score=s' | pl.score=s, tolerance=0, find opp.)
     *     p0: P(find opp. | pl.score=s, tolerance=0)
     *
     * Then:
     *
     *      S = (S0 * diag(p0)) + (S1 * diag(1-p0))
     *        = (S0 * diag(p0)) + (S1 * (I-diag(p0)))
     *        = (S0 * diag(p0)) + (S1 * I)  - (S1 * diag(p0))
     *        = ((S0-S1) * diag(p0)) + S1
     */
    matrix score_matrix_one(int max_rounds, real wait_time) {
        int n_scores = 2*max_rounds + 1;
        matrix[n_scores, n_scores] S0 = zero_matrix(n_scores, n_scores);
        matrix[n_scores, n_scores] S1 = zero_matrix(n_scores, n_scores);
        vector[n_scores] score_prior = score_record_matrix(max_rounds) * record_prior_vector(max_rounds);
        vector[n_scores] p0;
        for (i in 1:n_scores) {
            // S1[s'] = P(opp.score=s' | pl.score=i, tol=1, found)
            //        = P(s')/(P(i-1) + P(i) + P(i+1)) for s' in (i-1, i, i+1)
            if (n_scores == 1) {
                S1[i, i] = 1.0;
            }
            else if (i == 1) {
                real total = score_prior[i] + score_prior[i+1];
                S1[i,i] = score_prior[i] / total;
                S1[i+1,i] = score_prior[i+1] / total;
            }
            else if (i == n_scores) {
                real total = score_prior[i-1] + score_prior[i];
                S1[i-1,i] = score_prior[i-1] / total;
                S1[i,i] = score_prior[i] / total;
            }
            else {
                real total = score_prior[i-1] + score_prior[i] + score_prior[i+1];
                S1[i-1,i] = score_prior[i-1] / total;
                S1[i,i] = score_prior[i] / total;
                S1[i+1,i] = score_prior[i+1] / total;
            }
            // S0 = I
            S0[i,i] = 1.0;
            // p0[i] = 1-PoissonPMF(k=0, P(score[i])/wait_time)
            if (wait_time > 0) {
                p0[i] = 1 - exp(-score_prior[i] / wait_time);
            }
            else {
                p0[i] = 1.0;
            }
        }
        return diag_post_multiply(S0 - S1, p0) + S1;
    }
    /**
     * Construct F, representing the probability that a deck with a given record
     * is playing a given deck.
     *
     * Model as a series of matrix multiplications:
     *
     *      Q = U * S * B * diagonal_matrix(PR)
     *      F = ((F .* (M * F * Q)) * T_win) + ((F .* (M' * F * Q)) * T_lose)
     *
     * where:
     *
     * F[n_decks, n_records] is the distribution of decks that actually have
     *      each possible record. Each column should sum to 1. f(i,j) is the
     *      probability that someone is playing deck i, given that they have
     *      record j.
     * M[n_decks, n_decks] is the matchup matrix, built from model parameters:
     *      m(i,j) in [0, 1] is the probability of deck i winning a match given
     *      that its opponent is playing deck j.
     * M' is the transpose of M.
     * T_win[n_records, n_records] is a transition matrix associated with a
     *      match win. t_win(i,j) is the probability, given a current record i
     *      and a match win, that the next record will be record j. One
     *      wherever a win at record i leads to record j, zero otherwise.
     *      Records with the maximum number of rounds all transition to the
     *      starting record 0-0.
     * T_lose[n_records, n_records] is a transition matrix associated with a
     *      match loss. t_lose(i,j) is the probability, given a current record i
     *      and a match loss, that the next record will be record j. One
     *      wherever a loss at record i leads to record j, zero otherwise.
     *      Records with the maximum number of rounds all transition to the
     *      starting record 0-0.
     * Q[n_records, n_records] is the probability, given a match between two
     *      players, that the two players will have the exact combination of
     *      records. q(i,j) == q(j,i) == P(player record && opp. record).
     *      Sum of all entries should equal 1.
     * U[n_records, n_scores] is the prior distribution of records given a
     *      score. u(i,j) is the probability of having record i, given that the
     *      player has some record whose corresponding score is score j.
     * S[n_scores, n_scores] is the opponent's score distribution given the
     *      player's score. s(i,j) is the probability of getting paired against
     *      someone with score i, given that you have score j.
     * B[n_scores, n_records] is the prior distribution of scores given a
     *      record. Since each record results in a unique score (w-l),
     *      b(i,j) = 1 where record j corresponds to score i, and 0 elsewhere.
     * PR[n_records] is a vector representing the prior probability of having
     *      each record. diagonal_matrix(PR) is a matrix whose diagonal entries
     *      are the entries of PR and other entries are 0.
     *
     * "*" is ordinary matrix multiplication, ".*" is the Hadamard product.
     *
     * Matrices T_win, T_lose, U, and B can be derived from the number of
     * rounds, as can vector PR.
     *
     * Q and M' can be computed from the parameters and other matrices.
     *
     * F is defined recursively: it is initialized based on the field
     * distribution parameter, and computed iteratively.
     *
     * Parameters are the matchup matrix M, score matrix S, and the
     * field distribution, which is used to initialize F.
     */
    matrix deck_record_matrix(int n_decks, int max_rounds, vector p_field, matrix M, matrix S) {
        int max_iterations = 100;
        real epsilon = 0.0000000001;
        int n_scores = 2*max_rounds + 1;
        int n_records = ((max_rounds+1) * (max_rounds+2)) / 2;
        matrix[n_decks, n_records] F; // P(playing deck | record)
        matrix[n_records, n_records] T_win = zero_matrix(n_records, n_records);
        matrix[n_records, n_records] T_lose = zero_matrix(n_records, n_records);
        matrix[n_records, n_scores] U = record_score_matrix(max_rounds);
        matrix[n_scores, n_records] B = score_record_matrix(max_rounds);
        vector[n_records] PR = record_prior_vector(max_rounds);
        matrix[n_records, n_records] Q = diag_post_multiply(U * S * B, PR);
        // Initialize F = P(deck | record) by field distribution
        for (j in 1:n_records) {
            for (i in 1:n_decks) {
                F[i, j] = p_field[i];
            }
        }
        // Fill in transition matrices T_win and T_lose
        for (w_j in 0:max_rounds) {
            for (l_j in 0:(max_rounds-w_j)) {
                int r_j = r_index(w_j, l_j);
                int n_j = w_j + l_j;
                // Fill in record transition matrices
                for (w_i in 0:max_rounds) {
                    for (l_i in 0:(max_rounds-w_i)) {
                        // T(W)[i,j] = 1 if r[i]+win => r[j]
                        int r_i = r_index(w_i, l_i);
                        int n_i = w_i + l_i;
                        if (n_i == max_rounds && n_j == 0) {
                            // Transition back to 0-0 regardless of result
                            T_win[r_i, r_j] = 1.0;
                            T_lose[r_i, r_j] = 1.0;
                        }
                        else if ((l_i == l_j) && (w_j == w_i + 1)) {
                            T_win[r_i, r_j] = 1.0;
                        }
                        else if ((l_j == l_i + 1) && (w_i == w_j)) {
                            T_lose[r_i, r_j] = 1.0;
                        }
                    }
                }
            }
        }
        // Iterate until convergence
        for (i in 1:max_iterations) {
            matrix[n_decks, n_records] F_next;
            matrix[n_decks, n_records] F_norm;
            real diff = 0;
            // Let:
            //
            //      U = P(record | score)
            //      S = P(opp.score | pl.score)
            //      B = P(score | record)
            //      Q = P(prev.opp.record && pl.prev.record) == P(r',r)
            //        = U * S * B * diag(P(record))
            // Then:
            //
            //      F * Q == P(prev.opp.deck && pl.prev.record)
            //            == sum[r']{ P(d'|r') * P(r',r) }
            //            == sum[r']{ P(d'|r') * P(r') * P(r|r') }
            //            == sum[r']{ P(d',r') * P(r|r') }
            //            == sum[r']{ P(d',r') * P(r|r',d') }
            //            == sum[r']{ P(d',r',r) }
            //            == P(d',r)
            //            == P(prev.opp.deck && pl.prev.record)
            //      M * F * Q == sum[d']{ P(win|d,d')*P(d',r) }
            //                == sum[d']{ P(win|d,d',r)*P(d',r) }
            //                == sum[d']{ P(win,d,d',r)*P(d',r)/P(d,d',r) }
            //                == sum[d']{ P(win,d,d',r)*P(d',r)/(P(d|d',r)*P(d',r)) }
            //                == sum[d']{ P(win,d,d',r)/P(d|d',r) }
            //                == sum[d']{ P(win,d,d',r)/P(d|r) }
            //                == sum[d']{ P(win,d,d',r) } / P(d|r)
            //                == P(win,d,r) / P(d|r)
            //                == P(pl.deck && pl.prev.record && won(prev)) / P(p.deck | pl.prev.record)
            //      F .* (M * F * Q) == P(win,d,r)
            //                       == P(pl.deck && pl.prev.record && won(prev))
            //      (F .* (M * F * Q)) * T_win == sum[r]{ P(win,d,r) * P(curr|r,win) }
            //                                 == sum[r]{ P(win,d,r,curr) }
            //                                 == P(win,d,curr)
            //                                 == P(pl.deck, pl.curr.record, won last round)
            //      (F .* (M' * F * Q)) * T_lose == P(pl.deck, pl.curr.record, lost last round)
            //
            // Therefore:
            //
            //      F == column_normalize[ ((F .* (M * F * Q)) * T_win) + ((F .* (M' * F * Q)) * T_lose) ]
            //        == normalize_by_record[ P(pl.curr.deck && pl.curr.record) ]
            //        == P(deck | record)
            //
            matrix[n_decks, n_records] A = F * Q;
            F_next = ((F .* (M * A)) * T_win) + ((F .* (M' * A)) * T_lose);
            // Normalize by record
            for (j in 1:n_records) {
                real total = sum(col(F_next, j));
                for (k in 1:n_decks) {
                    if (total > 0) {
                        F_norm[k, j] = F_next[k, j] / total;
                    }
                }
            }
            // Test for convergence
            diff = sum(fabs(F_norm - F));
            // Update F
            F = F_norm;
            if (diff <= epsilon) {
                break;
            }
        }
        return F;
    }
// Compute distribution parameters from model parameters
    /**
     * Construct P, representing the probability of getting paired against deck
     * deck X given each possible record, determined by deck X's base field
     * percentage and matchup percentage against other decks, as well as the
     * maximum number of rounds. Follows from F according to the model:
     *
     *      P = F * U * S
     *
     * where:
     *
     *      F corresponds to P(deck | record)
     *      U corresponds to P(record | score)
     *      S corresponds to P(opponent's score | player's score)
     *
     * therefore P corresponds to P(opponent's deck | player's score) .
     *
     * The resulting probabilities define the distribution parameters, so this
     * function converts P back to a parameter vector before returning.
     */
    vector[] p_pairdeck_scores(int n_decks, int max_rounds, matrix F, matrix S) {
        int n_scores = 2*max_rounds + 1;
        int n_records = ((max_rounds+1) * (max_rounds+2)) / 2;
        matrix[n_records, n_scores] U = record_score_matrix(max_rounds);
        matrix[n_decks, n_scores] P = F * U * S;
        vector[n_decks] param_vectors[n_scores];
        for (j in 1:n_scores) {
            param_vectors[j] = col(P, j);
        }
        return param_vectors;
    }
}
data {
    int n_archetypes;
    int n_rounds;
    int pairings[((2*n_rounds)+1), n_archetypes];
    int paired_scores[((2*n_rounds)+1), ((2*n_rounds)+1)];
    int decks[(((n_rounds+1)*(n_rounds+2))/2), n_archetypes];
}
parameters {
    simplex[n_archetypes] pdeck;
    real<lower=0, upper=1> matchups[n_archetypes*(n_archetypes-1)/2];
    real<lower=0> wait_time;
}
transformed parameters {
    vector[n_archetypes] pdeck_score[(2*n_rounds)+1];
//    matrix[((2*n_rounds)+1), ((2*n_rounds)+1)] pscore_score_matrix = score_matrix_one(n_rounds, wait_time);
    matrix[((2*n_rounds)+1), ((2*n_rounds)+1)] pscore_score_matrix = score_matrix_full(n_rounds, wait_time);
    matrix[n_archetypes, (((n_rounds+1)*(n_rounds+2))/2)] pdeck_record_matrix = deck_record_matrix(
        n_archetypes, n_rounds, pdeck, matchup_matrix(matchups, n_archetypes), pscore_score_matrix);
    pdeck_score = p_pairdeck_scores(n_archetypes, n_rounds, pdeck_record_matrix, pscore_score_matrix);
}
model {
    real alpha = 11; // Beta(11,11) prior on matchup percentage inferred from old TMI data
    pdeck ~ dirichlet(rep_vector(1.0, n_archetypes));
    for (i in 1:(n_archetypes*(n_archetypes-1)/2)) {
        matchups[i] ~ beta(alpha, alpha);
    }
    for (i in 1:((2*n_rounds)+1)) {
        pairings[i] ~ multinomial(pdeck_score[i]);
        paired_scores[i] ~ multinomial(col(pscore_score_matrix, i));
    }
    for (i in 1:(((n_rounds+1)*(n_rounds+2))/2)) {
        decks[i] ~ multinomial(col(pdeck_record_matrix, i));
    }
    wait_time ~ exponential(2);
}
generated quantities {
    real pwin_deck[n_archetypes];
    for (i in 1:n_archetypes) {
        pwin_deck[i] = 0.0;
        for (j in 1:n_archetypes) {
            pwin_deck[i] += pdeck[j] * p_win_match(i, j, matchups);
        }
    }
}
