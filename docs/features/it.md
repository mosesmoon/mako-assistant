# Assistente MAKO — Guida alle funzioni

[English](en.md) · [台灣正體中文](zh_TW.md) · [简体中文](zh_CN.md) · [日本語](ja.md) · [Deutsch](de.md) · [Français](fr.md) · [Español](es.md) · **Italiano** · [ไทย](th.md) · [Tiếng Việt](vi.md) · [Bahasa Melayu](ms.md) · [हिन्दी](hi.md)

L’**Assistente MAKO** è uno strumento grafico per desktop Linux che attiva o disattiva con un clic la **generazione di fotogrammi di MAKO Renderer (Mako FG)** nei tuoi giochi Steam, senza modificare a mano alcun file di configurazione.

## A chi è rivolto

Su Steam Deck, in modalità Gioco, MAKO ha un plugin Decky che permette di regolare tutto durante il gioco. Su un **normale PC desktop o portatile Linux** (ad esempio Arch, Fedora o Ubuntu con KDE Plasma o GNOME), per far usare MAKO a un gioco di solito bisogna fare tutto a mano:

1. Aggiungere `~/.local/bin/mako-launch %command%` alle opzioni di avvio Steam del gioco (Proprietà → Opzioni di avvio) senza rovinare le opzioni già presenti.
2. Scoprire il nome del programma che il gioco **esegue davvero** (molti giochi avviano prima un launcher, e i giochi Unreal Engine eseguono un `*-Shipping.exe`).
3. Creare un profilo di gioco nelle impostazioni di MAKO e inserire i processi associati corretti (`active_in`).
4. Ripetere tutto quando un aggiornamento del gioco cambia il percorso o il nome dell’eseguibile.
5. Avviare il gioco senza sapere con certezza se la generazione di fotogrammi funziona davvero.

L’Assistente MAKO riunisce questi passaggi in un solo pulsante e, mentre un gioco è in esecuzione, mostra quali funzioni di MAKO sono **effettivamente** attive.

## Prima di iniziare

> ⚠ **L’Assistente MAKO non include MAKO Renderer e non lo installa al posto tuo.** Si limita a gestire le impostazioni di MAKO.

Per prima cosa:

1. **Installa MAKO Renderer (versione standalone)** seguendo le istruzioni di installazione di MAKO. Al termine deve esistere `~/.local/bin/mako-launch`.
2. **Apri MAKO UI una volta** per creare le impostazioni predefinite. In questo modo vengono creati `~/.config/mako-render/conf.toml` e il profilo predefinito `mako`. Ogni profilo di gioco creato dall’Assistente MAKO è una copia di questo profilo predefinito.
3. **Installa Steam.** Sono supportati il pacchetto nativo (`~/.local/share/Steam`, `~/.steam`) e le versioni Flatpak e Snap.

Assicurati di aver completato tutto quanto sopra e che MAKO funzioni prima di installare Mako FG in un gioco con l’Assistente MAKO.

Facoltativo: **Decky Loader**. Con Decky Loader le opzioni di avvio si possono applicare in tempo reale mentre Steam è aperto, senza chiuderlo (vedi «Come vengono scritte le opzioni di avvio» più sotto).

## Funzioni

### 1. Scansione automatica della libreria Steam

- Al primo avvio vengono scansionate **tutte** le tue librerie Steam (comprese quelle su altri dischi). In seguito puoi fare clic su «⟳ Ripeti la scansione dei giochi Steam».
- Gli strumenti come Proton e Steam Linux Runtime vengono esclusi, così vengono elencati solo i giochi.
- I nomi dei giochi compaiono con il nome localizzato ufficiale di Steam nella lingua dell’interfaccia e sono ordinati secondo le convenzioni di quella lingua.
- Per ogni gioco vengono mostrati la copertina, le opzioni di avvio attuali, il profilo MAKO e i percorsi dell’eseguibile rilevati.

### 2. «Installa Mako FG» con un clic

Quando fai clic su «Installa Mako FG», lo strumento:

- **Aggiunge l’opzione di avvio** `~/.local/bin/mako-launch %command%` alle opzioni di avvio Steam del gioco e **mantiene quelle già presenti**. Ad esempio `FOO=1 %command% -dx11` diventa `FOO=1 ~/.local/bin/mako-launch %command% -dx11`.
- **Rileva il vero eseguibile del gioco** dalle informazioni dell’applicazione di Steam. Gestisce i launcher (in quel caso cerca il vero programma del gioco nella cartella di installazione) e i `*-Shipping.exe` di Unreal Engine, e ignora i comuni programmi ausiliari.
- **Crea un profilo di gioco MAKO**: copia il profilo predefinito `mako` in un profilo dedicato al gioco in `conf.toml` e scrive i metadati del profilo di MAKO. **Sia MAKO UI sia il plugin Decky vedono questo profilo e possono modificarlo direttamente.**
- **Evita associazioni duplicate**: se anche il profilo predefinito `mako` è associato all’eseguibile di questo gioco, l’eseguibile viene rimosso da `mako`, così il gioco usa solo il proprio profilo. Se il profilo di un altro gioco è associato allo stesso eseguibile, ricevi un avviso, ma non viene cambiato nulla automaticamente.

### 3. Come vengono scritte le opzioni di avvio

Steam legge le opzioni di avvio solo all’avvio e sovrascrive il proprio file di configurazione alla chiusura. Perché Steam non sovrascriva la tua modifica, l’Assistente MAKO sceglie il metodo di scrittura in base allo stato di Steam e mostra questo stato nella finestra:

| Stato di Steam | Metodo di scrittura |
|---|---|
| Chiuso | Modifica direttamente il `localconfig.vdf` di Steam (dopo averne fatto un backup) |
| Aperto, e il client Steam è raggiungibile (richiede Decky Loader) | Applica la modifica in tempo reale tramite il client Steam, senza riavviare Steam |
| Aperto, ma il client non è raggiungibile | Chiede se chiudere Steam → applica la modifica → riavvia Steam |

### 4. Rimuovi

- «Rimuovi» toglie solo `mako-launch` dalle opzioni di avvio e lascia invariate le altre opzioni.
- Le impostazioni MAKO del gioco vengono **mantenute per impostazione predefinita**, così puoi riutilizzarle se lo reinstalli in seguito. Spunta «Rimuovi anche le impostazioni di MAKO Renderer del gioco» per eliminarle insieme.

### 5. Importare impostazioni esistenti

Se in passato avevi già aggiunto `mako-launch` a un gioco a mano, quel gioco mostra il pulsante «Importa impostazioni». Facendo clic viene creato il profilo MAKO del gioco, che da quel momento è incluso nell’aggiornamento automatico dei percorsi.

### 6. Aggiornamento automatico dei percorsi dopo gli aggiornamenti dei giochi

- A ogni nuova scansione, lo strumento rileva di nuovo gli eseguibili dei giochi **installati con questo strumento**. Se un aggiornamento ha spostato o rinominato l’eseguibile, i processi associati di MAKO vengono aggiornati automaticamente e la modifica viene riportata nell’area del registro.
- I processi associati che hai **aggiunto a mano** in MAKO UI vengono mantenuti.
- Se hai eliminato il profilo di un gioco in MAKO UI, lo strumento rispetta la tua scelta e non lo ricrea.
- Se una libreria è temporaneamente non disponibile (ad esempio un disco esterno non collegato), le impostazioni di quei giochi restano invariate.

### 7. Avviare i giochi dall’elenco

Ogni riga ha un pulsante «▶ Avvia» che avvia il gioco tramite Steam. Mentre il gioco è in esecuzione, il pulsante mostra «In esecuzione».

### 8. Visualizzazione in tempo reale delle funzioni MAKO effettivamente in uso

La colonna «Funzioni MAKO attive» si aggiorna ogni 3 secondi. Mostra ciò che MAKO ha **effettivamente applicato** nel gioco, non ciò che è scritto nel file di configurazione:

- **Generazione di fotogrammi**: moltiplicatore fisso (ad esempio ×2) o modalità adattiva (FPS obiettivo e moltiplicatore massimo), scala Flow e modalità prestazioni.
- **Scalatura**: metodo e risoluzione (ad esempio 1280×720 → 2560×1440), supersampling.
- **Altri layer**: vkBasalt, Zink, audio ALSA.
- **Modifiche in sospeso**, come «riavvio del gioco necessario» o «ricostruzione della swapchain necessaria», e gli errori segnalati da MAKO.

Se un gioco ha Mako FG installato ma MAKO non è stato davvero caricato, viene indicato anche questo, per aiutarti a individuare il problema.

### 9. Overlay all’avvio di un gioco

Se l’Assistente MAKO è aperto quando avvii un gioco, non appena rileva che MAKO è attivo nel gioco mostra le funzioni MAKO attive nell’angolo in basso a destra per circa 10 secondi, poi le fa sparire in dissolvenza:

- Compare una volta per avvio, non prende mai il focus di tastiera o mouse, e i clic del mouse lo attraversano.
- Può comparire sopra i giochi Proton a schermo intero.
- Se un gioco con Mako FG installato non ha ancora caricato MAKO 90 secondi dopo l’avvio, viene mostrato invece un avviso.
- Puoi disattivarlo con la casella «Overlay all'avvio» nella barra degli strumenti.

### 10. Ricerca e filtri

- Cerca per nome del gioco (in qualsiasi lingua) o per App ID.
- Filtri: tutti i giochi, Mako FG installato, Mako FG non installato, solo impostazioni MAKO, in esecuzione.

### 11. Dodici lingue dell’interfaccia

台灣正體中文, 简体中文, English, 日本語, Deutsch, Français, Español, Italiano, ไทย, Tiếng Việt, Bahasa Melayu, हिन्दी.

Al primo avvio la lingua segue quella di sistema. Puoi cambiarla in qualsiasi momento in alto a destra; la modifica ha effetto subito e viene ricordata.

### 12. Progettato per la sicurezza

- Prima di ogni modifica viene fatto un backup di `conf.toml` e del `localconfig.vdf` di Steam (`*.mako-assistant.bak`).
- Dopo aver scritto `conf.toml`, lo strumento lo verifica con `mako-cli validate`. Se MAKO lo rifiuta, il file originale viene ripristinato automaticamente.
- `localconfig.vdf` non viene mai modificato direttamente mentre Steam è aperto.

## Installare l’Assistente MAKO

**AppImage (consigliato)**: Python e Qt sono inclusi, non serve installare altro.

```bash
chmod +x MAKO_Assistant-*-x86_64.AppImage
./MAKO_Assistant-*-x86_64.AppImage
```

**Dal codice sorgente**: richiede Python 3.11 o successivo e PyQt6 (Arch: `sudo pacman -S python-pyqt6`).

```bash
./mako-assistant    # avvio diretto
./install.sh        # installa in ~/.local/share/mako-assistant e aggiunge una voce al menu delle applicazioni
```

## Limitazioni note

- **L’overlay non compare nella modalità Gioco di Steam Deck (gamescope).** Su Steam Deck usa invece il plugin Decky di MAKO.
- I giochi in schermo intero esclusivo con Wayland nativo possono coprire l’overlay.
- Le opzioni di avvio si possono cambiare in tempo reale solo tramite la porta del client Steam aperta da Decky Loader (8080). Senza Decky, chiudi Steam prima di applicare, oppure lascia che sia lo strumento a chiudere e riavviare Steam.
- La visualizzazione delle funzioni effettivamente in uso e i metadati dei profili MAKO vengono letti nel formato della versione attuale di MAKO. Dopo un aggiornamento importante di MAKO o di Steam potrebbero temporaneamente non comparire (vedrai «—»), ma installazione e rimozione continuano a funzionare.
- In tailandese, vietnamita, malese e hindi i menu contestuali sono in inglese (Qt non ha traduzioni ufficiali per queste lingue). Steam non ha nomi dei giochi in malese né in hindi, quindi queste due lingue mostrano sempre i nomi originali.
- Viene conservato solo il backup più recente.

## Dove vengono salvati i dati

| Posizione | Contenuto |
|---|---|
| `~/.config/mako-assistant/state.json` | Stato dell’Assistente MAKO: cache dell’elenco dei giochi, giochi installati con questo strumento, lingua dell’interfaccia, impostazione dell’overlay |
| `~/.config/mako-render/conf.toml` | Impostazioni di MAKO Renderer (profili dei giochi) |
| `~/.config/mako-render/profile-metadata.json` | Metadati dei profili MAKO (nomi dei giochi, App ID di Steam) |
| `<Steam>/userdata/<ID utente>/config/localconfig.vdf` | Opzioni di avvio di Steam |
