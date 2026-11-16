# UBF Köln Beamer-Timer — Bedienkarte für die Windows-11-Probe

**NUR TESTBETRIEB — SONNTAGSGOTTESDIENST: NO_GO.** Keine Installation,
Veröffentlichung oder Vor-Ort-Abnahme wurde durch dieses Dokument ausgeführt.
Diese Karte begleitet die
[acht verbindlichen Tests W01–W08](./PHYSICAL_ACCEPTANCE_WINDOWS11.md).
Ergebnisse müssen von den Personen **am realen Laptop und Beamer** stammen.

## Vor dem Test

1. **Nativen Build tatsächlich vorhanden?** Der Entwurf hat keinen Installer.
   Nur mit freigegebenem lokalem Entwicklungs-Build testen
   (Buildanleitung in [NATIVE_WINDOWS.md](./NATIVE_WINDOWS.md)).
   Ohne nativen Build: **NOT_TESTED**, keinen Browserlauf als native Abnahme werten.
2. Beamer verbinden, **Win + P → Erweitern** wählen; unter
   **Einstellungen → System → Bildschirm** kontrollieren, dass das
   Laptop-Panel die *Hauptanzeige* bleibt. Bildschirmnummern, Auflösung,
   Skalierung und Anordnung notieren.
3. Netzteil anschließen, Benachrichtigungen unterdrücken, Ruhezustand
   während der Probe verhindern. Eine zweite Person schaut ausschließlich
   auf das Zuschauerbild des Beamers.
4. PowerPoint-Datei und Canva-Präsentation (falls vorgesehen) vorher
   bereithalten. Canva benötigt möglicherweise Netzwerk; die
   Offlineprüfung W02 betrifft den **nativen Timer**, nicht Canva.

## Sichere Abfolge am Bedienplatz

| Phase | Bedienhandlung | Muss sichtbar sein |
| --- | --- | --- |
| Projektionsstart | Im nativen Controller **Auf Beamer projizieren** | Nur Welcome-Folie auf dem Beamer, nur Steuerung auf dem Laptop |
| Timertest | 00:10 wählen, starten, pausieren, fortsetzen und 00:00 abwarten | Countdown und Ring synchron, keine Anzeige privater Steuerelemente |
| Probe PowerPoint | Zielmonitor in PowerPoint **Bildschirmpräsentation → Monitore** prüfen; Referentenansicht und Publikumsansicht unterscheiden | Publikum sieht niemals Notizen/Steuerung |
| Übergabe | **Beamer freigeben**; anschließend das separat vorbereitete Publikumsfenster nutzen | Timerfenster geschlossen; nächstes Programm startet **nicht automatisch** |
| Probe Canva | **Präsentationsansicht** und **Vollbild** getrennt testen; Teilnehmenden- und Präsentationsfenster auseinanderhalten | Teilnehmendenfenster auf dem Beamer; Notizen nur auf dem Laptop |
| Rückweg | Timer erneut **Auf Beamer projizieren**; bei Störung manuell auf getesteten Fallback wechseln | Steuerung und Countdown bleiben erhalten |

**Handoff-Reihenfolge für W05/W06 separat vergleichen:** Eine bereits
gestartete Präsentation kann den Timer verdecken; eine erst nach
`Beamer freigeben` gestartete Präsentation kann kurz den Desktop zeigen.
Beide Fälle aus dem Zuschauerraum beobachten. **Nichts davon ist als
nahtlos zertifiziert.** Weder PowerPoint noch Canva werden vom Timer
automatisch gestartet oder fokussiert.

## Sofortiger Testabbruch

Bei falschem Bildschirm, privater Referentenansicht im Publikumsbild,
Steuerungs-/Fokusverlust, unerwartetem Countdown-Reset, Desktop-/Taskleisten-
Einblendung oder Beamerabzug mit Laptop-Übernahme: **FAIL**, Test stoppen,
beobachteten Ablauf notieren. Keine spontane Reparatur während eines
Gottesdienstes.

**Rückfallweg ist nicht identisch mit nativer Projektion:** Die bisherige
`Start-Timer.cmd`-Variante braucht Node.js 20+ und einen vollständig
entpackten Projektordner. Sie startet einen lokalen Browser-Controller;
das Display muss auf den Beamer gezogen und mit F11 maximiert werden.
Alternativ kann die unveränderte `assets/welcome.png` als statisches
Bild genutzt werden. W08 erst PASS setzen, wenn der tatsächlich
vor Ort verfügbare Rückfallweg real vorgeführt wurde.

## Ergebnis erfassen

In [PHYSICAL_ACCEPTANCE_WINDOWS11.md](./PHYSICAL_ACCEPTANCE_WINDOWS11.md)
für **jeden** Test W01–W08 `PASS`, `FAIL` oder `NOT_TESTED`
mit Beobachtung, Systemkonfiguration und Build-SHA erfassen.
Ein anderer CI-PASS ersetzt keinen dieser acht Vor-Ort-Tests.
**Sonntagseinsatz bleibt NO_GO**, solange irgendein Pflichttest nicht
als tatsächlich bestanden dokumentiert ist.

Weitere offizielle Hinweise:
[Microsoft: PowerPoint auf zwei Bildschirmen](https://support.microsoft.com/en-us/powerpoint/present-on-multiple-monitors-and-view-speaker-notes-privately)
und
[Canva: Präsentationsmodi](https://www.canva.com/de_de/help/presentation-modes/).


## Im lokalen Probe-ZIP

1. `BUILD_MANIFEST.json`-Quell-SHA mit dem genehmigten GitHub-Commit
   **unabhängig** vergleichen. Alle enthaltenen Dateien entpacken.
2. `Start-Probe.cmd` führt SHA-256-Prüfungen durch; bei gültigen Dateien
   und nur nach manueller Eingabe von **PROBE** startet die unsignierte EXE.
   Windows-Sicherheitsmeldungen nicht unbesehen umgehen.
3. `ABNAHME_W01-W08.html` im Browser offline öffnen. Alle acht Tests
   stehen zunächst **NOT_TESTED**. Metadaten und beobachtete PASS/FAIL
   eintragen; W05 PowerPoint (vorher/nachher) und W06 Canva
   (Vollbild/Präsentationsansicht) gesondert dokumentieren.
   **W05/W06 PASS** ist erst nach Notizen zu **beiden** Varianten wählbar.
   Falls ein Teilnachweis entfernt wird, springt der Status auf NOT_TESTED.
   Importierte alte PASS-Werte bleiben als historische Einträge erhalten,
   werden bei fehlenden Teilnachweisen aber sichtbar als unvollständig markiert.
4. Bei einer späteren Probe desselben Builds können die alten lokalen
   Ergebnisse wieder angezeigt werden. Das Formular markiert die
   **wiederhergestellte frühere Probe** sichtbar. Für den neuen Testtermin
   **Neue Probe beginnen** wählen und den Reset bestätigen; alte Ergebnisse
   vorher als JSON sichern. **Alte PASS-Angaben niemals wiederverwenden.**
5. Zum Ende die Ergebnisdatei über **Ergebnisse als JSON sichern**
   exportieren. Eine Datei auf einem autorisierten lokalen Datenträger
   aufbewahren. Das Formular übermittelt keine Daten und setzt
   niemals die Live-Freigabe.
