# Resultados simulados: patch_2g45

Geometria nominal: Patch 2.45 GHz: L = 28.9 mm, W = 37.3 mm, inset = 8.8 mm, folga = 1.0 mm, linha = 3.0 mm; placa 70 x 70 mm, FR-4 1.6 mm (er = 4.4)

Referência: borda da placa, na entrada do SMA. Faixa simulada: 2 a 3 GHz.

| Caso | Ressonância (GHz) | S11 mínimo (dB) | Faixa com S11 < -10 dB (GHz) | Largura (MHz) |
|---|---|---|---|---|
| nominal | 2.448 | -31.7 | 2.416 a 2.480 | 64 |
| FR-4 com er = 4,2 | 2.503 | -32.1 | 2.470 a 2.536 | 66 |
| FR-4 com er = 4,6 | 2.396 | -28.0 | 2.365 a 2.428 | 63 |
| fresa come 0,1 mm por borda | 2.463 | -27.6 | 2.431 a 2.495 | 64 |
| placa com 1,5 mm | 2.451 | -25.1 | 2.422 a 2.481 | 59 |

Impedância de entrada na ressonância (nominal): 47.6 +1.0j ohm.

## Radiação em 2.448 GHz (nominal)

- diretividade: 6.8 dBi
- eficiência de radiação: 41 % (o FR-4 tem perdas altas; num substrato de RF passaria de 80 %)
- ganho realizado: 3.0 dBi

## Enlace entre duas antenas iguais (|S21| no VNA de 2 portas, espaço livre)

| Distância (m) | S21 esperado (dB) |
|---|---|
| 0.5 | -28.2 |
| 1 | -34.2 |
| 1.5 | -37.7 |

Num laboratório comum, as reflexões em paredes e mesas mudam o S21 em alguns dB.
