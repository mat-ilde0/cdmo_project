include "globals.mzn";

int: n;  % even number of teams
set of int: TEAMS = 1..n;
set of int: WEEKS = 1..n-1;
set of int: SLOTS = 1..n div 2;


% Opponent of team t in week w
array[TEAMS, WEEKS] of var TEAMS: O;
% Period‐slot of team t in week w:
array[TEAMS, WEEKS] of var SLOTS: P;
% Home/Away indicator:
enum HA = { Home, Away };
array[TEAMS, WEEKS] of var HA: H;

%%%%% SCHEDULING CONSTRAINTS %%%%%%
% 1) Pairing symmetry: if t meets u in week w, then u meets t
constraint
  forall(t in TEAMS, w in WEEKS)(
    O[t,w] != t /\         % no self‐match
    O[ O[t,w], w ] = t
  );

% 2) Every team plays with every other team only once
constraint
  forall(t in TEAMS)(
    all_different([ O[t, w] | w in WEEKS ])
  );

% 3) Every team plays at most twice in the same period over the tournament
constraint
  forall(t in TEAMS, s in SLOTS)(
    sum(w in WEEKS)( bool2int(P[t,w] == s) ) <= 2
  );

% 4) Every team plays once a week
constraint
  forall(w in WEEKS)(
    all_different([ O[t, w] | t in TEAMS ])
  );

 
% 5) Exactly two teams must be assigned to each slot 
constraint
  forall(w in WEEKS, s in SLOTS)(
    sum(t in TEAMS)( bool2int(P[t,w] == s) ) = 2
  );

% 6) Ensure that in each match between team t and its opponent u in week w, one team plays at home and the other away.
constraint
  forall(w in WEEKS, t in TEAMS)(
    let { var TEAMS: u = O[t,w] } in
      (H[t,w] = Home /\ H[u,w] = Away)
   \/ (H[t,w] = Away /\ H[u,w] = Home)
  );

%%%%% CHANNELING CONSTRAINTS %%%%%%
% 7) Connect P and O slots
constraint
  forall(w in WEEKS, t in TEAMS, u in TEAMS where t < u)(
    (O[t,w] = u) <-> (P[t,w] = P[u,w])
  );

% 8) Each week is a perfect matching: map “slot” to opponent
constraint
  forall(w in WEEKS)(
    inverse([ O[t,w] | t in TEAMS ], [ O[t,w] | t in TEAMS ])
  );


%%%%% SYMMETRY BREAKING CONSTRAINTS %%%%%%
% 9) Canonical week-1 pairing + home/away
constraint
  forall(i in 1..n div 2) (
    O[i,1] = n+1-i       % i meets (n+1–i)
    /\ O[n+1-i,1] = i   % symmetry for the other side
    /\ H[i,1] = Home    % smaller team at Home
    /\ H[n+1-i,1] = Away
  );

% 10) Impose lexicographic order on Team 1 vs. Team 2’s slot‐sequence
array[WEEKS] of var SLOTS: Seq1 = [ P[1, w] | w in WEEKS ];
array[WEEKS] of var SLOTS: Seq2 = [ P[2, w] | w in WEEKS ];
constraint
  lex_lesseq(Seq1, Seq2);


% 11) Fix team 1 to play in slot 1 in week 1 
constraint
  P[1,1] = 1;

%%%%% OBJECTIVE FUNCTION: BALANCE HOME-AWAY GAMES %%%%%

% Optimize Home-away games
array[TEAMS] of var int: HA_diff;
constraint
  forall(t in TEAMS)(
    HA_diff[t] = sum(w in WEEKS)( bool2int(H[t,w] == Home) )
               - sum(w in WEEKS)( bool2int(H[t,w] == Away) )
  );
 
array[TEAMS] of var 0..n: HA_abs;
constraint
  forall(t in TEAMS)(
    HA_abs[t] = abs(HA_diff[t])
  );

constraint
  sum(t in TEAMS)(HA_abs[t]) < n+1;

var int: Obj = sum(t in TEAMS)(HA_abs[t]);

solve minimize Obj;

%%%%% OUTPUT FORMATTING %%%%%

array[SLOTS, WEEKS] of var TEAMS: HomeTeam;
array[SLOTS, WEEKS] of var TEAMS: AwayTeam;

constraint
  forall(w in WEEKS, s in SLOTS)(
    exists(t in TEAMS)(
      P[t,w] = s /\ H[t,w] = Home /\ HomeTeam[s,w] = t
    )
    /\
    exists(t in TEAMS)(
      P[t,w] = s /\ H[t,w] = Away /\ AwayTeam[s,w] = t
    )
  );
output [
  "{\n",
  "  \"CP\": {\n",
  "    \"sol\": [\n",
  concat([
    "      [" ++
    concat([
      let {
        var int: h = sum([t | t in TEAMS where P[t,w] == s /\ H[t,w] == Home]),
        var int: a = sum([t | t in TEAMS where P[t,w] == s /\ H[t,w] == Away])
      } in
      "[" ++ show(h) ++ "," ++ show(a) ++ "]"
      ++ if w < n-1 then ", " else "" endif
    | w in WEEKS])
    ++ "]" ++ if s < n div 2 then ",\n" else "\n" endif
  | s in SLOTS]),
  "    ],\n",
  "    \"obj\": " ++ show(Obj) ++ "\n",
  "  }\n",
  "}\n"
];





