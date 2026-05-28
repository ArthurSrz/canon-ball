## La manière dont je connecte la couche de connaissances au prompt change l'endroit où la balle atterrit

J'ai testé quatre façons d'injecter une couche de connaissances (une définition Wikidata de l'alpinisme) dans un même prompt, en mesurant la dispersion sémantique sur 12 essais par groupe avec qwen2.5 et des embeddings bge-m3.

### Résultats

| Mode | Ratio de dispersion | Resserrement | p-value | Δ centroïde (cosinus) |
|------|:---:|:---:|:---:|:---:|
| **System → User** | 0,724 | −27,6 % | <1e-4 | 0,020 |
| Injection par template | 0,786 | −21,4 % | 0,030 | 0,019 |
| Amorçage CoT | 0,816 | −18,4 % | 0,012 | 0,024 |
| Entrelacé | 0,894 | −10,6 % | 0,100 | 0,015 |

### Ce que fait chaque mode

- **System → User** — je place la connaissance dans un message `system` et le prompt dans un message `user` (deux messages séparés)
- **Injection par template** — je fusionne prompt + `---\nContexte :\n` + connaissance dans un seul message `user`
- **Amorçage CoT** — j'injecte la connaissance comme un faux tour `assistant` antérieur (« que sais-tu ? » → connaissance → prompt)
- **Entrelacé** — j'insère les paragraphes de connaissance entre les phrases du prompt, dans un unique message `user`

### Lecture

C'est le créneau du message système qui resserre le plus la zone d'atterrissage (−27,6 %, p < 0,0001). Je constate que le rôle `system` porte un signal de confiance implicite qui concentre la sortie du modèle autour de la connaissance. L'injection par template arrive en deuxième : le séparateur `---` me suffit pour que le modèle traite la connaissance comme du matériau de référence, mais sans la position privilégiée d'un message système.

L'amorçage CoT produit le plus grand déplacement de centroïde que j'observe (0,024 cosinus) — en présentant la connaissance comme quelque chose que le modèle « a déjà dit », je déplace le centre de la réponse plus qu'avec tout autre mode, même si je ne resserre pas autant la zone. L'entrelacement est la stratégie la plus faible que j'aie testée : en fragmentant la connaissance entre les phrases du prompt, j'en détruis la cohérence, et l'effet n'atteint pas la significativité.

Ce que j'en retiens, c'est qu'*où* je place la connaissance dans le flux de messages compte autant que *ce qu'*elle contient. Les mêmes 450 caractères de connaissance produisent, selon la manière dont je les assemble, une différence d'un facteur 3 dans le resserrement.
