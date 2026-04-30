# pi.txt programmatic checker — summary

## Overall accuracy

| dataset | n | accuracy |
|---------|--:|---------:|
| normal | 1000 | 681/1000 = 68.10% |
| hard | 200 | 99/200 = 49.50% |
| hard1 | 69 | 32/69 = 46.38% |
| hard2 | 200 | 100/200 = 50.00% |
| hard3 | 400 | 344/400 = 86.00% |
| evaluation_normal | 200 | 116/200 = 58.00% |
| evaluation_hard | 200 | 159/200 = 79.50% |
| evaluation_extra_hard | 200 | 195/200 = 97.50% |
| evaluation_order5 | 200 | 137/200 = 68.50% |
| full_etp | 22033636 | 13661037/22033636 = 62.0008% |

## Per-split rule breakdown

### `normal`  —  accuracy 681/1000 = 68.10%

Confusion: TP=439, FP=258, TN=242, FN=61

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| X3 | TRUE | 243 | 243 | 0 | 100.0% |
| F3_FALSE | FALSE | 25 | 25 | 0 | 100.0% |
| F4_TRUE | TRUE | 2 | 0 | 2 | 0.0% |
| F4_FALSE | FALSE | 19 | 19 | 0 | 100.0% |
| A1 | FALSE | 28 | 28 | 0 | 100.0% |
| A2 | FALSE | 25 | 25 | 0 | 100.0% |
| A3 | FALSE | 12 | 12 | 0 | 100.0% |
| A4 | FALSE | 29 | 29 | 0 | 100.0% |
| A5 | FALSE | 34 | 34 | 0 | 100.0% |
| A6 | FALSE | 26 | 26 | 0 | 100.0% |
| A7 | FALSE | 1 | 1 | 0 | 100.0% |
| A8 | FALSE | 13 | 13 | 0 | 100.0% |
| A10 | FALSE | 11 | 11 | 0 | 100.0% |
| H1 | FALSE | 19 | 1 | 18 | 5.3% |
| H2 | FALSE | 4 | 4 | 0 | 100.0% |
| H3 | FALSE | 45 | 3 | 42 | 6.7% |
| H4 | FALSE | 8 | 8 | 0 | 100.0% |
| H5 | FALSE | 4 | 3 | 1 | 75.0% |
| DEFAULT_TRUE | TRUE | 452 | 196 | 256 | 43.4% |

### `hard`  —  accuracy 99/200 = 49.50%

Confusion: TP=71, FP=98, TN=28, FN=3

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| F3_TRUE | TRUE | 1 | 0 | 1 | 0.0% |
| F4_TRUE | TRUE | 3 | 0 | 3 | 0.0% |
| A3 | FALSE | 3 | 3 | 0 | 100.0% |
| H2 | FALSE | 4 | 4 | 0 | 100.0% |
| H3 | FALSE | 16 | 16 | 0 | 100.0% |
| H5 | FALSE | 5 | 5 | 0 | 100.0% |
| H6 | FALSE | 3 | 0 | 3 | 0.0% |
| DEFAULT_TRUE | TRUE | 165 | 71 | 94 | 43.0% |

### `hard1`  —  accuracy 32/69 = 46.38%

Confusion: TP=23, FP=36, TN=9, FN=1

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| F3_TRUE | TRUE | 1 | 0 | 1 | 0.0% |
| F4_TRUE | TRUE | 1 | 0 | 1 | 0.0% |
| A3 | FALSE | 1 | 1 | 0 | 100.0% |
| H2 | FALSE | 1 | 1 | 0 | 100.0% |
| H3 | FALSE | 5 | 5 | 0 | 100.0% |
| H5 | FALSE | 2 | 2 | 0 | 100.0% |
| H6 | FALSE | 1 | 0 | 1 | 0.0% |
| DEFAULT_TRUE | TRUE | 57 | 23 | 34 | 40.4% |

### `hard2`  —  accuracy 100/200 = 50.00%

Confusion: TP=71, FP=71, TN=29, FN=29

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| F3_TRUE | TRUE | 1 | 0 | 1 | 0.0% |
| F4_TRUE | TRUE | 3 | 0 | 3 | 0.0% |
| A9 | FALSE | 1 | 1 | 0 | 100.0% |
| A10 | FALSE | 4 | 4 | 0 | 100.0% |
| H2 | FALSE | 2 | 2 | 0 | 100.0% |
| H3 | FALSE | 47 | 21 | 26 | 44.7% |
| H5 | FALSE | 2 | 0 | 2 | 0.0% |
| H6 | FALSE | 2 | 1 | 1 | 50.0% |
| DEFAULT_TRUE | TRUE | 138 | 71 | 67 | 51.4% |

### `hard3`  —  accuracy 344/400 = 86.00%

Confusion: TP=193, FP=54, TN=151, FN=2

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| X3 | TRUE | 1 | 1 | 0 | 100.0% |
| F2_TRUE | TRUE | 1 | 1 | 0 | 100.0% |
| F3_TRUE | TRUE | 5 | 4 | 1 | 80.0% |
| F3_FALSE | FALSE | 1 | 1 | 0 | 100.0% |
| F4_TRUE | TRUE | 4 | 3 | 1 | 75.0% |
| A1 | FALSE | 42 | 42 | 0 | 100.0% |
| A2 | FALSE | 33 | 33 | 0 | 100.0% |
| A3 | FALSE | 1 | 1 | 0 | 100.0% |
| A4 | FALSE | 1 | 1 | 0 | 100.0% |
| A5 | FALSE | 7 | 7 | 0 | 100.0% |
| A6 | FALSE | 26 | 26 | 0 | 100.0% |
| A8 | FALSE | 5 | 5 | 0 | 100.0% |
| A9 | FALSE | 1 | 1 | 0 | 100.0% |
| A10 | FALSE | 6 | 6 | 0 | 100.0% |
| H1 | FALSE | 2 | 2 | 0 | 100.0% |
| H2 | FALSE | 6 | 6 | 0 | 100.0% |
| H3 | FALSE | 8 | 8 | 0 | 100.0% |
| H4 | FALSE | 5 | 4 | 1 | 80.0% |
| H5 | FALSE | 5 | 4 | 1 | 80.0% |
| H6 | FALSE | 4 | 4 | 0 | 100.0% |
| DEFAULT_TRUE | TRUE | 236 | 184 | 52 | 78.0% |

### `evaluation_normal`  —  accuracy 116/200 = 58.00%

Confusion: TP=69, FP=53, TN=47, FN=31

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| X3 | TRUE | 13 | 13 | 0 | 100.0% |
| A1 | FALSE | 20 | 20 | 0 | 100.0% |
| A2 | FALSE | 2 | 2 | 0 | 100.0% |
| A3 | FALSE | 3 | 3 | 0 | 100.0% |
| A4 | FALSE | 5 | 5 | 0 | 100.0% |
| A5 | FALSE | 13 | 13 | 0 | 100.0% |
| H1 | FALSE | 3 | 0 | 3 | 0.0% |
| H2 | FALSE | 3 | 0 | 3 | 0.0% |
| H3 | FALSE | 24 | 4 | 20 | 16.7% |
| H4 | FALSE | 5 | 0 | 5 | 0.0% |
| DEFAULT_TRUE | TRUE | 109 | 56 | 53 | 51.4% |

### `evaluation_hard`  —  accuracy 159/200 = 79.50%

Confusion: TP=74, FP=15, TN=85, FN=26

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| X3 | TRUE | 14 | 14 | 0 | 100.0% |
| F3_TRUE | TRUE | 2 | 2 | 0 | 100.0% |
| F3_FALSE | FALSE | 7 | 7 | 0 | 100.0% |
| F4_TRUE | TRUE | 3 | 2 | 1 | 66.7% |
| F4_FALSE | FALSE | 13 | 13 | 0 | 100.0% |
| A1 | FALSE | 3 | 3 | 0 | 100.0% |
| A3 | FALSE | 1 | 1 | 0 | 100.0% |
| A4 | FALSE | 1 | 1 | 0 | 100.0% |
| A5 | FALSE | 13 | 13 | 0 | 100.0% |
| A6 | FALSE | 4 | 4 | 0 | 100.0% |
| A8 | FALSE | 5 | 5 | 0 | 100.0% |
| A10 | FALSE | 1 | 1 | 0 | 100.0% |
| H1 | FALSE | 5 | 0 | 5 | 0.0% |
| H2 | FALSE | 5 | 0 | 5 | 0.0% |
| H3 | FALSE | 52 | 37 | 15 | 71.2% |
| H6 | FALSE | 1 | 0 | 1 | 0.0% |
| DEFAULT_TRUE | TRUE | 70 | 56 | 14 | 80.0% |

### `evaluation_extra_hard`  —  accuracy 195/200 = 97.50%

Confusion: TP=95, FP=0, TN=100, FN=5

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| F3_TRUE | TRUE | 18 | 18 | 0 | 100.0% |
| F4_TRUE | TRUE | 1 | 1 | 0 | 100.0% |
| H3 | FALSE | 100 | 100 | 0 | 100.0% |
| H5 | FALSE | 3 | 0 | 3 | 0.0% |
| H6 | FALSE | 2 | 0 | 2 | 0.0% |
| DEFAULT_TRUE | TRUE | 76 | 76 | 0 | 100.0% |

### `evaluation_order5`  —  accuracy 137/200 = 68.50%

Confusion: TP=76, FP=39, TN=61, FN=24

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| X3 | TRUE | 41 | 41 | 0 | 100.0% |
| A1 | FALSE | 10 | 10 | 0 | 100.0% |
| A2 | FALSE | 9 | 9 | 0 | 100.0% |
| A4 | FALSE | 4 | 4 | 0 | 100.0% |
| A5 | FALSE | 12 | 12 | 0 | 100.0% |
| A6 | FALSE | 5 | 5 | 0 | 100.0% |
| A8 | FALSE | 2 | 2 | 0 | 100.0% |
| A10 | FALSE | 4 | 4 | 0 | 100.0% |
| H1 | FALSE | 9 | 0 | 9 | 0.0% |
| H3 | FALSE | 21 | 8 | 13 | 38.1% |
| H4 | FALSE | 6 | 5 | 1 | 83.3% |
| H5 | FALSE | 1 | 1 | 0 | 100.0% |
| H6 | FALSE | 2 | 1 | 1 | 50.0% |
| DEFAULT_TRUE | TRUE | 74 | 35 | 39 | 47.3% |

## Full ETP rule breakdown

### `full_etp`  —  accuracy 13661037/22033636 = 62.00%

Confusion: TP=7131114, FP=7325434, TN=6529923, FN=1047165

| rule | verdict | fires | correct | wrong | precision |
|------|---------|------:|--------:|------:|----------:|
| X1 | TRUE | 4694 | 4694 | 0 | 100.0% |
| X2 | TRUE | 4693 | 4693 | 0 | 100.0% |
| X3 | TRUE | 3828672 | 3828672 | 0 | 100.0% |
| F1_TRUE | TRUE | 1212 | 1212 | 0 | 100.0% |
| F1_FALSE | FALSE | 3480 | 3480 | 0 | 100.0% |
| F2_TRUE | TRUE | 1212 | 1212 | 0 | 100.0% |
| F2_FALSE | FALSE | 3480 | 3480 | 0 | 100.0% |
| F3_TRUE | TRUE | 26796 | 7791 | 19005 | 29.1% |
| F3_FALSE | FALSE | 695772 | 695772 | 0 | 100.0% |
| F4_TRUE | TRUE | 26796 | 7791 | 19005 | 29.1% |
| F4_FALSE | FALSE | 695772 | 695772 | 0 | 100.0% |
| A1 | FALSE | 812889 | 812889 | 0 | 100.0% |
| A2 | FALSE | 808876 | 808876 | 0 | 100.0% |
| A3 | FALSE | 220530 | 220530 | 0 | 100.0% |
| A4 | FALSE | 657092 | 657092 | 0 | 100.0% |
| A5 | FALSE | 1000068 | 1000068 | 0 | 100.0% |
| A6 | FALSE | 619093 | 619093 | 0 | 100.0% |
| A7 | FALSE | 11763 | 11763 | 0 | 100.0% |
| A8 | FALSE | 271388 | 271388 | 0 | 100.0% |
| A9 | FALSE | 2532 | 2532 | 0 | 100.0% |
| A10 | FALSE | 196686 | 196686 | 0 | 100.0% |
| H1 | FALSE | 308885 | 28525 | 280360 | 9.2% |
| H2 | FALSE | 116459 | 107440 | 9019 | 92.3% |
| H3 | FALSE | 891212 | 154041 | 737171 | 17.3% |
| H4 | FALSE | 180087 | 175428 | 4659 | 97.4% |
| H5 | FALSE | 32124 | 23822 | 8302 | 74.2% |
| H6 | FALSE | 48900 | 41246 | 7654 | 84.3% |
| DEFAULT_TRUE | TRUE | 10562473 | 3275049 | 7287424 | 31.0% |
