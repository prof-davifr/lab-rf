# Resultados simulados: patch_2g45

Antena: Patch 2.45 GHz: L = 30.0 mm, W = 20.0 mm, inset = 13.5 mm, folga = 1.0 mm, linha = 3.0 mm; placa 45 x 32 mm, FR-4 1.6 mm (er = 4.4)

Referência: borda da placa, na entrada do SMA. Faixa simulada: 2 a 3 GHz.

## Etapa 1: antena no ar

| Caso | Ressonância (GHz) | S11 mínimo (dB) | Faixa com S11 < -10 dB (GHz) | Largura (MHz) |
|---|---|---|---|---|
| nominal | 2.420 | -11.9 | 2.404 a 2.436 | 32 |
| FR-4 com er = 4,2 | 2.473 | -11.4 | 2.459 a 2.488 | 28 |
| FR-4 com er = 4,6 | 2.370 | -12.6 | 2.352 a 2.387 | 35 |
| fresa come 0,1 mm por borda | 2.428 | -8.6 | não chega a -10 dB | - |

## Etapa 2: antena sobre o revestimento

Amostra seca: amostra: 10 mm de polímero (er = 4, tand = 0.01) com 0 % de água -> er = 4.00, tand = 0.010; gap 3 mm.

| Água no polímero | er / tand do polímero | Ressonância (GHz) | Deslocamento (MHz) | S11 mínimo (dB) | Faixa com S11 < -10 dB (GHz) | Largura (MHz) |
|---|---|---|---|---|---|---|
| 0 % | 4.00 / 0.010 | 2.451 | +0 | -23.0 | 2.433 a 2.470 | 37 |
| 2 % | 4.56 / 0.019 | 2.445 | -7 | -25.7 | 2.426 a 2.463 | 37 |
| 4 % | 5.16 / 0.027 | 2.439 | -13 | -28.0 | 2.420 a 2.458 | 37 |
| 6 % | 5.80 / 0.034 | 2.433 | -18 | -29.6 | 2.414 a 2.452 | 38 |
| 8 % | 6.47 / 0.040 | 2.428 | -24 | -33.5 | 2.409 a 2.446 | 37 |
| 10 % | 7.18 / 0.046 | 2.422 | -29 | -33.8 | 2.404 a 2.441 | 38 |

Efeito do gap (amostra seca):

| Gap | Ressonância (GHz) | Deslocamento (MHz) | S11 mínimo (dB) | Faixa com S11 < -10 dB (GHz) | Largura (MHz) |
|---|---|---|---|---|---|
| 2 mm | 2.440 | -11 | -27.6 | 2.422 a 2.458 | 36 |
| 4 mm | 2.457 | +6 | -20.6 | 2.438 a 2.476 | 38 |
