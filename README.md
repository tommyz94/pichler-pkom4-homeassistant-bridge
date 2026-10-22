# Pichler PKOM4 Home Assistant Bridge

Integrazione Home Assistant per leggere e comandare **Pichler PKOM⁴ tramite la rete locale**, usando il gateway Micro Nabto già impiegato da PICHLERluft.

Non richiede password cloud, adattatori Modbus o un servizio sul Mac. Il collegamento avviene direttamente tra Home Assistant e la macchina su UDP 5570. L'email già autorizzata sul dispositivo identifica la sessione locale.

**Versione iniziale 0.1.0.** Letture e scritture sono state provate su una PKOM4 con boiler e gateway modello Nabto 1030. L'integrazione non è ancora stata installata su un Home Assistant di produzione; i test del framework sono eseguiti con Home Assistant 2026.1.0. Non è un prodotto ufficiale Pichler.

## Controlli, come nell'app

| Menu PICHLERluft | Entità Home Assistant | Funzioni |
|---|---|---|
| Modalità | Selettore modalità | Spento, Estate, Inverno, Automatico, Vacanza |
| Vacanza | Data fine vacanza + setpoint ambiente | Impostare prima la data; poi selezionare Vacanza |
| Ventilazione | Selettore ventilazione | Automatico, livelli 1–4 |
| Temperatura | Numero setpoint ambiente | 10–30 °C, passo 0,5 °C |
| Raffreddare | Numero setpoint raffrescamento | 15–40 °C, passo 0,5 °C |
| Consenso raffrescamento | Selettore | No, Sì, Eco |
| Acqua calda | Numero setpoint boiler | 20–75 °C, passo 0,5 °C |
| Riscaldamento elettrico | Interruttore | Consenso al riscaldamento elettrico del boiler |
| Riscaldamento rapido | Interruttore | Boost acqua calda |

Il setpoint ambiente è condiviso con la temperatura della modalità Vacanza, come nel dispositivo. L'opzione Eco è presente nell'app Android; la versione iOS può presentare un'interfaccia diversa.

Le impostazioni vengono scritte **solo quando si aziona un controllo**, anche da un'automazione. Nessuna scrittura avviene alla configurazione, all'avvio o durante il polling. L'integrazione controlla intervalli e passi, verifica la risposta della macchina e rilegge lo stato senza aggiornarlo in modo ottimistico. Non ripete automaticamente una scrittura fallita. Un gruppo di impostazioni viene validato prima dell'invio, ma è applicato tramite RPC separati, come nell'app: non è una transazione atomica.

### Risultato delle prove reali

- Confermati da rilettura: modalità Spento/Estate/Inverno/Automatico/Vacanza, data vacanza, livelli manuali 1–4, i tre setpoint di temperatura, consenso raffrescamento No/Sì/Eco, riscaldamento elettrico e boost.
- Tutte le impostazioni modificate durante le prove sono state ripristinate e rilette.
- Le prove verificano l'accettazione dei comandi e i registri risultanti, non un ciclo termico completo o le prestazioni di compressori e resistenze.
- **Ventilazione automatica:** sulla macchina provata il comando viene accettato, ma il registro continua a riportare l'ultimo livello manuale. È stato osservato anche dopo aver comandato Automatico dall'app ufficiale. Il bridge mantiene l'opzione e segnala il mancato riscontro; non inventa uno stato "Automatico". Il comportamento su altri firmware resta da verificare.

Non sono inclusi reset di contatori, parametri di installazione, gestione degli account cloud o programmazione settimanale delle versioni dell'app che la espongono. Il mirror copre i controlli PKOM4 dei menu confrontati, non qualsiasi funzione di qualsiasi versione PICHLERluft.

## Misure disponibili

21 sensori: temperature ambiente/esterna/mandata/ripresa/espulsione e boiler centro/fondo, due portate d'aria, energia cumulata, potenze dei compressori e della ventilazione, potenza totale calcolata, livelli ventilazione, setpoint, modalità grezza, codice anomalia e parola di stato.

Aggiornamento ogni 30 secondi, con sessione persistente. Se il dispositivo non risponde, le entità diventano non disponibili e la lettura successiva tenta una nuova sessione. Il contatore dei filtri non è esposto: la sua conversione in giorni non è stata confermata.

## Installazione tramite HACS

Requisiti: Home Assistant **2026.1.0 o successivo**, HACS e accesso LAN al gateway PKOM4. Non è compatibile con il solo protocollo Nabto Edge 5.

1. In HACS aprire **Repository personalizzati**.
2. Aggiungere `https://github.com/tommyz94/pichler-pkom4-home-assistant-bridge`, categoria **Integrazione**.
3. Scaricare **Pichler PKOM4 Local** e riavviare Home Assistant.
4. In **Impostazioni → Dispositivi e servizi → Aggiungi integrazione**, cercare **Pichler PKOM4 Local**.
5. Inserire IP locale della macchina, ID Nabto completo ed email già abilitata nell'app.

Il numero visibile nell'app potrebbe essere abbreviato con puntini: serve l'ID completo. Il flusso verifica identità e modello del dispositivo prima di creare le entità. È consigliata una prenotazione DHCP per mantenere stabile l'IP.

In alternativa, copiare `custom_components/pichler_pkom4_local` in `/config/custom_components/` e riavviare. Nessuna modifica a `configuration.yaml` è necessaria.

## Privacy e rete

La repository contiene codice, metadati del protocollo e test sintetici. Non contiene configurazioni personali, ID di dispositivi reali, email di account, password, certificati, APK o acquisizioni di rete.

IP, ID Nabto ed email vengono inseriti dal proprietario nell'interfaccia di Home Assistant e conservati **solo nella sua configurazione Home Assistant**, come per le altre integrazioni. Non sono inviati a GitHub o a un servizio di questo progetto. Il bridge non contatta i server cloud Pichler/LS Control/Nabto. HACS e Home Assistant scaricano normalmente codice e dipendenze durante l'installazione.

La modalità locale Micro Nabto qui usata identifica il client tramite email e usa traffico locale non cifrato con checksum. Utilizzarla su una LAN fidata; non esporre UDP 5570 a Internet. Il bridge non cambia protezioni, account o impostazioni di rete del dispositivo.

## Sviluppo e pubblicazione

Repository prevista: `tommyz94/pichler-pkom4-home-assistant-bridge`.

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

I test automatici usano solo dati sintetici e trasporti simulati: non inviano comandi a una macchina reale. Per contribuire, non inserire credenziali o dump personali nei test, nelle issue o nei log.

Dopo aver creato la repository vuota su GitHub, pubblicare il branch locale:

```sh
git push -u origin HEAD:main
```

Il remote `origin` è già impostato al percorso indicato. Nessun push viene eseguito dagli script del progetto. HACS può usare il branch predefinito anche senza release. Per offrire una versione selezionabile, creare una release GitHub `v0.1.0`, coerente con `manifest.json` (un solo tag Git non equivale a una release GitHub). Non occorre caricare uno ZIP.

Licenza **GPL-3.0-or-later**. Il framing Micro Nabto è fornito da [GenvexNabto](https://github.com/superrob/genvexnabto); i mapping sono specifici per PKOM4. Vedere [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
