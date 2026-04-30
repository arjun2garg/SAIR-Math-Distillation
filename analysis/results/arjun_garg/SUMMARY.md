# arjun_garg programmatic checker — summary

## Overall accuracy

| dataset | n | accuracy |
|---|---:|---:|
| normal | 1000 | 987/1000 = 98.7000% |
| hard | 200 | 130/200 = 65.0000% |
| hard1 | 69 | 47/69 = 68.1159% |
| hard2 | 200 | 180/200 = 90.0000% |
| hard3 | 400 | 297/400 = 74.2500% |
| evaluation_normal | 200 | 186/200 = 93.0000% |
| evaluation_hard | 200 | 153/200 = 76.5000% |
| evaluation_extra_hard | 200 | 19/200 = 9.5000% |
| evaluation_order5 | 200 | 179/200 = 89.5000% |
| full_etp | 22033636 | 21646035/22033636 = 98.2409% |

## Per-split rule breakdown

### `normal`  —  accuracy 987/1000 = 98.70%

Confusion: TP=494, FP=7, TN=493, FN=6

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| L1 | FALSE | 146 | 146 | 0 | 100.0% |
| L2 | FALSE | 122 | 122 | 0 | 100.0% |
| L3 | FALSE | 116 | 116 | 0 | 100.0% |
| M1 | FALSE | 42 | 42 | 0 | 100.0% |
| M2 | FALSE | 4 | 4 | 0 | 100.0% |
| M3 | FALSE | 2 | 2 | 0 | 100.0% |
| M4 | FALSE | 5 | 5 | 0 | 100.0% |
| M6 | FALSE | 7 | 7 | 0 | 100.0% |
| M7 | FALSE | 5 | 5 | 0 | 100.0% |
| T4 | TRUE | 243 | 243 | 0 | 100.0% |
| F1 | FALSE | 24 | 24 | 0 | 100.0% |
| B1 | FALSE | 7 | 4 | 3 | 57.1% |
| B2a | TRUE | 220 | 213 | 7 | 96.8% |
| B2b | TRUE | 38 | 38 | 0 | 100.0% |
| B2c | FALSE | 19 | 16 | 3 | 84.2% |

### `hard`  —  accuracy 130/200 = 65.00%

Confusion: TP=67, FP=63, TN=63, FN=7

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| L1 | FALSE | 9 | 9 | 0 | 100.0% |
| L2 | FALSE | 3 | 3 | 0 | 100.0% |
| M1 | FALSE | 3 | 3 | 0 | 100.0% |
| F1 | FALSE | 21 | 18 | 3 | 85.7% |
| B1 | FALSE | 15 | 11 | 4 | 73.3% |
| B2a | TRUE | 104 | 56 | 48 | 53.8% |
| B2b | TRUE | 26 | 11 | 15 | 42.3% |
| B2c | FALSE | 19 | 19 | 0 | 100.0% |

### `hard1`  —  accuracy 47/69 = 68.12%

Confusion: TP=22, FP=20, TN=25, FN=2

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| L1 | FALSE | 4 | 4 | 0 | 100.0% |
| L2 | FALSE | 1 | 1 | 0 | 100.0% |
| M1 | FALSE | 1 | 1 | 0 | 100.0% |
| F1 | FALSE | 7 | 6 | 1 | 85.7% |
| B1 | FALSE | 5 | 4 | 1 | 80.0% |
| B2a | TRUE | 34 | 18 | 16 | 52.9% |
| B2b | TRUE | 8 | 4 | 4 | 50.0% |
| B2c | FALSE | 9 | 9 | 0 | 100.0% |

### `hard2`  —  accuracy 180/200 = 90.00%

Confusion: TP=97, FP=17, TN=83, FN=3

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| M4 | FALSE | 1 | 1 | 0 | 100.0% |
| F1 | FALSE | 39 | 39 | 0 | 100.0% |
| B1 | FALSE | 14 | 11 | 3 | 78.6% |
| B2a | TRUE | 96 | 83 | 13 | 86.5% |
| B2b | TRUE | 18 | 14 | 4 | 77.8% |
| B2c | FALSE | 32 | 32 | 0 | 100.0% |

### `hard3`  —  accuracy 297/400 = 74.25%

Confusion: TP=163, FP=71, TN=134, FN=32

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| M2 | FALSE | 34 | 34 | 0 | 100.0% |
| M3 | FALSE | 42 | 42 | 0 | 100.0% |
| M4 | FALSE | 14 | 14 | 0 | 100.0% |
| M7 | FALSE | 1 | 1 | 0 | 100.0% |
| T4 | TRUE | 1 | 1 | 0 | 100.0% |
| F1 | FALSE | 36 | 26 | 10 | 72.2% |
| B1 | FALSE | 13 | 5 | 8 | 38.5% |
| B2a | TRUE | 203 | 138 | 65 | 68.0% |
| B2b | TRUE | 30 | 24 | 6 | 80.0% |
| B2c | FALSE | 26 | 12 | 14 | 46.2% |

### `evaluation_normal`  —  accuracy 186/200 = 93.00%

Confusion: TP=92, FP=6, TN=94, FN=8

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| L1 | FALSE | 17 | 17 | 0 | 100.0% |
| L2 | FALSE | 8 | 8 | 0 | 100.0% |
| L3 | FALSE | 10 | 10 | 0 | 100.0% |
| M1 | FALSE | 16 | 16 | 0 | 100.0% |
| M2 | FALSE | 2 | 2 | 0 | 100.0% |
| M3 | FALSE | 1 | 1 | 0 | 100.0% |
| M4 | FALSE | 16 | 16 | 0 | 100.0% |
| T4 | TRUE | 13 | 13 | 0 | 100.0% |
| F1 | FALSE | 12 | 5 | 7 | 41.7% |
| B1 | FALSE | 5 | 4 | 1 | 80.0% |
| B2a | TRUE | 79 | 73 | 6 | 92.4% |
| B2b | TRUE | 6 | 6 | 0 | 100.0% |
| B2c | FALSE | 15 | 15 | 0 | 100.0% |

### `evaluation_hard`  —  accuracy 153/200 = 76.50%

Confusion: TP=93, FP=40, TN=60, FN=7

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| L1 | FALSE | 1 | 1 | 0 | 100.0% |
| L2 | FALSE | 7 | 7 | 0 | 100.0% |
| M1 | FALSE | 13 | 13 | 0 | 100.0% |
| M2 | FALSE | 7 | 7 | 0 | 100.0% |
| M3 | FALSE | 14 | 14 | 0 | 100.0% |
| M7 | FALSE | 3 | 3 | 0 | 100.0% |
| T3 | TRUE | 3 | 3 | 0 | 100.0% |
| T4 | TRUE | 11 | 11 | 0 | 100.0% |
| F1 | FALSE | 16 | 11 | 5 | 68.8% |
| B1 | FALSE | 4 | 3 | 1 | 75.0% |
| B2a | TRUE | 116 | 76 | 40 | 65.5% |
| B2b | TRUE | 3 | 3 | 0 | 100.0% |
| B2c | FALSE | 2 | 1 | 1 | 50.0% |

### `evaluation_extra_hard`  —  accuracy 19/200 = 9.50%

Confusion: TP=19, FP=100, TN=0, FN=81

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| F1 | FALSE | 65 | 0 | 65 | 0.0% |
| B2a | TRUE | 112 | 12 | 100 | 10.7% |
| B2b | TRUE | 7 | 7 | 0 | 100.0% |
| B2c | FALSE | 16 | 0 | 16 | 0.0% |

### `evaluation_order5`  —  accuracy 179/200 = 89.50%

Confusion: TP=91, FP=12, TN=88, FN=9

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| L1 | FALSE | 17 | 17 | 0 | 100.0% |
| L2 | FALSE | 23 | 23 | 0 | 100.0% |
| M2 | FALSE | 6 | 6 | 0 | 100.0% |
| M3 | FALSE | 3 | 3 | 0 | 100.0% |
| M6 | FALSE | 3 | 3 | 0 | 100.0% |
| M7 | FALSE | 7 | 7 | 0 | 100.0% |
| T4 | TRUE | 41 | 41 | 0 | 100.0% |
| F1 | FALSE | 11 | 11 | 0 | 100.0% |
| B1 | FALSE | 27 | 18 | 9 | 66.7% |
| B2a | TRUE | 62 | 50 | 12 | 80.6% |

### `full_etp`  —  accuracy 21646035/22033636 = 98.24%

Confusion: TP=8096818, FP=306140, TN=13549217, FN=81461

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| L1 | FALSE | 4224720 | 4224720 | 0 | 100.0% |
| L2 | FALSE | 3300213 | 3300213 | 0 | 100.0% |
| L3 | FALSE | 3226498 | 3226498 | 0 | 100.0% |
| M1 | FALSE | 1120440 | 1120440 | 0 | 100.0% |
| M2 | FALSE | 128320 | 128320 | 0 | 100.0% |
| M3 | FALSE | 127950 | 127950 | 0 | 100.0% |
| M4 | FALSE | 187677 | 187677 | 0 | 100.0% |
| M6 | FALSE | 154105 | 154105 | 0 | 100.0% |
| M7 | FALSE | 150046 | 150046 | 0 | 100.0% |
| D8 | FALSE | 190 | 190 | 0 | 100.0% |
| T1 | TRUE | 4694 | 4694 | 0 | 100.0% |
| T3 | TRUE | 4693 | 4693 | 0 | 100.0% |
| T4 | TRUE | 3824795 | 3824795 | 0 | 100.0% |
| F1 | FALSE | 526729 | 506693 | 20036 | 96.2% |
| B1 | FALSE | 110195 | 83008 | 27187 | 75.3% |
| B2a | TRUE | 3853646 | 3562796 | 290850 | 92.5% |
| B2b | TRUE | 715130 | 699840 | 15290 | 97.9% |
| B2c | FALSE | 373595 | 339357 | 34238 | 90.8% |