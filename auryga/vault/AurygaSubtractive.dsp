import("stdfaust.lib");
declare name "AurygaSubtractive";

gate = button("gate");
freq = hslider("freq", 440, 20, 20000, 0.01) : si.smoo;
cutoff = hslider("cutoff", 1000, 20, 20000, 0.01) : si.smoo;
res = hslider("res", 1, 0.1, 10, 0.01) : si.smoo;
env_mod = hslider("env_mod", 1000, 0, 10000, 0.01) : si.smoo;
atk = hslider("atk", 0.01, 0.001, 2, 0.001);
dec = hslider("dec", 0.1, 0.001, 2, 0.001);
sus = hslider("sus", 0.5, 0, 1, 0.01);
rel = hslider("rel", 0.1, 0.001, 5, 0.001);
osc_mix = hslider("osc_mix", 0.5, 0, 1, 0.01); // 0 = saw, 1 = square
detune = hslider("detune", 0.01, 0, 0.1, 0.001);

env = en.adsr(atk, dec, sus, rel, gate);
filt_env = en.adsr(atk, dec, 0.1, rel, gate);

osc1 = os.sawtooth(freq) * (1 - osc_mix) + os.square(freq) * osc_mix;
osc2 = os.sawtooth(freq * (1 + detune)) * (1 - osc_mix) + os.square(freq * (1 - detune)) * osc_mix;
sig = (osc1 + osc2) * 0.5;

process = sig : fi.resonlp(cutoff + (filt_env * env_mod), res, 1) * env;
