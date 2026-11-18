% rules.pl - Rural road network inference rules (the rule-based "AI").
% All reasoning about roads lives here; roads.py only collects input and
% writes facts. This file loads the facts from roads.pl:
%   road(Source, Dest, Km, BaseMins, Type, Conditions, PotholeInches,
%        Status, Direction, Seasonal).
%   current_season(dry | rainy).
:- consult(roads).

% --- Hazard inference (spec: "potholes ... beyond 3 inches") ---------------

% A measured depth over 3 inches is inferred to be deep_potholes.
pothole_condition(Inches, deep_potholes) :- Inches > 3.

% all_conditions(+Stored, +Inches, -All): stored conditions plus inferred ones.
all_conditions(Stored, Inches, [C|Stored]) :-
    pothole_condition(Inches, C), \+ memberchk(C, Stored), !.
all_conditions(Stored, _, Stored).

% --- Auto +5 minute rule (spec: broken cisterns or deep potholes) ----------
% BaseMins is stored without the delay; the +5 is derived on every read, so
% repeated updates can never add it twice.

delay_condition(broken_cisterns).
delay_condition(deep_potholes).

% travel_time(+BaseMins, +Conditions, -Mins): +5 once if any delay condition.
travel_time(Base, Conds, Mins) :-
    member(C, Conds), delay_condition(C), !,
    Mins is Base + 5.
travel_time(Base, _, Base).

% --- Dynamic status (spec: blocked, severely damaged, seasonally blocked) --

% closure_reason(+Status, +Conditions, +Seasonal, -Reason)
closure_reason(closed, _, _, 'closed by admin (blocked)').
closure_reason(_, Conds, _, 'severely damaged: unsafe, auto-closed') :-
    memberchk(severely_damaged, Conds).
closure_reason(_, _, rainy, 'seasonal road: closed in rainy season') :-
    current_season(rainy).

% effective_status(+Status, +Conditions, +Seasonal, -Effective)
% closed if any closure reason applies, otherwise open.
effective_status(S, Conds, Seas, Eff) :-
    (   closure_reason(S, Conds, Seas, _) -> Eff = closed ; Eff = open ).

% Falling rocks: road stays open but the driver is warned.
warning(Conds, 'risk of falling rocks: drive with caution') :-
    memberchk(falling_rocks, Conds).

% --- One stored road after all rules --------------------------------------

% row_state(+Base, +Stored, +Inches, +Status, +Seasonal, -All, -Mins, -Effective)
% Works on one row's own values, so duplicate facts for a pair never mix.
row_state(Base, Stored, Inches, S, Seas, All, Mins, Eff) :-
    all_conditions(Stored, Inches, All),
    travel_time(Base, All, Mins),
    effective_status(S, All, Seas, Eff).

% --- Bidirectional rule (spec: two-way unless one-way) ---------------------
% connected(?From, ?To, -Km, -Mins): an open road you can drive From -> To.
% This is the interface the routing rules (Coley) should use.

% Every open road can be driven Source -> Dest.
connected(F, T, Km, Mins) :-
    road(F, T, Km, Base, _, Stored, In, S, _, Seas),
    row_state(Base, Stored, In, S, Seas, _, Mins, open).
% An open two_way road can also be driven Dest -> Source (no reverse fact).
connected(F, T, Km, Mins) :-
    road(T, F, Km, Base, _, Stored, In, S, two_way, Seas),
    row_state(Base, Stored, In, S, Seas, _, Mins, open).

% --- Explanation: why a road has its current time and status --------------

% reason(+Stored, +Inches, +Status, +Seasonal, -Text): one per matching rule.
reason(Stored, Inches, _, _, R) :-                   % inferred pothole
    pothole_condition(Inches, C), \+ memberchk(C, Stored),
    format(atom(R), 'inferred ~w from ~w in depth', [C, Inches]).
reason(Stored, Inches, _, _, R) :-                   % +5 delay (once)
    all_conditions(Stored, Inches, All),
    findall(C, (member(C, All), delay_condition(C)), Cs0),
    list_to_set(Cs0, Cs), Cs \== [],
    atomic_list_concat(Cs, ', ', Text),
    format(atom(R), '+5 min: ~w', [Text]).
reason(Stored, Inches, S, Seas, R) :-                % closure
    all_conditions(Stored, Inches, All),
    closure_reason(S, All, Seas, R).
reason(Stored, Inches, _, _, R) :-                   % warning
    all_conditions(Stored, Inches, All),
    warning(All, R).

% why(+F, +T, -Reasons): every reason for one road ([] if none).
why(F, T, Reasons) :-
    road(F, T, _, _, _, Stored, Inches, S, _, Seas),
    findall(R, reason(Stored, Inches, S, Seas, R), Reasons).

% --- Export for Python (tab-separated) -------------------------------------

% dump_roads: season on line 1, then one line per road (stored + derived).
dump_roads :-
    current_season(Season), format("~w~n", [Season]),
    forall(road(F, T, Km, Base, Ty, Conds, In, St, Dir, Seas),
       (   row_state(Base, Conds, In, St, Seas, _, Mins, Now),
           findall(R, reason(Conds, In, St, Seas, R), Rs),
           atomic_list_concat(Rs, '; ', Why),
           atomic_list_concat(Conds, ',', C),
           atomic_list_concat([F, T, Km, Base, Ty, C, In, St, Dir, Seas, Mins, Now, Why],
                              '\t', Line),
           format("~w~n", [Line])
       )).

% dump_edges: every open connection, one per line.
dump_edges :-
    forall(connected(F, T, Km, Mins), format("~w\t~w\t~w\t~w~n", [F, T, Km, Mins])).
