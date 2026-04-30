# aj.txt programmatic checker — summary

## Implemented vs skipped

**Implemented:**  Step 1 (M1-M4), Step 2 (affine sweep over Z_n, 40 probes), Step 6 (M5-M14, M16, M18), Step 8 default-TRUE.

**Skipped:** Steps 0/3/4/5/7 (narrative or per-pair); M15, M17, M19, M20 (abstract or infinite).

## Overall accuracy

| dataset | n | accuracy |
|---------|--:|---------:|
| normal | 1000 | 971/1000 = 97.10% |
| hard | 200 | 121/200 = 60.50% |
| hard1 | 69 | 41/69 = 59.42% |
| hard2 | 200 | 156/200 = 78.00% |
| hard3 | 400 | 318/400 = 79.50% |
| evaluation_normal | 200 | 173/200 = 86.50% |
| evaluation_hard | 200 | 182/200 = 91.00% |
| evaluation_extra_hard | 200 | 169/200 = 84.50% |
| evaluation_order5 | 200 | 181/200 = 90.50% |
| full_etp | 22033636 | 21189208/22033636 = 96.1676% |

## Per-split rule breakdown

### `normal`  —  accuracy 971/1000 = 97.10%

Confusion: TP=500, FP=29, TN=471, FN=0

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| M1_const | FALSE | 172 | 172 | 0 | 100.0% |
| M2_leftzero3 | FALSE | 114 | 114 | 0 | 100.0% |
| M3_rightzero3 | FALSE | 98 | 98 | 0 | 100.0% |
| M4_wraparound | FALSE | 6 | 6 | 0 | 100.0% |
| Aff_2_1_3 | FALSE | 14 | 14 | 0 | 100.0% |
| Aff_1_2_4 | FALSE | 3 | 3 | 0 | 100.0% |
| Aff_1_3_4 | FALSE | 5 | 5 | 0 | 100.0% |
| Aff_2_1_4 | FALSE | 3 | 3 | 0 | 100.0% |
| Aff_2_2_4 | FALSE | 6 | 6 | 0 | 100.0% |
| Aff_2_3_4 | FALSE | 2 | 2 | 0 | 100.0% |
| Aff_3_2_4 | FALSE | 2 | 2 | 0 | 100.0% |
| Aff_3_3_4 | FALSE | 13 | 13 | 0 | 100.0% |
| Aff_1_2_5 | FALSE | 2 | 2 | 0 | 100.0% |
| Aff_2_1_5 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_2_2_5 | FALSE | 3 | 3 | 0 | 100.0% |
| Aff_2_3_5 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_2_4_5 | FALSE | 4 | 4 | 0 | 100.0% |
| Aff_3_3_5 | FALSE | 4 | 4 | 0 | 100.0% |
| Aff_4_2_5 | FALSE | 4 | 4 | 0 | 100.0% |
| Aff_3_6_7 | FALSE | 2 | 2 | 0 | 100.0% |
| M5_max3 | FALSE | 1 | 1 | 0 | 100.0% |
| M7_knuth | FALSE | 1 | 1 | 0 | 100.0% |
| M8_bck | FALSE | 2 | 2 | 0 | 100.0% |
| M12_nilp3 | FALSE | 3 | 3 | 0 | 100.0% |
| M13_affine2xmy3 | FALSE | 1 | 1 | 0 | 100.0% |
| M16_loop5 | FALSE | 4 | 4 | 0 | 100.0% |
| STEP8_DEFAULT_TRUE | TRUE | 529 | 500 | 29 | 94.5% |

### `hard`  —  accuracy 121/200 = 60.50%

Confusion: TP=74, FP=79, TN=47, FN=0

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| M2_leftzero3 | FALSE | 9 | 9 | 0 | 100.0% |
| M3_rightzero3 | FALSE | 3 | 3 | 0 | 100.0% |
| Aff_1_1_7 | FALSE | 3 | 3 | 0 | 100.0% |
| Aff_2_6_7 | FALSE | 5 | 5 | 0 | 100.0% |
| M7_knuth | FALSE | 19 | 19 | 0 | 100.0% |
| M12_nilp3 | FALSE | 1 | 1 | 0 | 100.0% |
| M16_loop5 | FALSE | 7 | 7 | 0 | 100.0% |
| STEP8_DEFAULT_TRUE | TRUE | 153 | 74 | 79 | 48.4% |

### `hard1`  —  accuracy 41/69 = 59.42%

Confusion: TP=24, FP=28, TN=17, FN=0

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| M2_leftzero3 | FALSE | 4 | 4 | 0 | 100.0% |
| M3_rightzero3 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_1_1_7 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_2_6_7 | FALSE | 2 | 2 | 0 | 100.0% |
| M7_knuth | FALSE | 6 | 6 | 0 | 100.0% |
| M12_nilp3 | FALSE | 1 | 1 | 0 | 100.0% |
| M16_loop5 | FALSE | 2 | 2 | 0 | 100.0% |
| STEP8_DEFAULT_TRUE | TRUE | 52 | 24 | 28 | 46.2% |

### `hard2`  —  accuracy 156/200 = 78.00%

Confusion: TP=100, FP=44, TN=56, FN=0

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| Aff_2_4_5 | FALSE | 12 | 12 | 0 | 100.0% |
| Aff_3_3_5 | FALSE | 4 | 4 | 0 | 100.0% |
| Aff_4_2_5 | FALSE | 13 | 13 | 0 | 100.0% |
| Aff_2_6_7 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_6_2_7 | FALSE | 1 | 1 | 0 | 100.0% |
| M7_knuth | FALSE | 6 | 6 | 0 | 100.0% |
| M12_nilp3 | FALSE | 19 | 19 | 0 | 100.0% |
| STEP8_DEFAULT_TRUE | TRUE | 144 | 100 | 44 | 69.4% |

### `hard3`  —  accuracy 318/400 = 79.50%

Confusion: TP=195, FP=82, TN=123, FN=0

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| M4_wraparound | FALSE | 34 | 34 | 0 | 100.0% |
| Aff_1_2_4 | FALSE | 8 | 8 | 0 | 100.0% |
| Aff_1_3_4 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_2_1_4 | FALSE | 8 | 8 | 0 | 100.0% |
| Aff_2_2_4 | FALSE | 4 | 4 | 0 | 100.0% |
| Aff_2_3_4 | FALSE | 16 | 16 | 0 | 100.0% |
| Aff_3_2_4 | FALSE | 18 | 18 | 0 | 100.0% |
| Aff_3_3_4 | FALSE | 5 | 5 | 0 | 100.0% |
| Aff_1_3_5 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_2_1_5 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_2_2_5 | FALSE | 3 | 3 | 0 | 100.0% |
| Aff_2_4_5 | FALSE | 2 | 2 | 0 | 100.0% |
| Aff_3_3_5 | FALSE | 2 | 2 | 0 | 100.0% |
| Aff_2_3_7 | FALSE | 1 | 1 | 0 | 100.0% |
| M6_nand | FALSE | 1 | 1 | 0 | 100.0% |
| M7_knuth | FALSE | 12 | 12 | 0 | 100.0% |
| M8_bck | FALSE | 2 | 2 | 0 | 100.0% |
| M12_nilp3 | FALSE | 4 | 4 | 0 | 100.0% |
| STEP8_DEFAULT_TRUE | TRUE | 277 | 195 | 82 | 70.4% |

### `evaluation_normal`  —  accuracy 173/200 = 86.50%

Confusion: TP=100, FP=27, TN=73, FN=0

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| M1_const | FALSE | 19 | 19 | 0 | 100.0% |
| M2_leftzero3 | FALSE | 10 | 10 | 0 | 100.0% |
| M3_rightzero3 | FALSE | 6 | 6 | 0 | 100.0% |
| M4_wraparound | FALSE | 2 | 2 | 0 | 100.0% |
| Aff_2_1_3 | FALSE | 8 | 8 | 0 | 100.0% |
| Aff_1_3_4 | FALSE | 2 | 2 | 0 | 100.0% |
| Aff_2_2_4 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_2_3_4 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_3_1_4 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_3_3_4 | FALSE | 3 | 3 | 0 | 100.0% |
| Aff_1_3_5 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_2_3_5 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_2_4_5 | FALSE | 3 | 3 | 0 | 100.0% |
| Aff_2_1_7 | FALSE | 1 | 1 | 0 | 100.0% |
| M6_nand | FALSE | 2 | 2 | 0 | 100.0% |
| M7_knuth | FALSE | 2 | 2 | 0 | 100.0% |
| M8_bck | FALSE | 4 | 4 | 0 | 100.0% |
| M12_nilp3 | FALSE | 3 | 3 | 0 | 100.0% |
| M13_affine2xmy3 | FALSE | 1 | 1 | 0 | 100.0% |
| M16_loop5 | FALSE | 2 | 2 | 0 | 100.0% |
| STEP8_DEFAULT_TRUE | TRUE | 127 | 100 | 27 | 78.7% |

### `evaluation_hard`  —  accuracy 182/200 = 91.00%

Confusion: TP=100, FP=18, TN=82, FN=0

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| M2_leftzero3 | FALSE | 1 | 1 | 0 | 100.0% |
| M3_rightzero3 | FALSE | 7 | 7 | 0 | 100.0% |
| M4_wraparound | FALSE | 7 | 7 | 0 | 100.0% |
| Aff_2_1_3 | FALSE | 3 | 3 | 0 | 100.0% |
| Aff_1_2_4 | FALSE | 2 | 2 | 0 | 100.0% |
| Aff_1_3_4 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_2_1_4 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_2_2_4 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_2_3_4 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_3_2_4 | FALSE | 2 | 2 | 0 | 100.0% |
| Aff_3_3_4 | FALSE | 11 | 11 | 0 | 100.0% |
| Aff_2_2_5 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_4_2_5 | FALSE | 3 | 3 | 0 | 100.0% |
| M7_knuth | FALSE | 37 | 37 | 0 | 100.0% |
| M12_nilp3 | FALSE | 1 | 1 | 0 | 100.0% |
| M16_loop5 | FALSE | 3 | 3 | 0 | 100.0% |
| STEP8_DEFAULT_TRUE | TRUE | 118 | 100 | 18 | 84.7% |

### `evaluation_extra_hard`  —  accuracy 169/200 = 84.50%

Confusion: TP=100, FP=31, TN=69, FN=0

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| M7_knuth | FALSE | 69 | 69 | 0 | 100.0% |
| STEP8_DEFAULT_TRUE | TRUE | 131 | 100 | 31 | 76.3% |

### `evaluation_order5`  —  accuracy 181/200 = 90.50%

Confusion: TP=100, FP=19, TN=81, FN=0

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| M2_leftzero3 | FALSE | 17 | 17 | 0 | 100.0% |
| M3_rightzero3 | FALSE | 23 | 23 | 0 | 100.0% |
| M4_wraparound | FALSE | 6 | 6 | 0 | 100.0% |
| Aff_2_1_3 | FALSE | 6 | 6 | 0 | 100.0% |
| Aff_1_2_4 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_2_1_4 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_2_3_4 | FALSE | 3 | 3 | 0 | 100.0% |
| Aff_1_4_5 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_2_3_5 | FALSE | 1 | 1 | 0 | 100.0% |
| Aff_2_4_5 | FALSE | 5 | 5 | 0 | 100.0% |
| Aff_3_3_5 | FALSE | 2 | 2 | 0 | 100.0% |
| Aff_4_2_5 | FALSE | 2 | 2 | 0 | 100.0% |
| M7_knuth | FALSE | 4 | 4 | 0 | 100.0% |
| M13_affine2xmy3 | FALSE | 8 | 8 | 0 | 100.0% |
| M18_laverA2 | FALSE | 1 | 1 | 0 | 100.0% |
| STEP8_DEFAULT_TRUE | TRUE | 119 | 100 | 19 | 84.0% |

## Full ETP rule breakdown

### `full_etp`  —  accuracy 21189208/22033636 = 96.17%

Confusion: TP=8178279, FP=844428, TN=13010929, FN=0

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| M1_const | FALSE | 4882728 | 4882728 | 0 | 100.0% |
| M2_leftzero3 | FALSE | 3297843 | 3297843 | 0 | 100.0% |
| M3_rightzero3 | FALSE | 2570860 | 2570860 | 0 | 100.0% |
| M4_wraparound | FALSE | 149321 | 149321 | 0 | 100.0% |
| Aff_2_1_3 | FALSE | 261511 | 261511 | 0 | 100.0% |
| Aff_1_2_4 | FALSE | 64850 | 64850 | 0 | 100.0% |
| Aff_1_3_4 | FALSE | 184424 | 184424 | 0 | 100.0% |
| Aff_2_1_4 | FALSE | 67390 | 67390 | 0 | 100.0% |
| Aff_2_2_4 | FALSE | 92565 | 92565 | 0 | 100.0% |
| Aff_2_3_4 | FALSE | 76631 | 76631 | 0 | 100.0% |
| Aff_3_1_4 | FALSE | 6302 | 6302 | 0 | 100.0% |
| Aff_3_2_4 | FALSE | 60946 | 60946 | 0 | 100.0% |
| Aff_3_3_4 | FALSE | 387944 | 387944 | 0 | 100.0% |
| Aff_1_2_5 | FALSE | 40707 | 40707 | 0 | 100.0% |
| Aff_1_3_5 | FALSE | 14245 | 14245 | 0 | 100.0% |
| Aff_1_4_5 | FALSE | 231 | 231 | 0 | 100.0% |
| Aff_2_1_5 | FALSE | 43304 | 43304 | 0 | 100.0% |
| Aff_2_2_5 | FALSE | 76008 | 76008 | 0 | 100.0% |
| Aff_2_3_5 | FALSE | 41036 | 41036 | 0 | 100.0% |
| Aff_2_4_5 | FALSE | 124251 | 124251 | 0 | 100.0% |
| Aff_3_1_5 | FALSE | 2955 | 2955 | 0 | 100.0% |
| Aff_3_2_5 | FALSE | 566 | 566 | 0 | 100.0% |
| Aff_3_3_5 | FALSE | 50172 | 50172 | 0 | 100.0% |
| Aff_3_4_5 | FALSE | 10854 | 10854 | 0 | 100.0% |
| Aff_4_2_5 | FALSE | 91874 | 91874 | 0 | 100.0% |
| Aff_4_3_5 | FALSE | 6280 | 6280 | 0 | 100.0% |
| Aff_1_1_7 | FALSE | 5841 | 5841 | 0 | 100.0% |
| Aff_1_2_7 | FALSE | 1710 | 1710 | 0 | 100.0% |
| Aff_1_3_7 | FALSE | 395 | 395 | 0 | 100.0% |
| Aff_2_1_7 | FALSE | 1972 | 1972 | 0 | 100.0% |
| Aff_2_2_7 | FALSE | 1002 | 1002 | 0 | 100.0% |
| Aff_2_3_7 | FALSE | 1461 | 1461 | 0 | 100.0% |
| Aff_2_6_7 | FALSE | 16857 | 16857 | 0 | 100.0% |
| Aff_3_1_7 | FALSE | 306 | 306 | 0 | 100.0% |
| Aff_3_2_7 | FALSE | 320 | 320 | 0 | 100.0% |
| Aff_3_6_7 | FALSE | 9575 | 9575 | 0 | 100.0% |
| Aff_6_2_7 | FALSE | 2889 | 2889 | 0 | 100.0% |
| Aff_6_3_7 | FALSE | 209 | 209 | 0 | 100.0% |
| M5_max3 | FALSE | 5016 | 5016 | 0 | 100.0% |
| M6_nand | FALSE | 31691 | 31691 | 0 | 100.0% |
| M7_knuth | FALSE | 37132 | 37132 | 0 | 100.0% |
| M8_bck | FALSE | 77687 | 77687 | 0 | 100.0% |
| M9_impl | FALSE | 961 | 961 | 0 | 100.0% |
| M10_rps | FALSE | 58 | 58 | 0 | 100.0% |
| M12_nilp3 | FALSE | 103102 | 103102 | 0 | 100.0% |
| M13_affine2xmy3 | FALSE | 33138 | 33138 | 0 | 100.0% |
| M16_loop5 | FALSE | 67626 | 67626 | 0 | 100.0% |
| M18_laverA2 | FALSE | 6183 | 6183 | 0 | 100.0% |
| STEP8_DEFAULT_TRUE | TRUE | 9022707 | 8178279 | 844428 | 90.6% |
