import("stdfaust.lib");
declare name "AurygaTechnoKick";

// A 909-style Techno Kick Drum
gate = button("gate");
freq = hslider("freq", 50, 20, 200, 0.01);
decay = hslider("decay", 0.4, 0.01, 2, 0.01);
click_mix = hslider("click_mix", 0.2, 0, 1, 0.01);

// Pitch Envelope (fast drop)
pitch_env = en.ar(0.001, 0.05, gate);
f = freq * (1 + pitch_env * 5);

// Oscillator
body = os.osc(f);

// Click (white noise transient)
click = no.white_noise : fi.lowpass(1, 5000) * en.ar(0.001, 0.01, gate);

// Main Amp Envelope
env = en.ar(0.001, decay, gate);

process = (body + click * click_mix) : ef.cubicnl(0.5, 0) * env;
