# Resultados simulados: patch_3g50

Antena: Patch 3.5 GHz: L = 20.0 mm, W = 26.0 mm, inset = 7.25 mm, folga = 1.0 mm, linha = 3.0 mm; placa 35 x 38 mm, FR-4 1.6 mm (er = 4.4)

Referência: borda da placa, na entrada do SMA. Faixa simulada: 2.5 a 4.5 GHz.

## Etapa 1: antena no ar

| Caso | Ressonância (GHz) | S11 mínimo (dB) | Faixa com S11 < -10 dB (GHz) | Largura (MHz) |
|---|---|---|---|---|
| nominal | 3.489 | -16.5 | 3.439 a 3.538 | 99 |
| FR-4 com er = 4,2 | 3.565 | -15.8 | 3.515 a 3.615 | 100 |
| FR-4 com er = 4,6 | 3.417 | -17.0 | 3.367 a 3.466 | 99 |
| fresa come 0,1 mm por borda | 3.512 | -11.9 | 3.480 a 3.543 | 63 |

## Etapa 2: antena sobre o revestimento

Amostra seca: amostra: 10 mm de polímero (er = 4, tand = 0.01) com 0 % de água -> er = 4.00, tand = 0.010; gap 3 mm.

| Água no polímero | er / tand do polímero | Ressonância (GHz) | Deslocamento (MHz) | S11 mínimo (dB) | Faixa com S11 < -10 dB (GHz) | Largura (MHz) |
|---|---|---|---|---|---|---|
| 0 % | 4.00 / 0.010 | 3.514 | +0 | -15.6 | 3.484 a 3.545 | 60 |
| 2 % | 4.56 / 0.023 | 3.502 | -12 | -15.9 | 3.471 a 3.533 | 62 |
| 4 % | 5.15 / 0.034 | 3.489 | -26 | -15.9 | 3.458 a 3.520 | 62 |
| 6 % | 5.78 / 0.045 | 3.475 | -40 | -16.6 | 3.443 a 3.507 | 64 |
| 8 % | 6.45 / 0.054 | 3.460 | -55 | -17.8 | 3.426 a 3.494 | 68 |
| 10 % | 7.15 / 0.062 | 3.443 | -71 | -19.3 | 3.408 a 3.479 | 70 |

Efeito do gap (amostra seca):

| Gap | Ressonância (GHz) | Deslocamento (MHz) | S11 mínimo (dB) | Faixa com S11 < -10 dB (GHz) | Largura (MHz) |
|---|---|---|---|---|---|
| 2 mm | 3.505 | -10 | -15.1 | 3.476 a 3.533 | 57 |
| 4 mm | 3.518 | +3 | -15.6 | 3.487 a 3.549 | 62 |
