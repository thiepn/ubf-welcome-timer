# UBF Köln Beamer-Timer — physische Windows-11-Abnahme

**Status: NICHT DURCHGEFÜHRT / NO_GO für den Sonntagsgottesdienst.**
Dieses Protokoll ist eine Vorlage. GitHub Actions auf Windows Server 2022
sind **kein** Ersatz für den echten Beamer-Test. Keine Freigabe, Veröffentlichung,
Installation oder Änderung an der Kirche wurde vorgenommen.

## Prüfaufbau dokumentieren (vor Ort)

- Datum / verantwortliche Person: **NOT_TESTED**
- Windows-11-Version, Laptop-Modell: **NOT_TESTED**
- Beamermodell und Anschluss (z. B. HDMI): **NOT_TESTED**
- Windows-Hauptbildschirm (muss das Laptop-Panel sein): **NOT_TESTED**
- Beamer-Auflösung und Windows-Skalierung auf beiden Bildschirmen: **NOT_TESTED**
- App-Quellstand / getestete Build-SHA: **NOT_TESTED**
- PowerPoint-Version und Canva-Browser: **NOT_TESTED**

**Vorbedingungen:** Stromversorgung, Benachrichtigungen stumm, Ruhezustand
deaktiviert; **Win + P → Erweitern**, nicht Duplizieren. Unter
*Einstellungen → System → Bildschirm* muss das Laptop-Panel der
**Hauptbildschirm** sein. Den nativen Entwurfsstand ausschließlich in einem
nicht-öffentlichen Probelauf testen. Nicht im Gottesdienst erproben.

**Zugangshürde:** Für den nativen Entwurf gibt es **keine freigegebene
Windows-Installationsdatei**. Ein GitHub-Actions-PASS und der Browser-Fallback
installieren die native App nicht. Das lokale Probe-ZIP wird **auf einem
vertrauenswürdigen Windows-x64-Buildrechner** aus einem genehmigten Quell-Commit
erzeugt (Node.js 20+, Rust MSVC, Microsoft C++ Build Tools;
[NATIVE_WINDOWS.md](./NATIVE_WINDOWS.md)). Auf dem **autorisierten
Windows-11-x64-Kirchentestgerät** werden zum Starten der entpackten Probe
weder Node.js noch Rust noch C++ Build Tools benötigt; Windows WebView2
muss verfügbar sein. EXE und SHA nur aus der unabhängig genehmigten Quelle
übernehmen; die enthaltenen Hashes ersetzen keine digitale Signatur.
Ohne vorhandenes und lauffähiges Probe-ZIP W01–W07 **NOT_TESTED** lassen,
nicht als PASS oder als App-FAIL auslegen. Hier wurde keine Probe auf
dem Kirchenlaptop durchgeführt.

**Kurzablauf für die Person am Laptop:** [HANDOFF_OPERATOR_CARD_DE.md](./HANDOFF_OPERATOR_CARD_DE.md).
Vor Testbeginn nach Möglichkeit eine zweite Person am Zuschauerplatz
aufstellen; sie beurteilt nur das **echte Projektorbild**, nicht die Laptop-Vorschau.

## Acht verbindliche Abnahmetests

| ID | Durchführung | PASS-Kriterium | Beobachtung |
| --- | --- | --- | --- |
| W01 | Nativen Timer auf Windows 11 starten, Beamer erweitern, **Auf Beamer projizieren**; direkt danach per Tastatur den Laptop-Timer bedienen | Steuerung ausschließlich und weiter fokussiert auf dem Laptop; Welcome-Folie ausschließlich und vollflächig auf dem Beamer; kein F11 oder Fensterziehen | NOT_TESTED |
| W02 | Vorher Internetverbindung trennen; App neu öffnen, Projektion starten | Original-Canva-Folie und Timer funktionieren vollständig offline; kein lokaler Node-Server nötig | NOT_TESTED |
| W03 | 10-Sekunden-Timer starten, pausieren, fortsetzen, bis 00:00, dann Willkommen | Beamer und Steuerung stimmen überein; keine abgeschnittenen Zahlen/Progress-Ringe; Countdown bleibt bei 00:00 | NOT_TESTED |
| W04 | Bei laufender Projektion **Beamer freigeben**; anschließend **Auf Beamer projizieren**; jeweils Laptop-Fokus prüfen | Nur das Beamerfenster schließt/öffnet; Steuerung bleibt per Tastatur bedienbar und laufender Timer bleibt erhalten; keine falschen Zustandsanzeigen | NOT_TESTED |
| W05 | PowerPoint-Folien auf dem richtigen **externen** Präsentationsmonitor vorbereiten; am Ende des Countdowns freigeben und PowerPoint zeigen | Keine verkehrte Presenter-/Audience-Ansicht, keine Laptop-Steuerung auf dem Beamer, keine unerwünschte Desktop-Einblendung; Verzögerung dokumentieren | NOT_TESTED |
| W06 | Canva **Vollbild** und **Präsentationsansicht** separat prüfen; dann vom Timer an die Audience-Folie übergeben | Nur Audience-Inhalt auf dem Beamer; der Timer verdeckt Canva nach Freigabe nicht; keine unbeabsichtigten Fenster oder Desktop-Einblendungen | NOT_TESTED |
| W07 | Bei aktivem Timer Beamerkabel abziehen; danach wieder verbinden und neu projizieren | Projektion übernimmt niemals das Laptop-Panel; Steuerung bleibt bedienbar; Wiederverbinden erfordert keine manuelle Fensterrettung | NOT_TESTED |
| W08 | Notfallweg prüfen: Timer beenden / nativen Modus verlassen und **assets/welcome.png** oder unveränderten Browser-Fallback verwenden | Willkommensfolie lässt sich ohne native Projektion anzeigen; kein Absturz, keine vorhandenen Dateien verändert | NOT_TESTED |

Optional bei vorhandenem Aufbau: Beamer links vom Laptop (negative
Monitor-Koordinaten), verschiedene Windows-Skalierungsfaktoren (100/125/150 %),
Auflösungswechsel und Projektor-Aus-/Einschalten prüfen. Nur beobachtete
Ergebnisse als PASS markieren; nicht mögliche Fälle bleiben NOT_TESTED.

## Nachweise und Ergebnisprotokoll (erst vor Ort ausfüllen)

Die tatsächliche Ausführung dokumentieren, nicht CI-Ergebnisse übertragen.
Das Offline-Formular kann Ergebnisse einer **früheren Probe desselben Builds**
lokal wiederherstellen und kennzeichnet diese jetzt ausdrücklich. Vor einem
neuen Testtermin **Neue Probe beginnen** wählen und den Reset bestätigen;
vorhandene Beobachtungen vorher als JSON exportieren. Niemals alte PASS-Werte
als neue Vor-Ort-Ergebnisse übernehmen.
Je Test W01–W08 den Zustand **PASS / FAIL / NOT_TESTED** und eine knappe
Beobachtung eintragen. Bei FAIL einen reproduzierbaren Ablauf notieren und
den Live-Einsatz stoppen. Ein fehlender Build / fehlender Beamer ist
**NOT_TESTED**, kein PASS und kein beobachteter App-Defekt.

| Feld | Eintrag durch Testperson |
| --- | --- |
| Exakte getestete Commit-SHA / Build-Quelle | NOT_TESTED |
| Testzeitraum, verantwortliche Person | NOT_TESTED |
| Beamer- und Laptop-Modell, HDMI-/Adapterkette | NOT_TESTED |
| Display 1/2: Hauptanzeige, Auflösung, Skalierung, Anordnung | NOT_TESTED |
| W01 Status / Beobachtung | NOT_TESTED |
| W02 Status / Beobachtung | NOT_TESTED |
| W03 Status / Beobachtung | NOT_TESTED |
| W04 Status / Beobachtung | NOT_TESTED |
| W05 PowerPoint: Status / unerwünschte Sichtbarkeit / Umschaltverhalten | NOT_TESTED |
| W06 Canva: Status / unerwünschte Sichtbarkeit / Umschaltverhalten | NOT_TESTED |
| W07 Kabel-/Beamertrennung: Status / Laptop-Übernahme | NOT_TESTED |
| W08 Rückfallweg: Status / tatsächlich verfügbarer Startweg | NOT_TESTED |
| Zeitliche Unterbrechung / Desktop-Anzeige beim Übergang | NOT_TESTED |
| Beobachtungen aus Zuschauerperspektive (Foto/Video nur nach Zustimmung) | NOT_TESTED |
| Verantwortliche Entscheidung für Testbetrieb / Live-Einsatz | NO_GO |

**Messregel bei W05/W06:** Aus dem Zuschauerraum beobachten und
dokumentieren, ob Desktop, Taskleiste, private Referentenansicht,
Benachrichtigungen oder ein falsches Fenster sichtbar werden. Eine
„erfolgreiche“ Übergabe darf nicht bloß daraus abgeleitet werden, dass
nachträglich die korrekte Folie erscheint. Bei sichtbarer Störung FAIL
notieren; nicht durch einen pauschalen CI-PASS ersetzen. Nicht heimlich
Teilnehmende aufnehmen; wenn kein Video möglich ist, schriftliche
Beobachtung durch die zweite Testperson.

## Übergabe an PowerPoint und Canva

**PowerPoint:** Die Desktop-Version verwenden. Unter
*Bildschirmpräsentation → Monitore* die Beamer-Ausgabe explizit prüfen;
*Referentenansicht* muss auf dem Laptop, die **Folienansicht ohne Notizen**
auf dem Projektor liegen. „Automatisch“ nicht als gesicherte Bildschirmwahl
behandeln. **Zwei getrennte Proben:** (a) PowerPoint-Präsentation vor dem
Timerstart vorbereitet/gestartet, danach Timer davor projizieren und
`Beamer freigeben`; (b) PowerPoint erst nach Freigabe starten. Falls
Variante (a) den Timer vorher verdeckt oder (b) Desktop/Taskleiste zeigt,
genau das notieren, statt eine unterbrechungsfreie Übergabe zu behaupten.
PowerPoint kann Anzeigeeinstellungen beim Start/Ende ändern.

**Canva:** Bei *Präsentationsansicht* öffnet Canva zwei Fenster:
**Teilnehmendenfenster** (ohne Notizen) und **Präsentationsfenster** (mit
Notizen/Vorschau). Vor dem Handoff die tatsächliche Zuordnung auf Laptop
und Projektor prüfen; im Modus *Vollbild* den richtigen Bildschirm separat
testen. Canva kann seine Fensterzuordnung ändern; diese nie stillschweigend
annehmen. Die Offlinefähigkeit des nativen Timers bedeutet **nicht**, dass
Canva ohne Netzwerk zuverlässig lädt. Für W06 den realen Netzwerkzustand
dokumentieren.

Der Timer öffnet weder PowerPoint noch Canva automatisch.
**Beamer freigeben schließt nur das Timerfenster.** Eine kurze
Desktop-Einblendung ist möglich. Ein störungsfreier Wechsel wird erst nach
der tatsächlichen Beobachtung als PASS gewertet.

Offizielle Referenzen:
- [Microsoft: PowerPoint auf mehreren Monitoren](https://support.microsoft.com/en-gb/powerpoint/present-on-multiple-monitors-and-view-speaker-notes-privately)
- [Canva: Präsentationsmodi](https://www.canva.com/de_de/help/presentation-modes/)

## Ergebnis und Stop-Bedingung

| Prüffeld | Status |
| --- | --- |
| Alle acht Pflichttests W01–W08 | **NOT_TESTED** |
| Unbeabsichtigte Desktop-Einblendung / falscher Monitor | **NOT_TESTED** |
| Unterbrechungsfreier Gottesdienst-Probelauf | **NOT_TESTED** |
| **Live-Sonntag-Freigabe** | **NO_GO** |

Ein FAIL bei falschem Monitor, Laptop-Übernahme, fehlender Steuerung,
unerwartetem Timer-Reset oder störendem PowerPoint/Canva-Handoff bedeutet
**NO_GO**. Alle offenen NOT_TESTED-Pflichttests verhindern ebenfalls
eine Freigabe. Ergebnisse nur nach realer Beobachtung eintragen.
