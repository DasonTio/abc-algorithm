# Video notes: required ABC video

Video: https://www.youtube.com/watch?v=SVXmJdLsN0M (watched 7 Nov 2026).
Timestamps and the "Video" parts are my own observations; the wording was tidied with AI help (declared in `ai_use_declaration.md`).

## Note 1 – 6:39 – The three bee groups
**Video:** introduces the three groups that are essential to ABC: employed bees search around their own food source, onlooker bees search more deeply around the good sources, and scout bees search randomly.
**My project:** all three are implemented in `code/bee_colony.py`: the employed phase (SN = 10 searches per cycle), the onlooker phase (10 searches per cycle, chosen by probability) and the scout phase (at most one per cycle). The scout-ablation experiment turns scouts off only to measure their contribution; the recommended method keeps them.

## Note 2 – 7:22 – Scout bees
**Video:** a scout is a bee that abandons its nectar source and searches for a new one. The video does not describe the movement or the rule in detail.
**My project:** a food source is abandoned when its trial counter reaches `limit` = 45 failed attempts; the scout replaces it with a random guess (lat, lon, M) inside the bounds and resets the counter. At most one source is abandoned per cycle (the one with the most failures). The best solution is stored separately, so it is never lost.
**Differences from the slides (abandonment):** the slides count `limit` in cycles; as the assignment requires, my code counts failed improvement *attempts* (employed + onlooker), and a tie counts as a failure. In the experiments scouts were rare (median 1 per run). Without scouts the median result was unchanged, but the worst development run was twice as bad (J 0.093 vs 0.043).

## Note 3 – 10:01 – Food source = solution, nectar = fitness
**Video:** each food source is a solution associated with one employed bee; its nectar (quality) is its fitness value, and the best solution is the one with the greatest fitness.
**My project:** a food source is one guess of the earthquake (latitude, longitude, magnitude M).
**Difference (notation):** I *minimise* a cost J(x), the mismatch between predicted and reported station intensities, and convert it to a selection fitness F(x) = 1/(1 + J(x)). So my best solution is the lowest J, which is the same as the highest F. J and F are kept separate; the slides store the objective in an array called "fitness" and take its minimum.

## Note 4 – 20:13 – Onlooker selection by fitness
**Video:** food sources with higher fitness have a greater chance of being chosen by onlooker bees, so good solutions are explored further.
**My project:** each source's probability is p = F / ΣF, computed once per cycle after the employed phase; 10 onlookers are drawn by roulette wheel. Example from the manual trace: J = (1.160, 1.583, 2.903) gives p = (0.42, 0.35, 0.23).
**Difference (selection):** because I minimise J, the raw cost is never used as the weight (that would favour worse guesses). In the seed-100 run on the 2004 Chūetsu earthquake, onlookers made six moves in a row on the best source and corrected its magnitude from 6.29 to 6.73.
