import("stdfaust.lib");
declare name "AurygaAcid";

// A 303-style Acid Bass Synth
gate = button("gate");
freq = hslider("freq", 110, 20, 2000, 0.01) : si.smoo;
cutoff = hslider("cutoff", 500, 20, 10000, 0.01) : si.smoo;
res = hslider("res", 0.5, 0, 0.98, 0.01) : si.smoo;
env_mod = hslider("env_mod", 0.5, 0, 1, 0.01) : si.smoo;
accent = hslider("accent", 0, 0, 1, 1);

// Oscillator: Pulse with width mod or Sawtooth
osc = os.sawtooth(freq);

// 303 Envelope (Decay only)
env = en.ar(0.001, 0.3, gate);
filt_env = en.ar(0.001, 0.2 + (env_mod * 0.5), gate);

// Diode-ladder style filter emulation (approximate)
process = osc : ve.moog_vcf(res, cutoff * (1 + filt_env * env_mod)) * env * (1 + accent);
