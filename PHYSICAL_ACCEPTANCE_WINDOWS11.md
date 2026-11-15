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

## Übergabe an PowerPoint und Canva

**PowerPoint:** Über *Bildschirmpräsentation → Monitore* die tatsächliche
Beamer-Ausgabe wählen; *Referentenansicht* auf dem Laptop und die
Publikumsfolie auf dem Beamer vorab bestätigen. „Automatisch“ nicht als
gesicherte Bildschirmwahl behandeln. PowerPoint kann Anzeigeeinstellungen
beim Start oder Ende einer Präsentation ändern.

**Canva:** Bei *Präsentationsansicht* öffnet Canva ein getrenntes
Publikums- und Präsentationsfenster. Das Publikumsfenster muss vor der
Übergabe dem Beamer zugeordnet sein; bei *Vollbild* den richtigen Bildschirm
überprüfen.

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
