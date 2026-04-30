# yan-biao.txt programmatic checker — summary

## Overall accuracy

| dataset | n | accuracy |
|---------|--:|---------:|
| normal | 1000 | 969/1000 = 96.90% |
| hard | 200 | 144/200 = 72.00% |
| hard1 | 69 | 50/69 = 72.46% |
| hard2 | 200 | 166/200 = 83.00% |
| hard3 | 400 | 284/400 = 71.00% |
| evaluation_normal | 200 | 165/200 = 82.50% |
| evaluation_hard | 200 | 168/200 = 84.00% |
| evaluation_extra_hard | 200 | 109/200 = 54.50% |
| evaluation_order5 | 200 | 177/200 = 88.50% |
| full_etp | 22033636 | 21392345/22033636 = 97.0895% |

## Per-split rule breakdown

### `normal`  —  accuracy 969/1000 = 96.90%

Confusion: TP=470, FP=1, TN=499, FN=30

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| S0a | TRUE | 243 | 243 | 0 | 100.0% |
| F0 | FALSE | 172 | 172 | 0 | 100.0% |
| FP1_TRUE | TRUE | 1 | 1 | 0 | 100.0% |
| FP2_TRUE | TRUE | 1 | 1 | 0 | 100.0% |
| FP2_FALSE | FALSE | 1 | 1 | 0 | 100.0% |
| L | FALSE | 114 | 114 | 0 | 100.0% |
| R | FALSE | 97 | 97 | 0 | 100.0% |
| X | FALSE | 42 | 42 | 0 | 100.0% |
| D_SPINE_R | FALSE | 1 | 1 | 0 | 100.0% |
| CASE_A_3VARS_TRUE | TRUE | 181 | 181 | 0 | 100.0% |
| CASE_A_LE2VARS_FALSE | FALSE | 12 | 12 | 0 | 100.0% |
| B1 | TRUE | 34 | 34 | 0 | 100.0% |
| B2 | TRUE | 6 | 5 | 1 | 83.3% |
| B_SUB | TRUE | 1 | 1 | 0 | 100.0% |
| B3_LOOSE | TRUE | 2 | 2 | 0 | 100.0% |
| B_RPROJ_NARROW | TRUE | 2 | 2 | 0 | 100.0% |
| DEFAULT_FALSE | FALSE | 90 | 60 | 30 | 66.7% |

### `hard`  —  accuracy 144/200 = 72.00%

Confusion: TP=22, FP=4, TN=122, FN=52

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| FP1_TRUE | TRUE | 7 | 7 | 0 | 100.0% |
| FP2_TRUE | TRUE | 3 | 3 | 0 | 100.0% |
| L | FALSE | 9 | 9 | 0 | 100.0% |
| R | FALSE | 3 | 3 | 0 | 100.0% |
| X | FALSE | 3 | 3 | 0 | 100.0% |
| CASE_A_LE2VARS_FALSE | FALSE | 9 | 9 | 0 | 100.0% |
| B1 | TRUE | 3 | 3 | 0 | 100.0% |
| B2 | TRUE | 4 | 4 | 0 | 100.0% |
| B3_LOOSE | TRUE | 4 | 0 | 4 | 0.0% |
| B_RPROJ_NARROW | TRUE | 5 | 5 | 0 | 100.0% |
| DEFAULT_FALSE | FALSE | 150 | 98 | 52 | 65.3% |

### `hard1`  —  accuracy 50/69 = 72.46%

Confusion: TP=7, FP=2, TN=43, FN=17

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| FP1_TRUE | TRUE | 2 | 2 | 0 | 100.0% |
| FP2_TRUE | TRUE | 1 | 1 | 0 | 100.0% |
| L | FALSE | 4 | 4 | 0 | 100.0% |
| R | FALSE | 1 | 1 | 0 | 100.0% |
| X | FALSE | 1 | 1 | 0 | 100.0% |
| CASE_A_LE2VARS_FALSE | FALSE | 3 | 3 | 0 | 100.0% |
| B1 | TRUE | 1 | 1 | 0 | 100.0% |
| B2 | TRUE | 1 | 1 | 0 | 100.0% |
| B3_LOOSE | TRUE | 2 | 0 | 2 | 0.0% |
| B_RPROJ_NARROW | TRUE | 2 | 2 | 0 | 100.0% |
| DEFAULT_FALSE | FALSE | 51 | 34 | 17 | 66.7% |

### `hard2`  —  accuracy 166/200 = 83.00%

Confusion: TP=68, FP=2, TN=98, FN=32

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| CASE_A_3VARS_TRUE | TRUE | 61 | 61 | 0 | 100.0% |
| CASE_A_LE2VARS_FALSE | FALSE | 20 | 20 | 0 | 100.0% |
| B2 | TRUE | 3 | 3 | 0 | 100.0% |
| B3_LOOSE | TRUE | 5 | 3 | 2 | 60.0% |
| B_RPROJ_NARROW | TRUE | 1 | 1 | 0 | 100.0% |
| DEFAULT_FALSE | FALSE | 110 | 78 | 32 | 70.9% |

### `hard3`  —  accuracy 284/400 = 71.00%

Confusion: TP=88, FP=9, TN=196, FN=107

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| S0a | TRUE | 1 | 1 | 0 | 100.0% |
| FP1_TRUE | TRUE | 1 | 1 | 0 | 100.0% |
| FP2_TRUE | TRUE | 6 | 6 | 0 | 100.0% |
| FP3_TRUE | TRUE | 1 | 1 | 0 | 100.0% |
| D_SPINE_L | FALSE | 5 | 5 | 0 | 100.0% |
| D_SPINE_R | FALSE | 5 | 5 | 0 | 100.0% |
| B1 | TRUE | 21 | 21 | 0 | 100.0% |
| B2 | TRUE | 25 | 24 | 1 | 96.0% |
| B_SUB | TRUE | 1 | 1 | 0 | 100.0% |
| B3_SAME | TRUE | 1 | 1 | 0 | 100.0% |
| B3_LOOSE | TRUE | 27 | 23 | 4 | 85.2% |
| B_RPROJ_NARROW | TRUE | 13 | 9 | 4 | 69.2% |
| DEFAULT_FALSE | FALSE | 293 | 186 | 107 | 63.5% |

### `evaluation_normal`  —  accuracy 165/200 = 82.50%

Confusion: TP=69, FP=4, TN=96, FN=31

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| S0a | TRUE | 13 | 13 | 0 | 100.0% |
| F0 | FALSE | 8 | 8 | 0 | 100.0% |
| FP1_TRUE | TRUE | 1 | 1 | 0 | 100.0% |
| L | FALSE | 17 | 17 | 0 | 100.0% |
| R | FALSE | 8 | 8 | 0 | 100.0% |
| K | FALSE | 2 | 2 | 0 | 100.0% |
| X | FALSE | 16 | 16 | 0 | 100.0% |
| CASE_A_3VARS_TRUE | TRUE | 43 | 43 | 0 | 100.0% |
| CASE_A_LE2VARS_FALSE | FALSE | 3 | 1 | 2 | 33.3% |
| B1 | TRUE | 1 | 1 | 0 | 100.0% |
| B2 | TRUE | 3 | 2 | 1 | 66.7% |
| B_SUB | TRUE | 3 | 3 | 0 | 100.0% |
| B3_LOOSE | TRUE | 8 | 5 | 3 | 62.5% |
| B_RPROJ_NARROW | TRUE | 1 | 1 | 0 | 100.0% |
| DEFAULT_FALSE | FALSE | 73 | 44 | 29 | 60.3% |

### `evaluation_hard`  —  accuracy 168/200 = 84.00%

Confusion: TP=68, FP=0, TN=100, FN=32

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| S0a | TRUE | 14 | 14 | 0 | 100.0% |
| L | FALSE | 1 | 1 | 0 | 100.0% |
| R | FALSE | 7 | 7 | 0 | 100.0% |
| X | FALSE | 13 | 13 | 0 | 100.0% |
| CASE_A_3VARS_TRUE | TRUE | 42 | 42 | 0 | 100.0% |
| CASE_A_LE2VARS_FALSE | FALSE | 1 | 1 | 0 | 100.0% |
| B1 | TRUE | 2 | 2 | 0 | 100.0% |
| B2 | TRUE | 6 | 6 | 0 | 100.0% |
| B_SUB | TRUE | 1 | 1 | 0 | 100.0% |
| B3_SAME | TRUE | 1 | 1 | 0 | 100.0% |
| B_RPROJ_NARROW | TRUE | 2 | 2 | 0 | 100.0% |
| DEFAULT_FALSE | FALSE | 110 | 78 | 32 | 70.9% |

### `evaluation_extra_hard`  —  accuracy 109/200 = 54.50%

Confusion: TP=9, FP=0, TN=100, FN=91

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| B1 | TRUE | 7 | 7 | 0 | 100.0% |
| B3_LOOSE | TRUE | 2 | 2 | 0 | 100.0% |
| DEFAULT_FALSE | FALSE | 191 | 100 | 91 | 52.4% |

### `evaluation_order5`  —  accuracy 177/200 = 88.50%

Confusion: TP=95, FP=18, TN=82, FN=5

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| S0a | TRUE | 41 | 41 | 0 | 100.0% |
| L | FALSE | 17 | 17 | 0 | 100.0% |
| R | FALSE | 23 | 23 | 0 | 100.0% |
| CASE_A_3VARS_TRUE | TRUE | 68 | 52 | 16 | 76.5% |
| CASE_A_LE2VARS_FALSE | FALSE | 9 | 9 | 0 | 100.0% |
| B2 | TRUE | 3 | 2 | 1 | 66.7% |
| B3_LOOSE | TRUE | 1 | 0 | 1 | 0.0% |
| DEFAULT_FALSE | FALSE | 38 | 33 | 5 | 86.8% |

## Full ETP rule breakdown

### `full_etp`  —  accuracy 21392345/22033636 = 97.09%

Confusion: TP=7615162, FP=78174, TN=13777183, FN=563117

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| S0a | TRUE | 3830304 | 3830304 | 0 | 100.0% |
| T1 | TRUE | 7755 | 7755 | 0 | 100.0% |
| F0 | FALSE | 4879590 | 4879590 | 0 | 100.0% |
| FP1_TRUE | TRUE | 10908 | 10908 | 0 | 100.0% |
| FP1_FALSE | FALSE | 31320 | 31320 | 0 | 100.0% |
| FP2_TRUE | TRUE | 10908 | 10908 | 0 | 100.0% |
| FP2_FALSE | FALSE | 31320 | 31320 | 0 | 100.0% |
| FP3_TRUE | TRUE | 3108 | 3108 | 0 | 100.0% |
| L | FALSE | 3268846 | 3268846 | 0 | 100.0% |
| R | FALSE | 2540115 | 2540115 | 0 | 100.0% |
| K | FALSE | 240 | 240 | 0 | 100.0% |
| X | FALSE | 1120440 | 1120440 | 0 | 100.0% |
| D_SPINE_L | FALSE | 20264 | 20264 | 0 | 100.0% |
| D_SPINE_R | FALSE | 20264 | 20264 | 0 | 100.0% |
| CASE_A_3VARS_TRUE | TRUE | 3068568 | 3068568 | 0 | 100.0% |
| CASE_A_LE2VARS_FALSE | FALSE | 267444 | 267293 | 151 | 99.9% |
| B1 | TRUE | 569330 | 549824 | 19506 | 96.6% |
| B2 | TRUE | 79992 | 61628 | 18364 | 77.0% |
| B3_SAME | TRUE | 3724 | 3066 | 658 | 82.3% |
| B3_LOOSE | TRUE | 67033 | 52841 | 14192 | 78.8% |
| B_RPROJ_NARROW | TRUE | 41706 | 16252 | 25454 | 39.0% |
| DEFAULT_FALSE | FALSE | 2160457 | 1597491 | 562966 | 73.9% |
