# XAUUSD VB/H4 Candidate Validation

Candidate parameters:

- N: `18`
- Exit: `10`
- SL ATR: `2.2`
- Trail ATR: `3.2`
- H1 ADX min: `18.0`
- ATR ratio min: `1.0`

## Formal Annual Report

- Avg Return: `25.73%`
- Avg PF: `2.12`
- Avg MaxDD: `9.28%`
- Positive Years: `11/11`

## Cost Stress

| Scenario | Spread x | Slippage | Avg Ret | Avg PF | Avg DD | Pos Years | Worst Year |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| base | 1.0 | 1.0 | 25.73% | 2.12 | 9.28% | 11/11 | 1.18% |
| spread_1_25x | 1.25 | 1.0 | 23.69% | 1.56 | 8.43% | 9/11 | 0.00% |
| spread_1_50x | 1.5 | 1.0 | 23.43% | 2.25 | 7.14% | 8/11 | -4.13% |
| slippage_2x | 1.0 | 2.0 | 25.69% | 2.12 | 9.30% | 11/11 | 1.12% |
| spread_1_50x_slippage_2x | 1.5 | 2.0 | 23.40% | 2.24 | 7.14% | 8/11 | -4.17% |

## Walk Forward

| Window | Train Ret | Train PF | Test Ret | Test PF | Test Pos Years | Test Worst Year |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| wf_2015_2019__2020_2021 | 4.74% | 1.94 | 22.23% | 1.84 | 2/2 | 19.65% |
| wf_2016_2020__2021_2022 | 7.59% | 1.34 | 21.00% | 1.82 | 2/2 | 17.19% |
| wf_2017_2021__2022_2023 | 11.86% | 1.48 | 26.14% | 1.95 | 2/2 | 17.19% |
| wf_2018_2022__2023_2024 | 13.52% | 1.43 | 29.19% | 2.12 | 2/2 | 23.27% |
| wf_2019_2023__2024_2025 | 20.31% | 1.71 | 81.30% | 3.04 | 2/2 | 23.27% |