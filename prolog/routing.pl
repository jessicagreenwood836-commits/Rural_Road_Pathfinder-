% routing.pl - Path-finding for the rural road network (Req 3, P2).
%
% Sits on top of P1's rules.pl (which consults roads.pl):
%   road/10, row_state/8, current_season/1.
% Python (P3) should now load THIS file instead of rules.pl; routing.pl
% loads rules.pl itself, so every P1 predicate (dump_roads, dump_edges,
% why/3 ...) still works.
%
% Entry point for Python:
%   dump_route(+Source, +Dest, +Goal, +Avoids)
%     Goal   : distance | time | fewest_stops
%     Avoids : list drawn from [unpaved, closed, broken_cisterns, deep_potholes]
%   prints ONE tab-separated line:
%     ok   <algorithm> <km> <mins> <Place1|Place2|...>
%     none <algorithm>                 (no path under these criteria)
%     unknown <place>                  (place not in the network)
%     badgoal <goal>                   (goal not recognised)
%
% Algorithm choice is made by Prolog (select_algorithm/2):
%   distance     -> dijkstra  (shortest distance)
%   time         -> astar     (fastest; hop-based heuristic, see below)
%   fewest_stops -> bfs       (loose constraint: fewest places visited)

:- ensure_loaded(rules).

% --------------------------------------------------------------- the graph

% known_place(?P): P is a village/town that appears in some road fact.
known_place(P) :- road(P, _, _, _, _, _, _, _, _, _), !.
known_place(P) :- road(_, P, _, _, _, _, _, _, _, _), !.

% route_edge(?From, ?To, -Km, -Mins, -Type, -AllConds, -Effective)
% One drivable direction of one road, with P1's rules applied: Mins already
% includes the +5 rule, AllConds includes inferred deep_potholes (> 3 in) and
% Effective is open|closed (admin block, severely damaged, rainy season).
% Unlike connected/4, CLOSED roads are returned too, so that the
% "avoid closed roads" criterion is the user's choice.
route_edge(F, T, Km, Mins, Type, All, Eff) :-
    road(F, T, Km, Base, Type, Stored, In, S, _, Seas),
    row_state(Base, Stored, In, S, Seas, All, Mins, Eff).
route_edge(F, T, Km, Mins, Type, All, Eff) :-
    road(T, F, Km, Base, Type, Stored, In, S, two_way, Seas),
    row_state(Base, Stored, In, S, Seas, All, Mins, Eff).

% --------------------------------------------------- the "avoid" criteria

% allowed(+Avoids, +Type, +AllConds, +Effective): the road passes every filter.
allowed(Avoids, Type, All, Eff) :-
    \+ ( memberchk(unpaved, Avoids),          Type == unpaved ),
    \+ ( memberchk(closed, Avoids),           Eff == closed ),
    \+ ( memberchk(broken_cisterns, Avoids),  memberchk(broken_cisterns, All) ),
    \+ ( memberchk(deep_potholes, Avoids),    memberchk(deep_potholes, All) ).

% step_cost(+CostType, +Km, +Mins, -Cost)
step_cost(distance, Km, _, Km).
step_cost(time, _, Mins, Mins).

% ------------------------------------------------- choosing the algorithm

select_algorithm(distance,     dijkstra).
select_algorithm(time,         astar).
select_algorithm(fewest_stops, bfs).

cost_type(distance, distance).
cost_type(time,     time).

% ---------------------------------------- best-first search (Dijkstra / A*)
% Open list holds f(F, G, Node, ReversedPath, KmSoFar, MinsSoFar), kept sorted
% with msort/2 so the cheapest F comes first. A node is "closed" when it is
% expanded; the goal is accepted when it is popped, which is what makes the
% result optimal. Dijkstra = this search with heuristic 0.

dijkstra(S, G, Crit, Av, Path, Km, Mins) :-
    search(S, G, Crit, Av, none, Path, Km, Mins).

% A*: h(N) = (fewest road hops from N to the goal) * (cheapest single road).
% Every road costs at least the cheapest road, so h never overestimates
% (admissible), and h(N) <= cost(N,M) + h(M) (consistent). Hops are computed
% on the filtered graph, so the heuristic respects the avoid criteria.
astar(S, G, Crit, Av, Path, Km, Mins) :-
    hop_table(G, Av, Table),
    min_edge_cost(Crit, Av, Min),
    search(S, G, Crit, Av, h(Table, Min), Path, Km, Mins).

search(S, G, Crit, Av, H, Path, Km, Mins) :-
    heuristic(H, S, H0),
    expand([f(H0, 0, S, [S], 0, 0)], [], G, Crit, Av, H, Path, Km, Mins).

% expand(+Open, +Closed, +Goal, +Crit, +Avoids, +H, -Path, -Km, -Mins)
expand([f(_, _, Goal, Rev, K, M)|_], _, Goal, _, _, _, Path, K, M) :-
    !,
    reverse(Rev, Path).
expand([f(_, Gc, N, Rev, K, M)|Rest], Closed, Goal, Crit, Av, H, Path, Km, Mins) :-
    (   memberchk(N, Closed)
    ->  expand(Rest, Closed, Goal, Crit, Av, H, Path, Km, Mins)
    ;   findall(f(F1, G1, N2, [N2|Rev], K1, M1),
                (   route_edge(N, N2, Dk, Dm, Ty, All, Eff),
                    allowed(Av, Ty, All, Eff),
                    \+ memberchk(N2, [N|Closed]),
                    step_cost(Crit, Dk, Dm, C),
                    G1 is Gc + C,
                    K1 is K + Dk,
                    M1 is M + Dm,
                    heuristic(H, N2, H1),
                    F1 is G1 + H1
                ),
                Kids),
        append(Rest, Kids, Open0),
        msort(Open0, Open),
        expand(Open, [N|Closed], Goal, Crit, Av, H, Path, Km, Mins)
    ).

heuristic(none, _, 0).
heuristic(h(Table, Min), N, H) :-
    (   memberchk(N-Hops, Table)
    ->  H is Hops * Min
    ;   H = 0                                 % cannot reach goal anyway
    ).

% min_edge_cost(+Crit, +Avoids, -Min): cheapest allowed road (fails if none).
min_edge_cost(Crit, Av, Min) :-
    findall(C,
            (   route_edge(_, _, Dk, Dm, Ty, All, Eff),
                allowed(Av, Ty, All, Eff),
                step_cost(Crit, Dk, Dm, C)
            ),
            Cs),
    Cs \== [],
    min_list(Cs, Min).

% hop_table(+Goal, +Avoids, -Table): Place-Hops pairs, found by a backward
% breadth-first sweep from the goal over the allowed roads.
hop_table(Goal, Av, Table) :-
    hop_levels([Goal], [Goal-0], 0, Av, Table).

hop_levels([], Table, _, _, Table) :- !.
hop_levels(Frontier, Acc, D, Av, Table) :-
    D1 is D + 1,
    findall(P,
            (   member(M, Frontier),
                route_edge(P, M, _, _, Ty, All, Eff),
                allowed(Av, Ty, All, Eff)
            ),
            Ps0),
    sort(Ps0, Ps),
    exclude(seen(Acc), Ps, New),
    findall(P-D1, member(P, New), Pairs),
    append(Acc, Pairs, Acc1),
    hop_levels(New, Acc1, D1, Av, Table).

seen(Acc, P) :- memberchk(P-_, Acc).

% ----------------------------------------------- breadth-first search (BFS)
% Fewest places visited. Queue entries are b(Node, ReversedPath, Km, Mins).

bfs(S, G, Av, Path, Km, Mins) :-
    bfs_loop([b(S, [S], 0, 0)], [S], G, Av, Path, Km, Mins).

bfs_loop([b(Goal, Rev, K, M)|_], _, Goal, _, Path, K, M) :-
    !,
    reverse(Rev, Path).
bfs_loop([b(N, Rev, K, M)|Queue], Seen, Goal, Av, Path, Km, Mins) :-
    findall(b(N2, [N2|Rev], K1, M1),
            (   route_edge(N, N2, Dk, Dm, Ty, All, Eff),
                allowed(Av, Ty, All, Eff),
                K1 is K + Dk,
                M1 is M + Dm
            ),
            Kids0),
    fresh(Kids0, Seen, Kids, Seen1),
    append(Queue, Kids, Queue1),
    bfs_loop(Queue1, Seen1, Goal, Av, Path, Km, Mins).

% fresh(+Kids0, +Seen, -Kids, -Seen1): drop places already queued/visited
% (also removes duplicate kids made by parallel roads).
fresh([], Seen, [], Seen).
fresh([b(N, R, K, M)|T], Seen, Out, Seen2) :-
    (   memberchk(N, Seen)
    ->  fresh(T, Seen, Out, Seen2)
    ;   Out = [b(N, R, K, M)|Out1],
        fresh(T, [N|Seen], Out1, Seen2)
    ).

% ------------------------------------------------------------- dispatcher

run_algorithm(dijkstra, Goal, S, G, Av, Path, Km, Mins) :-
    cost_type(Goal, Crit),
    dijkstra(S, G, Crit, Av, Path, Km, Mins).
run_algorithm(astar, Goal, S, G, Av, Path, Km, Mins) :-
    cost_type(Goal, Crit),
    astar(S, G, Crit, Av, Path, Km, Mins).
run_algorithm(bfs, _, S, G, Av, Path, Km, Mins) :-
    bfs(S, G, Av, Path, Km, Mins).

% find_route(+S, +G, +Goal, +Avoids, ?Algo, -Path, -Km, -Mins)
% Algo is chosen by select_algorithm/2 from the Goal.
find_route(S, G, Goal, Avoids, Algo, Path, Km, Mins) :-
    select_algorithm(Goal, Algo),
    run_algorithm(Algo, Goal, S, G, Avoids, Path, Km, Mins).

% ---------------------------------------------------------- export for Python

dump_route(S, G, Goal, Avoids) :-
    (   \+ select_algorithm(Goal, _)
    ->  format("badgoal\t~w~n", [Goal])
    ;   \+ known_place(S)
    ->  format("unknown\t~w~n", [S])
    ;   \+ known_place(G)
    ->  format("unknown\t~w~n", [G])
    ;   find_route(S, G, Goal, Avoids, Algo, Path, Km, Mins)
    ->  atomic_list_concat(Path, '|', Places),
        format("ok\t~w\t~w\t~w\t~w~n", [Algo, Km, Mins, Places])
    ;   select_algorithm(Goal, Algo),
        format("none\t~w~n", [Algo])
    ).
