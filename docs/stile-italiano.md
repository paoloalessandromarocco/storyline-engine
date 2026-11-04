# Guida di stile — Italiano tecnico/marketing per storyline-engine.com

Documento di lavoro, aggiornato nel tempo man mano che arrivano nuovi testi di riferimento. Vive nel repository (non nella memoria di Claude) apposta: niente limiti di dimensione, versionato con git, leggibile e modificabile anche da Paolo direttamente.

## Fonti analizzate finora
- Tesi di laurea magistrale, Politecnico di Torino, Sales Intelligence (IA per marketing e vendite, AA 2021-2022)
- White paper Engineering Group, Media & Communication

## Pattern da imitare (dalla tesi)
La tesi funziona perché:
- **Definisce prima di usare.** Ogni sigla o concetto tecnico viene introdotto con una frase che ne spiega il referente concreto al primo uso, non lasciato implicito ("l'NPS, cioè l'indicatore che misura..." non solo "l'NPS").
- **Esempio concreto subito dopo la definizione astratta.** Non si ferma alla teoria: ogni concetto ha un caso applicativo o un numero a supporto nella frase successiva.
- **Struttura a passi enumerati** quando descrive un processo, invece di prosa continua — rende il flusso tracciabile.
- **Soggetto sempre esplicito e meccanico per i sistemi automatici**: "il modello calcola", "l'algoritmo assegna un punteggio" — mai personificazioni tipo "il sistema capisce" o "il modello pensa".

## Pattern da evitare (dal white paper)
Il white paper è lo spettro opposto, da non replicare:
- Buzzword corporate vaghe senza referente ("sinergie", "ecosistema digitale", "trasformazione abilitante") usate come riempitivo retorico invece che per descrivere un meccanismo reale.
- Frasi che suonano bene ma non sono falsificabili né verificabili — niente numero, niente esempio, niente meccanismo dietro l'affermazione.
- Tono promozionale che sostituisce la spiegazione tecnica con l'aggettivo ("soluzione innovativa e potente" invece di dire cosa fa).

## Regole concrete già applicate al sito (dal feedback diretto di Paolo, 2026-11-04)

1. **Niente abbreviazioni vaghe senza dire a cosa si riferiscono ogni volta.**
   - Evitare: "...per ogni beat della spec..." (quale spec? non è chiaro)
   - Preferire: "...per ogni beat dello `story_spec`..." — nome dell'artefatto reale, non un'abbreviazione generica

2. **Niente personificazione di soggetti non umani/meccanici.**
   - Evitare: "È qui che vive la maggior parte del comportamento effettivo del motore."
   - Preferire: "È qui che agisce il motore: una chiamata esegue l'intero loop..."
   - Un motore non "vive", "agisce" o "funziona" — mai verbi che implicano intenzionalità o esistenza biologica.

3. **Niente giudizio morale/soggettivo su sistemi automatici — usare termini di precisione.**
   - Evitare: "Quanto è buono il judge?" (buono/cattivo è un giudizio morale, fuori luogo per un componente software)
   - Preferire: "Quanto è accurato il judge?" — accurato, efficiente, affidabile: termini misurabili, non valoriali

4. **Qualificare sempre un ruolo automatico come tale alla prima spiegazione estesa.**
   - Evitare: "Gemini come judge VLM per D" (un lettore poco esperto può pensare sia una revisione umana)
   - Preferire: "Gemini come judge automatico (VLM) per D" — la parola "automatico" alla prima occorrenza dettagliata elimina l'ambiguità per il resto del testo

5. **Niente calchi letterali dall'inglese — tradurre il concetto, non la parola.**
   - Evitare: "Una tattica per secchio" (calco di "bucket" nel senso di categoria di difetto)
   - Preferire: "Per ogni categoria di difetto si sceglie una sola tattica"
   - Evitare: "addestra un motore di personaggio" (calco di "character engine" riferito a un prodotto terzo)
   - Preferire: "addestra un modello dedicato al personaggio"
   - Evitare: "Uno schizzo, non una costruzione" (calco di "a sketch, not a build")
   - Preferire: "Una bozza di progetto, non un'implementazione"

6. **Uniformare la terminologia che la pagina stessa ha già stabilito — non introdurre un sinonimo o un'abbreviazione isolata in un punto della pagina.**
   - Esempio: se il resto della pagina usa sempre "file di descrizione", non far ricomparire "spec" nuda in un paragrafo isolato
   - Esempio: "capitolo" per esteso ovunque, mai l'abbreviazione informale "capt."/"capt"
   - Questo vale anche per le frasi spiegate a lungo con un giro di parole quando il resto del testo ha già un termine preciso per lo stesso concetto — es. "contiene ciò che il capitolo 02 chiama il file di configurazione, più X, più Y" invece di elencare esplicitamente ogni campo

## Sessione 2026-11-04 (seconda passata) — dco-engine-tech.html
Altri 5 punti riscritti su richiesta diretta di Paolo, che hanno originato le regole 5 e 6 sopra: "tattica per secchio", la spiegazione della modifica locale mirata (troppo ellittica), il contenuto della riga del database per brand (frase-contenitore poco leggibile, riscritta come elenco con agreement/false-pass rate spiegati inline), la descrizione del prodotto Bria ("motore di personaggio"), e "uno schizzo, non una costruzione".

## Da fare
- Integrare altri documenti di riferimento quando Paolo li fornisce (ha indicato che ne arriveranno altri).
- Estrarre altre coppie prima/dopo concrete man mano che si editano nuove pagine del sito, non solo principi generali.
