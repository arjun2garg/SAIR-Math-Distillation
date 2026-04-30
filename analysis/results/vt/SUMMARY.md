# vt.txt programmatic checker — summary

## Overall accuracy

| dataset | n | accuracy |
|---------|--:|---------:|
| normal | 1000 | 898/1000 = 89.80% |
| hard | 200 | 111/200 = 55.50% |
| hard1 | 69 | 37/69 = 53.62% |
| hard2 | 200 | 100/200 = 50.00% |
| hard3 | 400 | 346/400 = 86.50% |
| evaluation_normal | 200 | 129/200 = 64.50% |
| evaluation_hard | 200 | 167/200 = 83.50% |
| evaluation_extra_hard | 200 | 195/200 = 97.50% |
| evaluation_order5 | 200 | 154/200 = 77.00% |
| full_etp | 22033636 | 19955265/22033636 = 90.5673% |

## Per-split rule breakdown

### `normal`  —  accuracy 898/1000 = 89.80%

Confusion: TP=439, FP=41, TN=459, FN=61

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| X3 | TRUE | 243 | 243 | 0 | 100.0% |
| LP | FALSE | 146 | 146 | 0 | 100.0% |
| RP | FALSE | 122 | 122 | 0 | 100.0% |
| XOR | FALSE | 59 | 59 | 0 | 100.0% |
| A1 | FALSE | 4 | 4 | 0 | 100.0% |
| A2 | FALSE | 5 | 5 | 0 | 100.0% |
| A3 | FALSE | 5 | 5 | 0 | 100.0% |
| A4 | FALSE | 1 | 1 | 0 | 100.0% |
| A5 | FALSE | 12 | 12 | 0 | 100.0% |
| A6 | FALSE | 3 | 3 | 0 | 100.0% |
| A7 | FALSE | 1 | 1 | 0 | 100.0% |
| A8 | FALSE | 1 | 1 | 0 | 100.0% |
| A10 | FALSE | 5 | 5 | 0 | 100.0% |
| C_PROBE | FALSE | 90 | 90 | 0 | 100.0% |
| H1 | FALSE | 18 | 0 | 18 | 0.0% |
| H3 | FALSE | 45 | 3 | 42 | 6.7% |
| H4 | FALSE | 1 | 1 | 0 | 100.0% |
| H5 | FALSE | 2 | 1 | 1 | 50.0% |
| HUB_Eq41 | TRUE | 18 | 10 | 8 | 55.6% |
| DEFAULT_TRUE | TRUE | 219 | 186 | 33 | 84.9% |

### `hard`  —  accuracy 111/200 = 55.50%

Confusion: TP=71, FP=86, TN=40, FN=3

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| LP | FALSE | 9 | 9 | 0 | 100.0% |
| RP | FALSE | 3 | 3 | 0 | 100.0% |
| XOR | FALSE | 3 | 3 | 0 | 100.0% |
| H2 | FALSE | 4 | 4 | 0 | 100.0% |
| H3 | FALSE | 16 | 16 | 0 | 100.0% |
| H5 | FALSE | 5 | 5 | 0 | 100.0% |
| H6 | FALSE | 3 | 0 | 3 | 0.0% |
| HUB_Eq41 | TRUE | 1 | 0 | 1 | 0.0% |
| DEFAULT_TRUE | TRUE | 156 | 71 | 85 | 45.5% |

### `hard1`  —  accuracy 37/69 = 53.62%

Confusion: TP=23, FP=31, TN=14, FN=1

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| LP | FALSE | 4 | 4 | 0 | 100.0% |
| RP | FALSE | 1 | 1 | 0 | 100.0% |
| XOR | FALSE | 1 | 1 | 0 | 100.0% |
| H2 | FALSE | 1 | 1 | 0 | 100.0% |
| H3 | FALSE | 5 | 5 | 0 | 100.0% |
| H5 | FALSE | 2 | 2 | 0 | 100.0% |
| H6 | FALSE | 1 | 0 | 1 | 0.0% |
| HUB_Eq41 | TRUE | 1 | 0 | 1 | 0.0% |
| DEFAULT_TRUE | TRUE | 53 | 23 | 30 | 43.4% |

### `hard2`  —  accuracy 100/200 = 50.00%

Confusion: TP=71, FP=71, TN=29, FN=29

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| A9 | FALSE | 1 | 1 | 0 | 100.0% |
| A10 | FALSE | 4 | 4 | 0 | 100.0% |
| H2 | FALSE | 2 | 2 | 0 | 100.0% |
| H3 | FALSE | 47 | 21 | 26 | 44.7% |
| H5 | FALSE | 2 | 0 | 2 | 0.0% |
| H6 | FALSE | 2 | 1 | 1 | 50.0% |
| HUB_Eq41 | TRUE | 20 | 0 | 20 | 0.0% |
| DEFAULT_TRUE | TRUE | 122 | 71 | 51 | 58.2% |

### `hard3`  —  accuracy 346/400 = 86.50%

Confusion: TP=193, FP=52, TN=153, FN=2

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| X3 | TRUE | 1 | 1 | 0 | 100.0% |
| F2_TRUE | TRUE | 1 | 1 | 0 | 100.0% |
| F3_TRUE | TRUE | 1 | 1 | 0 | 100.0% |
| F3_FALSE | FALSE | 1 | 1 | 0 | 100.0% |
| A1 | FALSE | 42 | 42 | 0 | 100.0% |
| A2 | FALSE | 33 | 33 | 0 | 100.0% |
| A3 | FALSE | 1 | 1 | 0 | 100.0% |
| A4 | FALSE | 1 | 1 | 0 | 100.0% |
| A5 | FALSE | 7 | 7 | 0 | 100.0% |
| A6 | FALSE | 27 | 27 | 0 | 100.0% |
| A8 | FALSE | 6 | 6 | 0 | 100.0% |
| A9 | FALSE | 1 | 1 | 0 | 100.0% |
| A10 | FALSE | 6 | 6 | 0 | 100.0% |
| H1 | FALSE | 2 | 2 | 0 | 100.0% |
| H2 | FALSE | 6 | 6 | 0 | 100.0% |
| H3 | FALSE | 8 | 8 | 0 | 100.0% |
| H4 | FALSE | 5 | 4 | 1 | 80.0% |
| H5 | FALSE | 5 | 4 | 1 | 80.0% |
| H6 | FALSE | 4 | 4 | 0 | 100.0% |
| HUB_Eq41 | TRUE | 14 | 7 | 7 | 50.0% |
| DEFAULT_TRUE | TRUE | 228 | 183 | 45 | 80.3% |

### `evaluation_normal`  —  accuracy 129/200 = 64.50%

Confusion: TP=69, FP=40, TN=60, FN=31

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| X3 | TRUE | 13 | 13 | 0 | 100.0% |
| LP | FALSE | 17 | 17 | 0 | 100.0% |
| RP | FALSE | 8 | 8 | 0 | 100.0% |
| XOR | FALSE | 16 | 16 | 0 | 100.0% |
| A1 | FALSE | 3 | 3 | 0 | 100.0% |
| A2 | FALSE | 2 | 2 | 0 | 100.0% |
| A3 | FALSE | 2 | 2 | 0 | 100.0% |
| C_PROBE | FALSE | 8 | 8 | 0 | 100.0% |
| H1 | FALSE | 3 | 0 | 3 | 0.0% |
| H2 | FALSE | 3 | 0 | 3 | 0.0% |
| H3 | FALSE | 24 | 4 | 20 | 16.7% |
| H4 | FALSE | 5 | 0 | 5 | 0.0% |
| HUB_Eq41 | TRUE | 12 | 0 | 12 | 0.0% |
| DEFAULT_TRUE | TRUE | 84 | 56 | 28 | 66.7% |

### `evaluation_hard`  —  accuracy 167/200 = 83.50%

Confusion: TP=74, FP=7, TN=93, FN=26

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| X3 | TRUE | 14 | 14 | 0 | 100.0% |
| LP | FALSE | 1 | 1 | 0 | 100.0% |
| RP | FALSE | 7 | 7 | 0 | 100.0% |
| XOR | FALSE | 13 | 13 | 0 | 100.0% |
| F3_FALSE | FALSE | 7 | 7 | 0 | 100.0% |
| F4_TRUE | TRUE | 2 | 2 | 0 | 100.0% |
| A1 | FALSE | 14 | 14 | 0 | 100.0% |
| A3 | FALSE | 1 | 1 | 0 | 100.0% |
| A4 | FALSE | 1 | 1 | 0 | 100.0% |
| A5 | FALSE | 6 | 6 | 0 | 100.0% |
| A6 | FALSE | 4 | 4 | 0 | 100.0% |
| A8 | FALSE | 1 | 1 | 0 | 100.0% |
| A10 | FALSE | 1 | 1 | 0 | 100.0% |
| H1 | FALSE | 5 | 0 | 5 | 0.0% |
| H2 | FALSE | 5 | 0 | 5 | 0.0% |
| H3 | FALSE | 52 | 37 | 15 | 71.2% |
| H6 | FALSE | 1 | 0 | 1 | 0.0% |
| HUB_Eq41 | TRUE | 1 | 1 | 0 | 100.0% |
| DEFAULT_TRUE | TRUE | 64 | 57 | 7 | 89.1% |

### `evaluation_extra_hard`  —  accuracy 195/200 = 97.50%

Confusion: TP=95, FP=0, TN=100, FN=5

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| F4_TRUE | TRUE | 1 | 1 | 0 | 100.0% |
| H3 | FALSE | 100 | 100 | 0 | 100.0% |
| H5 | FALSE | 3 | 0 | 3 | 0.0% |
| H6 | FALSE | 2 | 0 | 2 | 0.0% |
| HUB_Eq41 | TRUE | 1 | 1 | 0 | 100.0% |
| DEFAULT_TRUE | TRUE | 93 | 93 | 0 | 100.0% |

### `evaluation_order5`  —  accuracy 154/200 = 77.00%

Confusion: TP=76, FP=22, TN=78, FN=24

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| X3 | TRUE | 41 | 41 | 0 | 100.0% |
| LP | FALSE | 17 | 17 | 0 | 100.0% |
| RP | FALSE | 23 | 23 | 0 | 100.0% |
| A1 | FALSE | 3 | 3 | 0 | 100.0% |
| A2 | FALSE | 6 | 6 | 0 | 100.0% |
| A4 | FALSE | 4 | 4 | 0 | 100.0% |
| A5 | FALSE | 10 | 10 | 0 | 100.0% |
| A6 | FALSE | 1 | 1 | 0 | 100.0% |
| A8 | FALSE | 1 | 1 | 0 | 100.0% |
| A10 | FALSE | 4 | 4 | 0 | 100.0% |
| H1 | FALSE | 9 | 0 | 9 | 0.0% |
| H3 | FALSE | 21 | 8 | 13 | 38.1% |
| H4 | FALSE | 2 | 1 | 1 | 50.0% |
| H6 | FALSE | 1 | 0 | 1 | 0.0% |
| DEFAULT_TRUE | TRUE | 57 | 35 | 22 | 61.4% |

## Full ETP rule breakdown

### `full_etp`  —  accuracy 19955265/22033636 = 90.57%

Confusion: TP=7130810, FP=1030902, TN=12824455, FN=1047469

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| X1 | TRUE | 4694 | 4694 | 0 | 100.0% |
| X2 | TRUE | 4693 | 4693 | 0 | 100.0% |
| X3 | TRUE | 3828672 | 3828672 | 0 | 100.0% |
| LP | FALSE | 4224720 | 4224720 | 0 | 100.0% |
| RP | FALSE | 3300213 | 3300213 | 0 | 100.0% |
| XOR | FALSE | 1458890 | 1458890 | 0 | 100.0% |
| F1_TRUE | TRUE | 1212 | 1212 | 0 | 100.0% |
| F2_TRUE | TRUE | 1212 | 1212 | 0 | 100.0% |
| F3_TRUE | TRUE | 348 | 348 | 0 | 100.0% |
| F3_FALSE | FALSE | 2076 | 2076 | 0 | 100.0% |
| F4_TRUE | TRUE | 348 | 348 | 0 | 100.0% |
| F4_FALSE | FALSE | 2076 | 2076 | 0 | 100.0% |
| A1 | FALSE | 206174 | 206174 | 0 | 100.0% |
| A2 | FALSE | 204090 | 204090 | 0 | 100.0% |
| A3 | FALSE | 81447 | 81447 | 0 | 100.0% |
| A4 | FALSE | 81584 | 81584 | 0 | 100.0% |
| A5 | FALSE | 174680 | 174680 | 0 | 100.0% |
| A6 | FALSE | 107027 | 107027 | 0 | 100.0% |
| A7 | FALSE | 9395 | 9395 | 0 | 100.0% |
| A8 | FALSE | 54133 | 54133 | 0 | 100.0% |
| A9 | FALSE | 2246 | 2246 | 0 | 100.0% |
| A10 | FALSE | 70453 | 70453 | 0 | 100.0% |
| C_PROBE | FALSE | 2621749 | 2621749 | 0 | 100.0% |
| H1 | FALSE | 282336 | 1632 | 280704 | 0.6% |
| H2 | FALSE | 30016 | 20997 | 9019 | 70.0% |
| H3 | FALSE | 891170 | 154039 | 737131 | 17.3% |
| H4 | FALSE | 34858 | 30199 | 4659 | 86.6% |
| H5 | FALSE | 15539 | 7237 | 8302 | 46.6% |
| H6 | FALSE | 17052 | 9398 | 7654 | 55.1% |
| HUB_Eq41 | TRUE | 320144 | 142976 | 177168 | 44.7% |
| HUB_Eq6 | TRUE | 39 | 38 | 1 | 97.4% |
| DEFAULT_TRUE | TRUE | 4000350 | 3146617 | 853733 | 78.7% |
