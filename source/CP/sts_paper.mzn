% nao corre p n= 12 nem n=10; corre n=8 em 581ms
include "globals.mzn";

int: n;  % even number of teams
set of int: TEAMS = 1..n;
set of int: WEEKS = 1..n-1;
set of int: SLOTS = 1..n div 2;

/***
  VARIABLES
***/

% Opponent of team t in week w (0-based for bye, but STS has n even so no bye):
array[TEAMS, WEEKS] of var TEAMS: O;
% Period‐slot of team t in week w:
array[TEAMS, WEEKS] of var SLOTS: P;
% Home/Away indicator:
enum HA = { Home, Away };
array[TEAMS, WEEKS] of var HA: H;

/***
  BASIC “round‐robin” CONSTRAINTS
***/

% 1) Pairing symmetry: if t meets u in week w, then u meets t.
constraint
  forall(t in TEAMS, w in WEEKS)(
    O[t,w] != t /\         % no self‐match
    O[ O[t,w], w ] = t
  );

% 2) Each team meets each other exactly once:
constraint
  forall(t in TEAMS)(
    all_different([ O[t, w] | w in WEEKS ])
  );

% in each week, all teams are diff
constraint
  forall(w in WEEKS)(
    all_different([ O[t, w] | t in TEAMS ])
  );

% 3) Each week is a perfect matching: map “slot” to opponent
constraint
  forall(w in WEEKS)(
    inverse([ O[t,w] | t in TEAMS ], [ O[t,w] | t in TEAMS ]) %/\ % for each week, O[O[i]]=i
%      all_different([ P[t,w] | t in TEAMS ]) /\
%      forall(t in TEAMS)(
%       P[t,w] = P[ O[t,w], w ] /\   % two opponents share the same slot index
%       (H[t,w] = Home /\ H[ O[t,w], w ] = Away)  % ensure home/away roles
%     )
  );
 
% connect P and O : opposing teams play in the same slot

% constraint 
%   forall(w in WEEKS) (
%     forall(t in TEAMS)(
%      % se jogam uma contra a outra, jogam no mesmo slot
%      P[t,w] = P[O[t,w],w] 
%     )
%   );

% Connect P and O slots
constraint
  forall(w in WEEKS, t in TEAMS, u in TEAMS where t < u)(
    (O[t,w] = u) <-> (P[t,w] = P[u,w])
  );

/***
  “AT MOST 2 TIMES IN THE SAME SLOT” FOR EACH TEAM
***/

% (Option A) Count approach:
constraint
  forall(t in TEAMS, s in SLOTS)(
    sum(w in WEEKS)( bool2int(P[t,w] == s) ) <= 2
  );

% (Option B) Table approach: 
%   Precompute AllowedSlots = all (n−1)‐length vectors over SLOTS in which no value appears >2 times.
%   Then:
%   forall(t in TEAMS)(
%     table([ P[t,w] | w in WEEKS ], AllowedSlots)
%   );

/***
  (OPTIONAL) “BALANCE HOME/AWAY” OBJECTIVE
***/

% If you want to force “fair split of H vs. A for each team”:
% constraint
%   forall(t in TEAMS)(
%     sum(w in WEEKS)( bool2int(H[t,w] == H) )  >= floor((n-1)/2) /\
%     sum(w in WEEKS)( bool2int(H[t,w] == H) )  <= ceil((n-1)/2)
%   );

/***
  SYMMETRY‐BREAKING (“Align with Carlsson et al.”— Section 6.5)
***/

% (a) Fix team 1’s week-1 opponent+venue:
constraint
  O[1, 1] = 2 /\ H[1,1] = Home;   % Team 1 plays Team 2 at home in week 1

% (b) Impose lexicographic order on Team 1 vs. Team 2’s slot‐sequence 
%     (breaks “swap 1↔2” symmetry):
array[WEEKS] of var SLOTS: Seq1 = [ P[1, w] | w in WEEKS ];
array[WEEKS] of var SLOTS: Seq2 = [ P[2, w] | w in WEEKS ];
constraint
  lex_lesseq(Seq1, Seq2);


% (c) If “slot labels” are interchangeable, fix slot of (1,1)=1:
constraint
  P[1,1] = 1;
  
% — in each week w and slot s, exactly 2 teams must occupy that slot:
constraint
  forall(w in WEEKS, s in SLOTS)(
    sum(t in TEAMS)( bool2int(P[t,w] == s) ) = 2
  );

% — for each match {t, O[t,w]} in week w, one Home and one Away
constraint
  forall(w in WEEKS, t in TEAMS)(
    let { var TEAMS: u = O[t,w] } in
      (H[t,w] = Home /\ H[u,w] = Away)
   \/ (H[t,w] = Away /\ H[u,w] = Home)
  );


/***
  (OPTIONAL) IMPROVED “COST TABLE” FOR stronger inference
***/

% % If you want to minimize “imbalance”:
% var 0..n: MaxImb;
% array[TEAMS] of var int: HA_diff;
% constraint
%   forall(t in TEAMS)(
%     HA_diff[t] = sum(w in WEEKS)( bool2int(H[t,w] == H) )
%                - sum(w in WEEKS)( bool2int(H[t,w] == A) )
%   );
% constraint
%   MaxImb = max([ abs(HA_diff[t]) | t in TEAMS ]);
% solve minimize MaxImb;

/*
  Alternatively, precompute for each possible “||H[t,*] vector||” the 
  resulting imbalance, store it as a table, and replace the sums above 
  by a single “table” constraint that maps (H[t,1..n-1])→HA_diff[t].  
  This is exactly how Carlsson et al derive eqn. (26–27) to strengthen 
  back‐propagation from the cost function :contentReference[oaicite:10]{index=10}.
*/
solve satisfy;

% –– print week×slot matrix of [home,away] without helper functions
% output [
%   % before each new slot‐line (except the first), newline:
%   if s > 1 then "\n" else "" endif
%   ++
%   % for this slot s, list one “[h,a]” per week w:
%   concat([
%     "[" 
%      ++ show(
%           sum(t in TEAMS)(
%             t * bool2int(P[t,w] == s /\ H[t,w] == Home)
%           )
%         )
%      ++ ","
%      ++ show(
%           sum(t in TEAMS)(
%             t * bool2int(P[t,w] == s /\ H[t,w] == Away)
%           )
%         )
%     ++ "]"
%     ++ if w < n-1 then " " else "" endif
%     | w in WEEKS
%   ])
% | s in SLOTS
% ];