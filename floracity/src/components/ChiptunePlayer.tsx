import React from 'react';
import WebView from 'react-native-webview';

// Minimal silent WAV (44 bytes) — playing this unlocks iOS AudioContext autoplay
const SILENT_WAV =
  'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA=';

const HTML = `<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>html,body{margin:0;padding:0;overflow:hidden;}</style>
</head>
<body>
<!--
  Silent audio element: autoplay + mediaPlaybackRequiresUserAction=false
  unlocks the WKWebView audio session on iOS so AudioContext can run freely.
-->
<audio id="u" autoplay loop preload="auto"
  src="${SILENT_WAV}" style="display:none"></audio>

<script>
(function() {
  var AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return;
  var ctx = new AC();

  var B = 60 / 160;  // quarter note at 160 BPM
  var Q = B, H = B*2, E = B/2;

  var f = {
    C3:130.81,D3:146.83,E3:164.81,F3:174.61,G3:196.00,A3:220.00,
    C4:261.63,D4:293.66,E4:329.63,F4:349.23,G4:392.00,A4:440.00,B4:493.88,
    C5:523.25,D5:587.33,E5:659.25,F5:698.46,G5:783.99,A5:880.00,
    r:0
  };

  function note(freq, t, dur, vol, type) {
    if (!freq) return;
    var o = ctx.createOscillator();
    var g = ctx.createGain();
    o.type = type || 'square';
    o.frequency.value = freq;
    g.gain.setValueAtTime(vol, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + Math.max(dur * 0.86, dur - 0.02));
    o.connect(g); g.connect(ctx.destination);
    o.start(t); o.stop(t + dur);
  }

  // ── Melody A (8 bars) ──────────────────────────────────────────────────
  var MEL_A = [
    [f.E5,Q],[f.G5,Q],[f.A5,H],
    [f.G5,Q],[f.E5,Q],[f.C5,H],
    [f.D5,Q],[f.F5,Q],[f.G5,Q],[f.E5,Q],
    [f.C5,H],[f.r,H],
    [f.G4,Q],[f.A4,Q],[f.C5,Q],[f.E5,Q],
    [f.D5,Q],[f.C5,Q],[f.B4,H],
    [f.A4,Q],[f.B4,Q],[f.C5,Q],[f.D5,Q],
    [f.E5,H],[f.C5,H],
  ];

  // ── Melody B / bridge (8 bars) ─────────────────────────────────────────
  var MEL_B = [
    [f.F5,Q],[f.E5,Q],[f.D5,Q],[f.C5,Q],
    [f.B4,H],[f.G4,H],
    [f.A4,Q],[f.B4,Q],[f.C5,Q],[f.A4,Q],
    [f.G4,H],[f.r,H],
    [f.C5,Q],[f.D5,Q],[f.E5,Q],[f.G5,Q],
    [f.F5,Q],[f.E5,Q],[f.D5,H],
    [f.C5,Q],[f.B4,Q],[f.A4,Q],[f.G4,Q],
    [f.C5,H],[f.C5,H],
  ];

  // ── Bass (16 bars, square) ─────────────────────────────────────────────
  var BASS = [
    [f.C3,H],[f.G3,H],[f.A3,H],[f.E3,H],
    [f.F3,H],[f.C3,H],[f.G3,H],[f.G3,H],
    [f.C3,H],[f.G3,H],[f.A3,H],[f.E3,H],
    [f.F3,H],[f.C3,H],[f.G3,H],[f.G3,H],
    [f.F3,H],[f.C3,H],[f.G3,H],[f.D3,H],
    [f.A3,H],[f.E3,H],[f.G3,H],[f.G3,H],
    [f.C3,H],[f.G3,H],[f.A3,H],[f.F3,H],
    [f.G3,H],[f.C3,H],[f.C3,H],[f.G3,H],
  ];

  // ── Harmony (16 bars, triangle) ────────────────────────────────────────
  var HARMONY = [
    [f.C5,H],[f.E5,H],[f.A4,H],[f.C5,H],
    [f.D5,H],[f.F4,H],[f.C5,H],[f.r,H],
    [f.E4,H],[f.C5,H],[f.B4,H],[f.G4,H],
    [f.A4,H],[f.D4,H],[f.G4,H],[f.E4,H],
    [f.F4,H],[f.C5,H],[f.G4,H],[f.D5,H],
    [f.A4,H],[f.E5,H],[f.G4,H],[f.r,H],
    [f.C5,H],[f.E4,H],[f.A4,H],[f.F4,H],
    [f.G4,H],[f.E4,H],[f.C5,H],[f.G4,H],
  ];

  function sched(pat, t0, vol, type) {
    var t = t0;
    for (var i = 0; i < pat.length; i++) {
      note(pat[i][0], t, pat[i][1], vol, type);
      t += pat[i][1];
    }
  }

  function dur(pat) {
    var d = 0;
    for (var i = 0; i < pat.length; i++) d += pat[i][1];
    return d;
  }

  var fullMelody = MEL_A.concat(MEL_B);
  var loopDur = dur(fullMelody); // 24 s
  var nextStart = 0;
  var started = false;

  function scheduleLoop() {
    sched(fullMelody, nextStart, 0.11, 'square');
    sched(BASS,       nextStart, 0.07, 'square');
    sched(HARMONY,    nextStart, 0.05, 'triangle');
    nextStart += loopDur;
    setTimeout(scheduleLoop, (loopDur - 1.5) * 1000);
  }

  function start() {
    if (started) return;
    started = true;
    nextStart = ctx.currentTime + 0.05;
    scheduleLoop();
  }

  function tryResume() {
    if (ctx.state === 'running') { start(); return; }
    ctx.resume().then(start).catch(function() {});
  }

  // ── iOS unlock via silent <audio> element ──────────────────────────────
  var audio = document.getElementById('u');
  if (audio) {
    audio.addEventListener('play', tryResume, { once: true });
    audio.play().then(tryResume).catch(function() {});
  }

  // Direct attempt (works on Android immediately)
  tryResume();

  // Fallback: any touch on this page also unlocks
  document.addEventListener('touchstart', tryResume, { once: true });
})();
</script>
</body>
</html>`;

export function ChiptunePlayer() {
  return (
    // Positioned above the visible area so it is off-screen but still live
    <WebView
      source={{ html: HTML }}
      style={{ position: 'absolute', top: -200, left: 0, width: 150, height: 100 }}
      allowsInlineMediaPlayback
      mediaPlaybackRequiresUserAction={false}
      javaScriptEnabled
      scrollEnabled={false}
    />
  );
}
