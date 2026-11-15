# UBF Köln Timer — Kurzanleitung für den Sonntagsgottesdienst

**Status:** Offline-First-Release-Kandidat. Automatische Tests ersetzen keinen Beamer-Test im Gemeinderaum. GitHub Pages ist nicht erforderlich.

## Einmal vor dem Gottesdienst vorbereiten

1. Den **gesamten** Projektordner auf den Windows-11-Laptop kopieren oder die ZIP vollständig entpacken. Die Unterordner `assets`, `js`, `css` und `scripts` müssen erhalten bleiben.
2. **Node.js 20 oder neuer** muss bereits installiert und über `node` im Windows-PATH erreichbar sein (Installation ggf. vorher mit Internet). Für den Betrieb selbst: **kein Internet, kein `npm install`, kein Python** nötig.
3. Netzteil anschließen. Standby und Bildschirmabschaltung während des Gottesdienstes verhindern. Deckel geöffnet lassen oder die Windows-Einstellungen vorher auf dem konkreten Gerät prüfen.
4. Beamer verbinden; mit **Win + P → Erweitern** zwei getrennte Bildschirme einstellen (nicht „Duplizieren“).

## Sonntag: starten (ohne Terminalbefehle)

1. Im entpackten Projektordner **`Start-Timer.cmd` doppelklicken**. Das schwarze Fenster während des gesamten Gottesdienstes **offen lassen**. Der Launcher prüft Node.js, die benötigten Dateien und den Port und startet den lokalen Server auf **`127.0.0.1:8765`**.
2. Die Steuerung sollte im Standardbrowser öffnen. Falls nicht, selbst öffnen: **http://127.0.0.1:8765/control.html**.
3. **Projektionsfenster öffnen** anklicken. Falls das Pop-up blockiert ist: **http://127.0.0.1:8765/display.html** als zweites Fenster *im selben Browserprofil* öffnen.
4. **Nur das Projektionsfenster** auf den Beamer ziehen und **F11** drücken. Das Steuerfenster bleibt ausschließlich auf dem Laptop.
5. Vor Beginn eine **10-Sekunden-Probe** machen: Starten, Pausieren, Fortsetzen, bei `00:00` stehen lassen, **Willkommensfolie anzeigen**. Danach die benötigte Countdown-Dauer auswählen.

**Wichtig:** „Projektionsfenster verbunden“ zeigt nur ein zweites Browserfenster an, **nicht** den tatsächlich angeschlossenen Beamer. Der Bediener muss den Beamer selbst kontrollieren. Auf Laptop und Beamer denselben Ursprung (`127.0.0.1:8765`), Browser und Browserprofil verwenden. Nicht `localhost`, `file://` oder einen anderen Browser mischen.

## Während des Gottesdienstes

| Schaltfläche | Wirkung |
|---|---|
| 1 / 3 / 5 / 10 Min. | Nur Dauer wählen, Countdown startet noch nicht |
| Countdown starten | Timer auf dem Beamer starten |
| Pausieren / Fortsetzen | Angezeigte Zeit anhalten / fortsetzen |
| Zurücksetzen | Zeit auf gewählte Dauer zurücksetzen; Timer bleibt pausiert |
| Willkommensfolie anzeigen | Zur ursprünglichen Canva-Folie zurückkehren |

Das schwarze Serverfenster offen lassen. Kein zweites Steuerfenster starten. Nicht zwischen Browserprofilen, Hostnamen oder einer späteren GitHub-Pages-Adresse wechseln: Die Fenster würden nicht zuverlässig synchronisieren.

## Schnelle Fehlerbehebung

| Problem | Direktes Vorgehen |
|---|---|
| `node` nicht gefunden | Node.js 20+ **vor** dem Gottesdienst installieren; ohne Node kein lokaler Start |
| „Dateien fehlen“ | Komplette ZIP entpacken, dann im Projektordner erneut `Start-Timer.cmd` ausführen |
| Port 8765 bereits belegt | Vorher gestarteten Timer-/Serverprozess schließen; nicht blind einen anderen Dienst öffnen |
| Browser öffnet nicht automatisch | `http://127.0.0.1:8765/control.html` selbst öffnen; schwarzes Fenster muss laufen |
| Beamer bleibt bei der Willkommensfolie | Beide URLs und dasselbe Browserprofil prüfen, nur **ein** Steuerfenster; nachsehen, ob der Timer auf dem Laptop gestartet ist |
| „Mehrere Steuerfenster“ | Alle bis auf **ein** Steuerfenster schließen; einige Sekunden auf Freigabe warten |
| Speichern blockiert | Fenster möglichst nicht neu laden. Geht der Zustand verloren, Timer bewusst neu starten. Die Anzeige kann ohne gespeicherten Zustand abweichen |
| Countdown/Fenster/Server ausgefallen | Wenn möglich `Start-Timer.cmd` erneut starten, beide Fenster **auf derselben lokalen Adresse** öffnen und Zustand prüfen; bei Unsicherheit Timer bewusst zurücksetzen und neu starten |
| Windows zeigt den Desktop/Benachrichtigungen | Projektionsfenster auf dem Beamer wieder F11; Windows-Benachrichtigungen vorher ausschalten |

**Sofort-Fallback:** Die unveränderte Datei **`assets/welcome.png`** direkt im Bildbetrachter öffnen und auf dem Beamer im Vollbild zeigen. Die Original-Folie ist auch ohne Node.js und Timer benutzbar.

## Abnahmekriterien am echten Beamer (noch NICHT GETESTET)

- [ ] Windows 11 mit **Erweitern**; Steuerung nur auf dem Laptop, Folie nur auf dem Beamer.
- [ ] 16:9-Folie, Ring und Ziffern gut lesbar und ohne Abschneiden bei echter Beamer-Auflösung.
- [ ] Kein Windows-Desktop/Benachrichtigungen sichtbar, F11-Vollbild bleibt stabil.
- [ ] 10-Sekunden-Timer, Pause/Fortsetzen/Zurücksetzen/Willkommen funktionieren ohne Verzögerung oder Fensterfokuswechsel.
- [ ] Bei getrennter Internetverbindung starten beide Fenster vom **laufenden lokalen Server** neu und funktionieren.
- [ ] Einmal Steuerung neu öffnen; laufende Anzeige und Steuerung stimmen überein.
- [ ] Fallback `assets/welcome.png` im Beamer-Vollbild ausprobiert.
- [ ] Mindestens ein kompletter Probelauf ohne Ruhezustand/Display-Unterbrechung.

**Entscheidung:** Vor diesen echten Windows-/Beamer-Abnahmen **kein Live-Gottesdienst-PASS** behaupten. Dieser Stand erstellt/aktiviert weder GitHub Pages noch einen öffentlichen Dienst.
