<!--
ARCHIVAL — Spanish original of the v2 design document, preserved verbatim.

Authored 2026-08-13; recovered from the v2 design discussion transcript.
This file is the drift-guard for the normative English translation in
DESIGN.md and is the only Spanish file in this repository (explicit
exception approved by the author, 2026-08-13). Do not edit: bootstrap
resolutions are applied only in DESIGN.md.
-->

# Asistente de verificación con evidencia — Documento de diseño (v2)
**Proyecto:** evolución de [`NLP-Fake-News-Colombia`](https://github.com/POLUX89/NLP-Fake-News-Colombia)
**Estado:** diseño. v1 completada y publicada; v2 sin implementar.
**Fecha del documento:** 13 de agosto de 2026
> Nota: este documento está en español porque así se diseñó. El repositorio
> actual está íntegramente en inglés; si se incorpora como `docs/V2_DESIGN.md`
> conviene traducirlo por consistencia.
---
## 1. Qué es y qué no es
**Es** un asistente que, dado un enunciado en español, recupera y muestra
evidencia pertinente de un corpus curado —priorizando fuentes primarias—, y
subordinadamente estima cómo un verificador profesional lo etiquetaría.
**No es** un detector de verdad ni un "detector de fake news". No dispone de
*ground truth*: dispone de juicios expertos publicados y mide concordancia con
ellos.
Formulación operativa: **predictor de juicio verificador + recuperador de
evidencia**, no clasificador de veracidad.
### Cambio de producto respecto a la v1
| | v1 (hecha) | v2 (diseño) |
|---|---|---|
| Entrada | texto del claim | texto del claim + corpus |
| Producto | etiqueta | **evidencia**; etiqueta secundaria |
| Base de la decisión | estilo/tema aprendido | relación lógica con documentos |
| Etiqueta ColombiaCheck | objetivo de entrenamiento | referencia de evaluación |
---
## 2. Motivación empírica (resultados propios de la v1)
La v2 no nace de una preferencia estética, sino de un resultado medido:
| Modelo | macro-F1 (test) | Falso | Cuestionable | Verdadero |
|---|---|---|---|---|
| TF-IDF + LogReg | 0.386 | 0.743 | 0.351 | 0.065 |
| BETO (weighted loss) | **0.405** | 0.806 | 0.410 | **0.000** |
- BETO apenas supera a bag-of-words (+0.02 en test; IC 95% [0.371, 0.440]).
- `Verdadero` es inaprendible: 93 ejemplos, en declive (33 en 2020 → 2 en 2026).
- El EDA muestra que `petro`, `video` y `colombia` encabezan **las tres clases**:
  el tema no separa el veredicto.
**Conclusión:** clasificar veracidad desde el texto del claim no funciona, y no
es un problema de capacidad del modelo. La señal necesaria no está en el claim;
está en la evidencia externa. Ese es el argumento de diseño de la v2.
Este resultado negativo, reportado honestamente, es el activo narrativo central
del proyecto.
---
## 3. El problema del *ground truth* y sus salvaguardas
Las etiquetas de ColombiaCheck son un juicio periodístico con metodología
pública: referencia ruidosa valiosa, no verdad de campo.
(Formulación cuidadosa: *limitación metodológica*, no cuestionamiento de
credibilidad del medio.)
Salvaguardas:
1. **Triangulación multi-verificador.** Vía ClaimReview incorporar AFP Factual,
   EFE Verifica, La Silla Vacía, Chequeado. Calcular κ entre verificadores sobre
   claims comunes → **techo humano** de referencia.
2. **Etiquetas blandas / exclusión marcada** donde los verificadores difieren.
3. **Abstención de primera clase.** Clase NEI ("evidencia insuficiente") +
   predicción selectiva por umbral. Conformal prediction (MAPIE) como refinamiento.
4. **Calibración medida.** ECE y diagramas de fiabilidad en cada release.
5. **Auditoría de etiquetas** con confident learning (cleanlab) → cola de revisión.
6. **κ propio del autor** sobre ~100 claims, para validar el mapeo de escalas.
7. **Evidencia siempre visible**, con fuente y fecha.
8. **Test de simetría** (§7) antes de cualquier publicación.
**Métricas:** macro-F1, κ ponderado cuadrático (clases ordinales), matriz de
confusión, bootstrap para clases minoritarias. Nunca accuracy sola: el baseline
mayoritario ronda 76%.
κ se reporta **siempre relativo al techo humano**. Un κ de 0.45 contra un techo
de 0.55 es un buen resultado; sin ese contexto invita a lecturas erróneas.
---
## 4. Arquitectura
```
claim
  │
  ├─► [A] Enrutador de check-worthiness
  │        ├─ factual verificable ──────► camino completo
  │        ├─ juicio de valor ──────────► evidencia y contexto, SIN etiqueta
  │        └─ fuera de alcance ─────────► rechazo explicado
  │
  ├─► [B] Recuperación (corte temporal + tier boost)
  │        BM25 + bi-encoder → fusión RRF → (rerank cross-encoder) → top-k
  │
  ├─► [C] NLI por pasaje  (k corridas independientes)
  │        mDeBERTa-XNLI → entailment / contradiction / neutral
  │
  ├─► [D] Agregación (regla explícita y documentada)
  │
  └─► [E] Salida: EVIDENCIA primero; etiqueta como chip subordinado
```
### [A] Enrutador — requisito de seguridad, no mejora opcional
Ejemplo canónico: *"El salario mínimo fue mala práctica"* **no debe recibir
etiqueta**. Es un juicio de valor; no existe evidencia que lo verifique.
Etiquetarlo como "Falso" convierte la herramienta en instrumento político.
Implementación inicial: LLM zero-shot ("¿es esto verificable con datos o es una
valoración?"). Resuelve ~90% de casos sin entrenar nada. Reemplazable después
por un clasificador entrenado (CLEF CheckThat! tarea 1 tiene datos en español).
### [B] Recuperación
- **Híbrido obligatorio:** BM25 es insustituible para cifras, fechas y nombres
  propios, que es lo que abunda en claims. Fusionar con **RRF**, no sumando scores.
- **Sin entrenar el retriever al principio.** Modelos multilingües zero-shot
  (`multilingual-e5-base`, `BGE-m3`) rinden bien. Medir `recall@50` contra BM25
  como baseline antes de considerar fine-tuning.
- **Prefijos E5:** los modelos E5 exigen `"query: "` y `"passage: "`. Sin ellos
  rinden peor y no falla nada visiblemente.
- **Dos pasadas separadas: tier 1 y tier 2.** Así siempre se sabe si hubo
  pronunciamiento oficial, en vez de que la prensa desplace lo oficial en un
  ranking único. Pasada tier 1 vacía = información, no error.
- **Corte temporal obligatorio:** solo evidencia anterior al fact-check, y
  blocklist de dominios verificadores. Sin esto, el sistema *lee la respuesta* y
  la concordancia es circular.
- **Chunking:** 200–400 tokens con solape, respetando límites de párrafo.
  Determina más la calidad que el modelo elegido.
### [C] NLI
Modelo preentrenado, sin fine-tuning, sin GPU. Se corre **k veces**, una por
pasaje recuperado — el pasaje más similar no siempre es el más informativo.
La similitud coseno mide parecido temático; el NLI mide relación lógica.
Traducción de salidas: contradiction → la evidencia desmiente; entailment → la
respalda; neutral → *este pasaje no dice nada al respecto* (≠ "cuestionable").
### [D] Agregación — la decisión de diseño más importante
Opciones: mayoría simple · prioridad a lo informativo (ignorar neutrales salvo
que todo sea neutral) · ponderación por confianza y/o similitud · umbral de
evidencia (≥2 pasajes concordantes).
**Esta regla es editorial disfrazada de hiperparámetro.** "Basta una
contradicción fuerte" produce un sistema agresivo; "exijo mayoría de 3" produce
uno cauteloso. Ninguna es neutral. Va explícita en el README.
Ponderar por **diversidad de fuentes**: tres pasajes del mismo medio son una
sola voz, no tres evidencias.
Salida legítima adicional: **"evidencia mixta / disputada"**. Cuando medios de
distinta línea editorial se contradicen, eso *es* el hallazgo. Forzar veredicto
sería el error.
### [E] Interfaz
- Evidencia arriba, con fuente y fecha; etiqueta abajo, discreta.
- **Distinguir visualmente** un veredicto humano recuperado (v1: claim-matching)
  de uno generado por el sistema (v2). Se ven igual en pantalla y tienen
  responsabilidades distintas.
- Disclaimer permanente, no solo en el README.
- El sistema explica por qué *no* responde cuando abstiene.
---
## 5. Corpus
### Tiers
| Tier | Contenido | Vía de acceso | Frecuencia |
|---|---|---|---|
| 1 | DANE, BanRep, `.gov.co`, DNP, Contraloría, Registraduría | API Socrata, portales, descargas | mensual/trimestral |
| 1b | Gremios (Fedegán, Fedearroz, Fedecafé) | portales | variable |
| 2 | Prensa | RSS / sitemap | diaria |
Los gremios publican datos primarios pero **son parte interesada**: marcar como
"fuente con interés declarado", nunca tier 1 puro.
**Conflicto de interés estructural:** cuando el claim es *sobre el gobierno*, el
gobierno no es fuente primaria neutral. Requiere contrapesos (Contraloría,
multilaterales, academia) o marcado explícito del conflicto en la salida.
### Cómo derivar el registro de fuentes sin ser experto en cada sector
Extraer las URLs citadas por ~500 chequeos de ColombiaCheck y contar dominios
por tema. Sin saber de agricultura, emergen MinAgricultura, Agronet, ICA, ENA
del DANE. **Los datos del recon de la v1 (4,756 chequeos) ya permiten esto.**
Advertencia: hereda el criterio de autoridad de ColombiaCheck a la capa de
recuperación, donde ya no es visible. Auditar la lista y complementar con
fuentes que ellos no citen.
### Construcción
```
raw/         inmutable, nunca se sobrescribe (irreversible: el RSS no tiene histórico)
processed/   normalización, dedup por URL canónica, chunking
index/       embeddings + metadata (dominio, fecha, tier, categoría, URL)
```
Cambiar de modelo de embeddings o de chunking = reconstruir desde `raw/`, sin
volver a recolectar.
**Escala suficiente: 10.000–50.000 pasajes.** No hacen falta millones; hace
falta que los correctos estén.
---
## 6. Gobernanza de datos y permisos
**Paso 1 de la ingesta no es escribir código: es la auditoría de permisos por
dominio.** Tabla versionada en el repo:
`dominio | ¿RSS? | robots.txt | ToS (cláusula IA/minería) | qué guardo | fecha de revisión`
### Hallazgos ya verificados
| Medio | Situación | Decisión |
|---|---|---|
| **El Tiempo** | Aviso legal explícito: prohíbe minería de texto y datos, desarrollo de ML/IA/LLM, datasets archivados y uso comercial. Lista blanca con `Google-Extended: Allow` | **Fuera del corpus.** Solicitar permiso a `notificaciones@eltiempo.com` |
| **Semana** | Sin cláusula anti-IA en robots.txt; `Disallow` solo en rutas técnicas | Candidato. Verificar ToS |
| **Blu Radio** | Bloquea `GPTBot` y `ChatGPT-user`; no menciona otros bots de IA. Sin `/rss` | **Ámbar** (opt-out parcial y reactivo). Consultar antes de ingerir |
`Allow: /rss/` **no** significa "solo RSS": en robots.txt lo no prohibido está
permitido. La ausencia de `Disallow` sobre artículos es el dato relevante.
User-agents a buscar en cada dominio: `Google-Extended`, `GPTBot`, `CCBot`,
`ClaudeBot`, `anthropic-ai`, `PerplexityBot`, `Applebot-Extended`.
### Principios
- robots.txt es el **piso**; los ToS pesan más legalmente.
- Indexar (uso interno) ≠ redistribuir. Ninguno de los dos está autorizado por
  la mera ausencia de bloqueo.
- Opt-out parcial → lectura conservadora. Aprovechar la omisión técnica sería
  cumplir la letra y violar el propósito.
- Nunca suplantar un user-agent permitido.
- Registrar **fecha de revisión**: las políticas cambian.
### Tier 1 opera bajo régimen inverso
La **Ley 1712 de 2014** hace la información pública accesible por defecto y
habilita petición formal con plazos legales. Además, tier 1 **tiene histórico
descargable**: se puede construir hoy, sin esperar acumulación.
### Sesgo estructural inducido
Si los medios con capacidad jurídica son los que ponen cláusulas anti-IA, el
corpus sobrerrepresenta medios sin política de datos. **El corpus no será una
muestra del periodismo colombiano, sino del periodismo colombiano sin
departamento jurídico dedicado a IA.** Declarar así de crudo en limitaciones.
---
## 7. Sesgo político
El caso difícil no son los claims factuales —los medios rara vez contradicen una
cifra del DANE—, sino los valorativos y causales. Por eso el enrutador (§4A)
resuelve la mayor parte del problema antes de que llegue al NLI.
Salvaguardas adicionales:
- **Jerarquía de fuentes** (§5): muchos claims se resuelven contra el dato
  original sin necesidad de prensa.
- **Balance auditado del índice**, con taxonomía externa y citable de
  orientación editorial (Baly et al.), no criterio propio.
- **Transparencia de la disputa**: mostrar quién contradice y quién apoya.
- **Test de simetría** — requisito previo a publicar: claims equivalentes sobre
  figuras de distinto signo político deben recibir tratamiento comparable.
  Estratificar errores por actor y tema.
**Ojo con el falso balance:** la simetría de tratamiento no implica simetría de
veracidad. Incluir "ambos lados" no aplica cuando un lado contradice datos
oficiales verificables.
---
## 8. MLOps
El artefacto versionado **ya no es un clasificador entrenado**, es una
**configuración de recuperación**: modelo de embeddings + chunking + pesos del
híbrido + boost por tier + reranker + regla de agregación + umbrales.
Se envuelve como `mlflow.pyfunc` custom y se registra en el Model Registry.
La app carga `stage=Production` — patrón que la v1 ya implementa cargando desde
el Hub de HF.
### Métricas de experimento
`recall@k` de evidencia · nDCG · proporción tier 1 recuperada · diversidad de
dominios · tasa de abstención · latencia · **κ como secundaria**.
### Disparadores de nueva versión
- Nuevo modelo de embeddings a comparar
- Cambio de chunking o de pesos del híbrido
- **Crecimiento del corpus** (disparador real y continuo; re-indexar ≡ reentrenar)
- Degradación monitoreada: sube la tasa "sin evidencia" o cae la proporción tier 1
### Compuertas de promoción (AND)
1. Métricas de recuperación ≥ champion en **holdout congelado** (DVC)
2. No peor en set prospectivo reciente
3. Calibración no degradada
4. Sin caída significativa en ningún slice (tema, orientación del sujeto, fecha, región)
5. Tasa de abstención en rango (que no haga trampa absteniéndose de todo)
6. **Compuertas éticas:** no promover si cae la diversidad de fuentes ni si sube
   la abstención en claims regionales
7. **Aprobación humana manual** en la transición de stage
Despliegue: shadow mode 2–4 semanas → swap → rollback automático.
### Versionado del índice = requisito de auditabilidad
El corpus **es** el modelo. Cada run registra: hash del índice + commit del
código + `revision` del modelo de HF. Si alguien cuestiona un veredicto de hace
tres meses, debe poder reconstruirse la evidencia que existía entonces.
Añadir o quitar dominios es decisión editorial: va al log de versiones **con
justificación escrita**, no como commit silencioso de datos.
> Riesgo: optimizar configuraciones contra un conjunto derivado de ColombiaCheck
> converge hacia su criterio de evidencia, run tras run — el sesgo entra por la
> puerta de la optimización aunque no se entrene nada. Por eso las compuertas
> incluyen métricas independientes de su criterio.
Es MLOps sin fine-tuning, y está bien: buena parte de los sistemas de IA en
producción hoy orquestan componentes preentrenados en vez de entrenarlos.
---
## 9. Hoja de ruta
Presupuesto: **2–3 h/semana** (~10 h/mes). Partiendo de la v1 completa.
| Fase | Entregable | Horas | Tiempo real |
|---|---|---|---|
| **0** | Auditoría de permisos + cron RSS corriendo | 15–20 | 6–8 sem |
| **1** | Corpus tier 1 (APIs oficiales) + normalización + chunking + índice | 25–35 | 10–14 sem |
| **2** | Claim-matcher sobre corpus existente + evaluación + app | 20–30 | 8–12 sem |
| **3** | Enrutador + NLI + agregación + corte temporal | 30–40 | 12–16 sem |
| **4** | MLflow pyfunc + DVC + monitoreo + compuertas | 25–35 | 10–14 sem |
**Total: 8–12 meses.** Hito publicable en el mes ~6 (fases 0–2).
### Regla de prioridad
**El cron de RSS es lo único con reloj.** El corpus que no empiece a acumularse
hoy no existirá en tres meses; todo lo demás puede diseñarse después. Tier 1 y
el resto no tienen ventana que se cierre.
### Mitigación de fragmentación
Sesiones de 2 h separadas por 7 días gastan 30–40 min en reinmersión.
`NEXT.md` con la siguiente tarea concreta escrita **al cerrar** cada sesión ·
commits pequeños · entorno protegido.
### Ritmo de lectura
Máximo 1 sesión de lectura por cada 3 de construcción. La lectura sin
construcción es la forma más común de que un proyecto muera en fase de diseño.
---
## 10. Lo que la v1 ya aporta
- `acquisition.py` — cosecha de ClaimReview = constructor del corpus semilla
- Recon de 4,756 chequeos → extracción de fuentes citadas sin recolección nueva
- Split congelado (seed 42), bootstrap CI, evaluación única en test
- App Streamlit cargando modelo remoto → un paso de `stage=Production`
- Model Card · Datasheet · Data Statement · CI · pre-commit con `nbstripout`
- Sesgo de selección ya cuantificado: 61.8% de cobertura de ClaimReview
- Criterio demostrado: `rating` (markup estructurado) sobre `verdict` (heurística
  frágil de primer match)
La v2 es una rama de este repo, no un proyecto nuevo.
---
## 11. Decisiones abiertas
1. **Alcance político.** Un sistema que emite juicios sobre claims políticos
   nacionales, construido y desplegado públicamente por un oficial en servicio
   activo, tiene implicaciones que exceden lo técnico (la restricción de
   deliberación política para militares en Colombia es constitucional).
   Opción defendible metodológicamente: **excluir política partidista nacional**
   y centrarse en desinformación no partidista —salud, desastres, fraudes,
   ciencia—, donde el problema técnico es idéntico. **Decisión pendiente y
   consciente**, no omisión.
2. **Demo pública de la v1.** Actualmente en línea, con disclaimer correcto. Un
   pantallazo circula sin él. Decidir explícitamente si sigue activa.
3. Solicitud formal a El Tiempo (y Blu): enviar o descartar.
4. Idioma del repositorio para la documentación v2.
5. Umbral de similitud del claim-matcher y regla de agregación concretas.
---
## 12. Limitaciones a declarar desde el día uno
- No hay *ground truth*; solo concordancia con juicios expertos.
- Sesgo de selección: los verificadores chequean lo viral-dudoso; el sistema no
  sirve para escanear noticias generales.
- Corpus incompleto por opt-out de medios, con sesgo hacia medios sin política
  de datos.
- Abstención asimétrica: menos estadística oficial en temas rurales, economía
  informal, territorios periféricos → "evidencia insuficiente" se concentra donde
  el Estado registra menos.
- Desfase de ritmos: tier 1 mensual vs. prensa diaria → claims recientes se
  resuelven con tier 2.
- La clase "cuestionable" (manipulación por contexto omitido) es la más difícil
  y la peor cubierta; si se colapsa, decirlo como limitación, no como
  simplificación técnica.
- Modelos NLI entrenados sobre XNLI (traducciones) rinden peor con habla
  coloquial colombiana → más "neutral" en ciertos hablantes.
- Artefactos de NLI: las negaciones disparan "contradicción" sin razonamiento.
- Fuera de alcance: análisis longitudinal de cobertura mediática colombiana
  (requiere representatividad que el opt-out impide).
---
## 13. Riesgos
| Riesgo | Mitigación |
|---|---|
| **Alcance.** Tres proyectos disfrazados de uno | Hito publicable en mes 6; fases 3–4 son mejoras, no requisitos |
| **Colisión con la monografía** | La tesis tiene prioridad; solo la fase 0 corre en paralelo |
| **Lavado de autoridad** (pantallazos "la IA dice FALSO") | Disclaimer en UI, evidencia primero, abstención por defecto ante particulares |
| **Transparency theater** | Fricción deliberada: evidencia legible, fuente y fecha visibles |
| **PII en logs** por campo de texto libre | Política de retención + filtro de claims sobre personas no públicas (Ley 1581) |
| **Sobre-ingeniería como coartada** | Horas explícitas reservadas para model card y limitaciones |
| **Memorización en pesos publicados** | Declarar el supuesto en el Datasheet |
---
## 14. Referencias
**Verificación automática**
- Guo, Schlichtkrull & Vlachos (2022). *A Survey on Automated Fact-Checking*. TACL.
- Schlichtkrull, Guo & Vlachos (2023). *AVeriTeC*. NeurIPS.
- Thorne et al. (2018). *FEVER*. NAACL.
- Glockner, Hou & Gurevych (2022). *Missing Counter-Evidence Renders NLP Fact-Checking Unrealistic*. EMNLP.
- Nakov et al. (2021). *Automated Fact-Checking for Assisting Human Fact-Checkers*. IJCAI.
- Hassan et al. (2017). *ClaimBuster*. VLDB.
- Konstantinovskiy et al. (2021). *Toward Automated Factchecking*. Digital Threats.
- Kazemi et al. (2021). *Claim Matching Beyond English*. ACL.
- Barrón-Cedeño et al. CLEF CheckThat! Lab.
**Recuperación**
- Karpukhin et al. (2020). *Dense Passage Retrieval*. EMNLP.
- Thakur et al. (2021). *BEIR*. NeurIPS.
- Cormack et al. (2009). *Reciprocal Rank Fusion*. SIGIR.
- Lin, Nogueira & Yates (2021). *Pretrained Transformers for Text Ranking*.
- Wang et al. (2022). *GPL*. NAACL.
**NLI**
- Bowman et al. (2015). *SNLI*. EMNLP.
- Conneau et al. (2018). *XNLI*. EMNLP.
- Gururangan et al. (2018). *Annotation Artifacts in NLI Data*. NAACL.
**Etiquetas, acuerdo y calibración**
- Cohen (1960, 1968). Coeficientes de acuerdo.
- Aroyo & Welty (2015). *Truth Is a Lie*. AI Magazine.
- Uma et al. (2021). *Learning from Disagreement: A Survey*. JAIR.
- Northcutt, Jiang & Chuang (2021). *Confident Learning*. JAIR.
- Guo et al. (2017). *On Calibration of Modern Neural Networks*. ICML.
- Angelopoulos & Bates (2023). *Conformal Prediction: A Gentle Introduction*.
- Lim (2018). *Checking How Fact-checkers Check*. Research & Politics.
**Fuentes, sesgo mediático y gobernanza**
- Baly et al. (2018). *Predicting Factuality of Reporting and Bias of News Media Sources*. EMNLP.
- Baly et al. (2020). *We Can Detect Your Bias*. EMNLP.
- Longpre et al. (2024). *Consent in Crisis: The Rapid Decline of the AI Data Commons*.
- Mitchell et al. (2019). *Model Cards for Model Reporting*. FAT*.
- Bender & Friedman (2018). *Data Statements for NLP*. TACL.
- Gebru et al. (2021). *Datasheets for Datasets*. CACM.
- Wardle & Derakhshan (2017). *Information Disorder*. Consejo de Europa.
- RFC 9309 — Robots Exclusion Protocol.
- Ley 1712 de 2014 (transparencia) · Ley 1581 de 2012 (habeas data).
**Interacción y confianza**
- Bansal et al. (2021). *Does the Whole Exceed its Parts?*. CHI.
- Buçinca, Malaya & Gajos (2021). *To Trust or to Think*. CSCW.
- Uscinski & Butler (2013). *The Epistemology of Fact Checking*. Critical Review.
**Ingeniería**
- Huyen (2022). *Designing Machine Learning Systems*. O'Reilly.
- Sculley et al. (2015). *Hidden Technical Debt in ML Systems*. NeurIPS.
- Wilson et al. (2017). *Good Enough Practices in Scientific Computing*. PLOS CB.
- Barbaresi (2021). *Trafilatura*. ACL demos.
- Cañete et al. (2020). *Spanish Pre-Trained BERT Model* (BETO). PML4DC.
---
## Principio rector
> El sistema no dice qué es verdad. Muestra qué dicen las fuentes, de qué fecha,
> y con qué grado de acuerdo — y reconoce cuándo no puede pronunciarse.
>
> Lo que distingue un proyecto serio de uno ingenuo no es eliminar el sesgo:
> es medirlo, exponerlo y no pretender neutralidad.
