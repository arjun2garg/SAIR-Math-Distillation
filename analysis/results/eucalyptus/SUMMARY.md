# eucalyptus.txt programmatic checker — summary

## Overall accuracy

| dataset | n | accuracy |
|---------|--:|---------:|
| normal | 1000 | 743/1000 = 74.30% |
| hard | 200 | 126/200 = 63.00% |
| hard1 | 69 | 45/69 = 65.22% |
| hard2 | 200 | 100/200 = 50.00% |
| hard3 | 400 | 206/400 = 51.50% |
| evaluation_normal | 200 | 113/200 = 56.50% |
| evaluation_hard | 200 | 114/200 = 57.00% |
| evaluation_extra_hard | 200 | 100/200 = 50.00% |
| evaluation_order5 | 200 | 141/200 = 70.50% |
| full_etp | 22033636 | 17689539/22033636 = 80.2842% |

Hard countermodels parsed: 38 blocks, 63 Eq1 IDs resolved (0 strings unmatched).

## Per-split rule breakdown

### `normal`  —  accuracy 743/1000 = 74.30%

Confusion: TP=243, FP=0, TN=500, FN=257

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| X2_singleton_collapse | TRUE | 243 | 243 | 0 | 100.0% |
| L_constzero | FALSE | 172 | 172 | 0 | 100.0% |
| LP | FALSE | 114 | 114 | 0 | 100.0% |
| RP | FALSE | 98 | 98 | 0 | 100.0% |
| T2_AND | FALSE | 6 | 6 | 0 | 100.0% |
| T2_XOR | FALSE | 41 | 41 | 0 | 100.0% |
| T2_LEFT_NOT | FALSE | 8 | 8 | 0 | 100.0% |
| T2_RIGHT_NOT | FALSE | 5 | 5 | 0 | 100.0% |
| T2_NAND | FALSE | 1 | 1 | 0 | 100.0% |
| T2_IMPLY | FALSE | 3 | 3 | 0 | 100.0% |
| T2_NIMPLY | FALSE | 4 | 4 | 0 | 100.0% |
| T3_Z3_ADD | FALSE | 2 | 2 | 0 | 100.0% |
| T3_Z3_NEG | FALSE | 6 | 6 | 0 | 100.0% |
| T3_Z3_SUB | FALSE | 1 | 1 | 0 | 100.0% |
| HARD_002 | FALSE | 1 | 1 | 0 | 100.0% |
| HARD_012 | FALSE | 1 | 1 | 0 | 100.0% |
| HARD_016 | FALSE | 1 | 1 | 0 | 100.0% |
| HARD_029 | FALSE | 1 | 1 | 0 | 100.0% |
| HARD_030 | FALSE | 1 | 1 | 0 | 100.0% |
| HARD_036 | FALSE | 1 | 1 | 0 | 100.0% |
| CLASSIFY_DEFAULT_FALSE | FALSE | 290 | 33 | 257 | 11.4% |

### `hard`  —  accuracy 126/200 = 63.00%

Confusion: TP=0, FP=0, TN=126, FN=74

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| LP | FALSE | 9 | 9 | 0 | 100.0% |
| RP | FALSE | 3 | 3 | 0 | 100.0% |
| T2_AND | FALSE | 3 | 3 | 0 | 100.0% |
| HARD_014 | FALSE | 4 | 4 | 0 | 100.0% |
| HARD_015 | FALSE | 8 | 8 | 0 | 100.0% |
| HARD_018 | FALSE | 4 | 4 | 0 | 100.0% |
| HARD_019 | FALSE | 3 | 3 | 0 | 100.0% |
| CLASSIFY_DEFAULT_FALSE | FALSE | 166 | 92 | 74 | 55.4% |

### `hard1`  —  accuracy 45/69 = 65.22%

Confusion: TP=0, FP=0, TN=45, FN=24

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| LP | FALSE | 4 | 4 | 0 | 100.0% |
| RP | FALSE | 1 | 1 | 0 | 100.0% |
| T2_AND | FALSE | 1 | 1 | 0 | 100.0% |
| HARD_014 | FALSE | 1 | 1 | 0 | 100.0% |
| HARD_015 | FALSE | 2 | 2 | 0 | 100.0% |
| HARD_018 | FALSE | 2 | 2 | 0 | 100.0% |
| HARD_019 | FALSE | 1 | 1 | 0 | 100.0% |
| CLASSIFY_DEFAULT_FALSE | FALSE | 57 | 33 | 24 | 57.9% |

### `hard2`  —  accuracy 100/200 = 50.00%

Confusion: TP=0, FP=0, TN=100, FN=100

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| HARD_026 | FALSE | 9 | 9 | 0 | 100.0% |
| HARD_031 | FALSE | 9 | 9 | 0 | 100.0% |
| CLASSIFY_DEFAULT_FALSE | FALSE | 182 | 82 | 100 | 45.1% |

### `hard3`  —  accuracy 206/400 = 51.50%

Confusion: TP=1, FP=0, TN=205, FN=194

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| X2_singleton_collapse | TRUE | 1 | 1 | 0 | 100.0% |
| T2_LEFT_NOT | FALSE | 1 | 1 | 0 | 100.0% |
| T2_RIGHT_NOT | FALSE | 1 | 1 | 0 | 100.0% |
| T2_NAND | FALSE | 1 | 1 | 0 | 100.0% |
| T2_NIMPLY | FALSE | 1 | 1 | 0 | 100.0% |
| T3_Z3_ADD | FALSE | 1 | 1 | 0 | 100.0% |
| T3_Z3_NEG | FALSE | 11 | 11 | 0 | 100.0% |
| T3_Z3_SUB | FALSE | 1 | 1 | 0 | 100.0% |
| HARD_000 | FALSE | 1 | 1 | 0 | 100.0% |
| HARD_001 | FALSE | 1 | 1 | 0 | 100.0% |
| HARD_002 | FALSE | 1 | 1 | 0 | 100.0% |
| HARD_014 | FALSE | 3 | 3 | 0 | 100.0% |
| HARD_018 | FALSE | 1 | 1 | 0 | 100.0% |
| HARD_022 | FALSE | 7 | 7 | 0 | 100.0% |
| CLASSIFY_DEFAULT_FALSE | FALSE | 368 | 174 | 194 | 47.3% |

### `evaluation_normal`  —  accuracy 113/200 = 56.50%

Confusion: TP=13, FP=0, TN=100, FN=87

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| X2_singleton_collapse | TRUE | 13 | 13 | 0 | 100.0% |
| L_constzero | FALSE | 19 | 19 | 0 | 100.0% |
| LP | FALSE | 10 | 10 | 0 | 100.0% |
| RP | FALSE | 6 | 6 | 0 | 100.0% |
| T2_AND | FALSE | 4 | 4 | 0 | 100.0% |
| T2_XOR | FALSE | 14 | 14 | 0 | 100.0% |
| T2_LEFT_NOT | FALSE | 1 | 1 | 0 | 100.0% |
| T2_NAND | FALSE | 2 | 2 | 0 | 100.0% |
| T2_IMPLY | FALSE | 8 | 8 | 0 | 100.0% |
| T2_NIMPLY | FALSE | 4 | 4 | 0 | 100.0% |
| T3_Z3_ADD | FALSE | 2 | 2 | 0 | 100.0% |
| HARD_014 | FALSE | 2 | 2 | 0 | 100.0% |
| CLASSIFY_DEFAULT_FALSE | FALSE | 115 | 28 | 87 | 24.3% |

### `evaluation_hard`  —  accuracy 114/200 = 57.00%

Confusion: TP=14, FP=0, TN=100, FN=86

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| X2_singleton_collapse | TRUE | 14 | 14 | 0 | 100.0% |
| LP | FALSE | 1 | 1 | 0 | 100.0% |
| RP | FALSE | 7 | 7 | 0 | 100.0% |
| T2_XOR | FALSE | 13 | 13 | 0 | 100.0% |
| T2_RIGHT_NOT | FALSE | 3 | 3 | 0 | 100.0% |
| T2_NIMPLY | FALSE | 1 | 1 | 0 | 100.0% |
| T3_Z3_ADD | FALSE | 1 | 1 | 0 | 100.0% |
| T3_Z3_NEG | FALSE | 6 | 6 | 0 | 100.0% |
| T3_Z3_SUB | FALSE | 1 | 1 | 0 | 100.0% |
| HARD_014 | FALSE | 33 | 33 | 0 | 100.0% |
| HARD_022 | FALSE | 4 | 4 | 0 | 100.0% |
| CLASSIFY_DEFAULT_FALSE | FALSE | 116 | 30 | 86 | 25.9% |

### `evaluation_extra_hard`  —  accuracy 100/200 = 50.00%

Confusion: TP=0, FP=0, TN=100, FN=100

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| HARD_014 | FALSE | 8 | 8 | 0 | 100.0% |
| HARD_022 | FALSE | 61 | 61 | 0 | 100.0% |
| CLASSIFY_DEFAULT_FALSE | FALSE | 131 | 31 | 100 | 23.7% |

### `evaluation_order5`  —  accuracy 141/200 = 70.50%

Confusion: TP=41, FP=0, TN=100, FN=59

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| X2_singleton_collapse | TRUE | 41 | 41 | 0 | 100.0% |
| LP | FALSE | 17 | 17 | 0 | 100.0% |
| RP | FALSE | 23 | 23 | 0 | 100.0% |
| T2_LEFT_NOT | FALSE | 3 | 3 | 0 | 100.0% |
| T2_RIGHT_NOT | FALSE | 7 | 7 | 0 | 100.0% |
| T2_IMPLY | FALSE | 2 | 2 | 0 | 100.0% |
| T2_NIMPLY | FALSE | 1 | 1 | 0 | 100.0% |
| T3_Z3_NEG | FALSE | 10 | 10 | 0 | 100.0% |
| T3_Z3_SUB | FALSE | 4 | 4 | 0 | 100.0% |
| CLASSIFY_DEFAULT_FALSE | FALSE | 92 | 33 | 59 | 35.9% |

## Full ETP rule breakdown

### `full_etp`  —  accuracy 17689539/22033636 = 80.28%

Confusion: TP=3834182, FP=0, TN=13855357, FN=4344097

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| X1_tautology_eq2 | TRUE | 4694 | 4694 | 0 | 100.0% |
| X2_singleton_collapse | TRUE | 3829488 | 3829488 | 0 | 100.0% |
| L_constzero | FALSE | 4882728 | 4882728 | 0 | 100.0% |
| LP | FALSE | 3297843 | 3297843 | 0 | 100.0% |
| RP | FALSE | 2570860 | 2570860 | 0 | 100.0% |
| T2_AND | FALSE | 91442 | 91442 | 0 | 100.0% |
| T2_XOR | FALSE | 1077428 | 1077428 | 0 | 100.0% |
| T2_LEFT_NOT | FALSE | 175400 | 175400 | 0 | 100.0% |
| T2_RIGHT_NOT | FALSE | 171627 | 171627 | 0 | 100.0% |
| T2_NAND | FALSE | 48682 | 48682 | 0 | 100.0% |
| T2_IMPLY | FALSE | 125956 | 125956 | 0 | 100.0% |
| T2_NIMPLY | FALSE | 118817 | 118817 | 0 | 100.0% |
| T3_Z3_ADD | FALSE | 54654 | 54654 | 0 | 100.0% |
| T3_Z3_NEG | FALSE | 104286 | 104286 | 0 | 100.0% |
| T3_Z3_SUB | FALSE | 39592 | 39592 | 0 | 100.0% |
| HARD_000 | FALSE | 335 | 335 | 0 | 100.0% |
| HARD_001 | FALSE | 1076 | 1076 | 0 | 100.0% |
| HARD_002 | FALSE | 1184 | 1184 | 0 | 100.0% |
| HARD_004 | FALSE | 13545 | 13545 | 0 | 100.0% |
| HARD_005 | FALSE | 4548 | 4548 | 0 | 100.0% |
| HARD_008 | FALSE | 4548 | 4548 | 0 | 100.0% |
| HARD_010 | FALSE | 167 | 167 | 0 | 100.0% |
| HARD_011 | FALSE | 4682 | 4682 | 0 | 100.0% |
| HARD_012 | FALSE | 4515 | 4515 | 0 | 100.0% |
| HARD_014 | FALSE | 9232 | 9232 | 0 | 100.0% |
| HARD_015 | FALSE | 4681 | 4681 | 0 | 100.0% |
| HARD_016 | FALSE | 4621 | 4621 | 0 | 100.0% |
| HARD_017 | FALSE | 4621 | 4621 | 0 | 100.0% |
| HARD_018 | FALSE | 4683 | 4683 | 0 | 100.0% |
| HARD_019 | FALSE | 4616 | 4616 | 0 | 100.0% |
| HARD_020 | FALSE | 4682 | 4682 | 0 | 100.0% |
| HARD_021 | FALSE | 4682 | 4682 | 0 | 100.0% |
| HARD_022 | FALSE | 9232 | 9232 | 0 | 100.0% |
| HARD_023 | FALSE | 4685 | 4685 | 0 | 100.0% |
| HARD_024 | FALSE | 4687 | 4687 | 0 | 100.0% |
| HARD_025 | FALSE | 4691 | 4691 | 0 | 100.0% |
| HARD_026 | FALSE | 9034 | 9034 | 0 | 100.0% |
| HARD_027 | FALSE | 9034 | 9034 | 0 | 100.0% |
| HARD_028 | FALSE | 4518 | 4518 | 0 | 100.0% |
| HARD_029 | FALSE | 4517 | 4517 | 0 | 100.0% |
| HARD_030 | FALSE | 4518 | 4518 | 0 | 100.0% |
| HARD_031 | FALSE | 4517 | 4517 | 0 | 100.0% |
| HARD_032 | FALSE | 4517 | 4517 | 0 | 100.0% |
| HARD_033 | FALSE | 4517 | 4517 | 0 | 100.0% |
| HARD_034 | FALSE | 4656 | 4656 | 0 | 100.0% |
| HARD_035 | FALSE | 4605 | 4605 | 0 | 100.0% |
| HARD_036 | FALSE | 4656 | 4656 | 0 | 100.0% |
| HARD_037 | FALSE | 4656 | 4656 | 0 | 100.0% |
| CLASSIFY_DEFAULT_FALSE | FALSE | 5276681 | 932584 | 4344097 | 17.7% |
