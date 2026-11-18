:- encoding(utf8).
% roads.pl - Rural road network facts (saved by rules.pl / roads.py).
% road(Source, Dest, Km, BaseMins, Type, Conditions, PotholeInches,
%      Status, Direction, Seasonal).
%   Type       : paved | unpaved
%   Conditions : list of broken_cisterns, deep_potholes, severely_damaged,
%                falling_rocks ([] = none)
%   Status     : open | closed      Direction : two_way | one_way
%   Seasonal   : none | rainy (rainy = blocked in the rainy season)
%   BaseMins excludes the +5 delay; rules.pl adds it.
:- dynamic road/10.
:- dynamic current_season/1.

current_season(dry).

% --- Kingston network ------------------------------------------------------
road('Downtown Kingston', 'Cross Roads', 3, 8, paved, [], 0, open, one_way, none).
road('Cross Roads', 'Half Way Tree', 3, 8, paved, [], 0, open, one_way, none).
road('Half Way Tree', 'Downtown Kingston', 6, 15, paved, [], 0, open, two_way, none).
road('Half Way Tree', 'Constant Spring', 5, 12, paved, [], 0, open, two_way, none).
road('Constant Spring', 'Stony Hill', 6, 15, paved, [deep_potholes], 4, open, two_way, none).
road('Stony Hill', 'Lawrence Tavern', 9, 22, unpaved, [], 0, closed, two_way, none).
road('Half Way Tree', 'Papine', 7, 18, paved, [broken_cisterns], 0, open, two_way, none).
road('Cross Roads', 'Papine', 6, 15, paved, [], 0, open, two_way, none).
road('Papine', 'Gordon Town', 6, 15, paved, [falling_rocks], 0, open, two_way, rainy).
road('Gordon Town', 'Mavis Bank', 10, 30, unpaved, [broken_cisterns, deep_potholes], 5, open, two_way, rainy).
road('Papine', 'Irish Town', 9, 25, paved, [severely_damaged], 0, open, two_way, none).
road('Downtown Kingston', 'Harbour View', 9, 15, paved, [], 0, open, two_way, none).
road('Harbour View', 'Bull Bay', 5, 10, paved, [], 2, open, two_way, none).

% --- Brief's sample rows (A=Highgate, B=Islington, C=Annotto Bay, D=Port Maria)
%   A -> B  5 km 10 min paved   none            open
%   B -> C  3 km 15 min unpaved broken cisterns open
%   C -> D  7 km 12 min paved   deep potholes   closed
road('Highgate', 'Islington', 5, 10, paved, [], 0, open, two_way, none).
road('Islington', 'Annotto Bay', 3, 15, unpaved, [broken_cisterns], 0, open, two_way, none).
road('Annotto Bay', 'Port Maria', 7, 12, paved, [deep_potholes], 0, closed, two_way, none).
road('Port Maria', 'Oracabessa', 4, 8, paved, [broken_cisterns], 0, open, two_way, none).