# reza_jamei.txt programmatic checker — summary

## Overall accuracy

| dataset | n | accuracy |
|---------|--:|---------:|
| normal | 1000 | 973/1000 = 97.30% |
| hard | 200 | 122/200 = 61.00% |
| hard1 | 69 | 45/69 = 65.22% |
| hard2 | 200 | 179/200 = 89.50% |
| hard3 | 400 | 299/400 = 74.75% |
| evaluation_normal | 200 | 188/200 = 94.00% |
| evaluation_hard | 200 | 146/200 = 73.00% |
| evaluation_extra_hard | 200 | 91/200 = 45.50% |
| evaluation_order5 | 200 | 172/200 = 86.00% |
| full_etp | 22033636 | 21350195/22033636 = 96.8982% |

## Per-split rule breakdown

### `normal`  —  accuracy 973/1000 = 97.30%

Confusion: TP=496, FP=23, TN=477, FN=4

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| A3 | TRUE | 243 | 243 | 0 | 100.0% |
| A8 | TRUE | 9 | 9 | 0 | 100.0% |
| W1 | FALSE | 146 | 146 | 0 | 100.0% |
| W2 | FALSE | 122 | 122 | 0 | 100.0% |
| W3 | FALSE | 2 | 2 | 0 | 100.0% |
| W4 | FALSE | 17 | 17 | 0 | 100.0% |
| W6 | FALSE | 51 | 51 | 0 | 100.0% |
| W7 | FALSE | 3 | 3 | 0 | 100.0% |
| W8 | FALSE | 93 | 93 | 0 | 100.0% |
| W9 | FALSE | 4 | 4 | 0 | 100.0% |
| W10 | FALSE | 2 | 2 | 0 | 100.0% |
| B1 | FALSE | 23 | 20 | 3 | 87.0% |
| B2a | TRUE | 232 | 213 | 19 | 91.8% |
| B2b | TRUE | 29 | 29 | 0 | 100.0% |
| B2c | TRUE | 6 | 2 | 4 | 33.3% |
| B2d | FALSE | 18 | 17 | 1 | 94.4% |

### `hard`  —  accuracy 122/200 = 61.00%

Confusion: TP=67, FP=71, TN=55, FN=7

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| W1 | FALSE | 9 | 9 | 0 | 100.0% |
| W2 | FALSE | 3 | 3 | 0 | 100.0% |
| W4 | FALSE | 3 | 3 | 0 | 100.0% |
| B1 | FALSE | 36 | 29 | 7 | 80.6% |
| B2a | TRUE | 104 | 56 | 48 | 53.8% |
| B2b | TRUE | 26 | 11 | 15 | 42.3% |
| B2c | TRUE | 8 | 0 | 8 | 0.0% |
| B2d | FALSE | 11 | 11 | 0 | 100.0% |

### `hard1`  —  accuracy 45/69 = 65.22%

Confusion: TP=22, FP=22, TN=23, FN=2

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| W1 | FALSE | 4 | 4 | 0 | 100.0% |
| W2 | FALSE | 1 | 1 | 0 | 100.0% |
| W4 | FALSE | 1 | 1 | 0 | 100.0% |
| B1 | FALSE | 12 | 10 | 2 | 83.3% |
| B2a | TRUE | 34 | 18 | 16 | 52.9% |
| B2b | TRUE | 8 | 4 | 4 | 50.0% |
| B2c | TRUE | 2 | 0 | 2 | 0.0% |
| B2d | FALSE | 7 | 7 | 0 | 100.0% |

### `hard2`  —  accuracy 179/200 = 89.50%

Confusion: TP=97, FP=18, TN=82, FN=3

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| B1 | FALSE | 53 | 50 | 3 | 94.3% |
| B2a | TRUE | 96 | 83 | 13 | 86.5% |
| B2b | TRUE | 18 | 14 | 4 | 77.8% |
| B2c | TRUE | 1 | 0 | 1 | 0.0% |
| B2d | FALSE | 32 | 32 | 0 | 100.0% |

### `hard3`  —  accuracy 299/400 = 74.75%

Confusion: TP=177, FP=83, TN=122, FN=18

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| A3 | TRUE | 1 | 1 | 0 | 100.0% |
| A5 | TRUE | 1 | 1 | 0 | 100.0% |
| A8 | TRUE | 5 | 4 | 1 | 80.0% |
| W7 | FALSE | 1 | 1 | 0 | 100.0% |
| W9 | FALSE | 33 | 33 | 0 | 100.0% |
| W10 | FALSE | 42 | 42 | 0 | 100.0% |
| B1 | FALSE | 34 | 24 | 10 | 70.6% |
| B2a | TRUE | 217 | 144 | 73 | 66.4% |
| B2b | TRUE | 28 | 22 | 6 | 78.6% |
| B2c | TRUE | 8 | 5 | 3 | 62.5% |
| B2d | FALSE | 30 | 22 | 8 | 73.3% |

### `evaluation_normal`  —  accuracy 188/200 = 94.00%

Confusion: TP=95, FP=7, TN=93, FN=5

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| A3 | TRUE | 13 | 13 | 0 | 100.0% |
| W1 | FALSE | 17 | 17 | 0 | 100.0% |
| W2 | FALSE | 8 | 8 | 0 | 100.0% |
| W3 | FALSE | 4 | 4 | 0 | 100.0% |
| W4 | FALSE | 2 | 2 | 0 | 100.0% |
| W6 | FALSE | 14 | 14 | 0 | 100.0% |
| W7 | FALSE | 2 | 2 | 0 | 100.0% |
| W8 | FALSE | 8 | 8 | 0 | 100.0% |
| W9 | FALSE | 2 | 2 | 0 | 100.0% |
| B1 | FALSE | 11 | 6 | 5 | 54.5% |
| B2a | TRUE | 82 | 76 | 6 | 92.7% |
| B2b | TRUE | 6 | 6 | 0 | 100.0% |
| B2c | TRUE | 1 | 0 | 1 | 0.0% |
| B2d | FALSE | 30 | 30 | 0 | 100.0% |

### `evaluation_hard`  —  accuracy 146/200 = 73.00%

Confusion: TP=96, FP=50, TN=50, FN=4

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| A3 | TRUE | 14 | 14 | 0 | 100.0% |
| A8 | TRUE | 9 | 2 | 7 | 22.2% |
| W1 | FALSE | 1 | 1 | 0 | 100.0% |
| W2 | FALSE | 7 | 7 | 0 | 100.0% |
| W6 | FALSE | 13 | 13 | 0 | 100.0% |
| W7 | FALSE | 1 | 1 | 0 | 100.0% |
| W10 | FALSE | 14 | 14 | 0 | 100.0% |
| B1 | FALSE | 16 | 13 | 3 | 81.2% |
| B2a | TRUE | 119 | 76 | 43 | 63.9% |
| B2b | TRUE | 4 | 4 | 0 | 100.0% |
| B2d | FALSE | 2 | 1 | 1 | 50.0% |

### `evaluation_extra_hard`  —  accuracy 91/200 = 45.50%

Confusion: TP=91, FP=100, TN=0, FN=9

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| A8 | TRUE | 1 | 1 | 0 | 100.0% |
| B1 | FALSE | 7 | 0 | 7 | 0.0% |
| B2a | TRUE | 115 | 15 | 100 | 13.0% |
| B2b | TRUE | 61 | 61 | 0 | 100.0% |
| B2c | TRUE | 14 | 14 | 0 | 100.0% |
| B2d | FALSE | 2 | 0 | 2 | 0.0% |

### `evaluation_order5`  —  accuracy 172/200 = 86.00%

Confusion: TP=91, FP=19, TN=81, FN=9

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| A3 | TRUE | 41 | 41 | 0 | 100.0% |
| W1 | FALSE | 17 | 17 | 0 | 100.0% |
| W2 | FALSE | 23 | 23 | 0 | 100.0% |
| W9 | FALSE | 6 | 6 | 0 | 100.0% |
| W10 | FALSE | 3 | 3 | 0 | 100.0% |
| B1 | FALSE | 41 | 32 | 9 | 78.0% |
| B2a | TRUE | 69 | 50 | 19 | 72.5% |

## Full ETP rule breakdown

### `full_etp`  —  accuracy 21350195/22033636 = 96.90%

Confusion: TP=8121104, FP=626266, TN=13229091, FN=57175

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| A1 | TRUE | 4694 | 4694 | 0 | 100.0% |
| A2 | TRUE | 4693 | 4693 | 0 | 100.0% |
| A3 | TRUE | 3828672 | 3828672 | 0 | 100.0% |
| A4 | TRUE | 1212 | 1212 | 0 | 100.0% |
| A5 | TRUE | 1212 | 1212 | 0 | 100.0% |
| A6 | TRUE | 174 | 174 | 0 | 100.0% |
| A7 | TRUE | 174 | 174 | 0 | 100.0% |
| A8 | TRUE | 138306 | 135546 | 2760 | 98.0% |
| A9a | TRUE | 13 | 13 | 0 | 100.0% |
| W1 | FALSE | 4223563 | 4223563 | 0 | 100.0% |
| W2 | FALSE | 3299056 | 3299056 | 0 | 100.0% |
| W3 | FALSE | 2082 | 2082 | 0 | 100.0% |
| W4 | FALSE | 283268 | 283268 | 0 | 100.0% |
| W5 | FALSE | 2676 | 2676 | 0 | 100.0% |
| W6 | FALSE | 1329342 | 1329342 | 0 | 100.0% |
| W7 | FALSE | 72412 | 72412 | 0 | 100.0% |
| W8 | FALSE | 2769641 | 2769641 | 0 | 100.0% |
| W9 | FALSE | 125329 | 125329 | 0 | 100.0% |
| W10 | FALSE | 125000 | 125000 | 0 | 100.0% |
| B1 | FALSE | 549688 | 518234 | 31454 | 94.3% |
| B2a | TRUE | 4138659 | 3569074 | 569585 | 86.2% |
| B2b | TRUE | 592063 | 569049 | 23014 | 96.1% |
| B2c | TRUE | 37498 | 6591 | 30907 | 17.6% |
| B2d | FALSE | 504209 | 478488 | 25721 | 94.9% |
