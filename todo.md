### Geschwindigkeit erhöhen
FFmpeg-Hardware-Encoding (größter Gewinn, kaum Qualitätsverlust)
Statt den fertigen Video-Stream in Python frame-by-frame zu schreiben, 
kann man FFmpeg mit Hardware-Encoder nutzen — h264_nvenc (NVIDIA), h264_amf (AMD) oder h264_videotoolbox (Apple).
Das lagert die Encodierung auf die GPU aus und ist oft 3–5× schneller. Fallback auf Software-Encoder wenn keine GPU verfügbar.

### Output Option
Output Option hinzufügen (Kein timer, kein Abschluss Bild)
es soll nur das Video/Bild mit Musik und einem Outro Titel in der Mitte angezeigt werden
und eine fate in fate out Sekunden Einstellung

### Sound hinzufügen
Wenn das Video fertig gerendert ist oder ein fehler beim rendern passiert sollen töne kommen.
Den soll man in den einstellungen auch ein/aus schalten können

### Fertig pop-up
Das fertig/fehler popup beim rendern soll abgerundete ecken haben