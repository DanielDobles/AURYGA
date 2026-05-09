import("stdfaust.lib");
declare name "AurygaMinimoog";

// Adapted from the grame-cncm/faust/examples/synthesizers repository
// A classic 3-oscillator virtual analog architecture with a 24dB ladder filter

gate = button("gate");
freq = hslider("freq", 440, 20, 20000, 0.01) : si.smoo;
cutoff = hslider("cutoff", 2000, 20, 20000, 0.01) : si.smoo;
res = hslider("res", 0.5, 0, 1, 0.01) : si.smoo;

atk = hslider("atk", 0.01, 0.001, 2, 0.001);
dec = hslider("dec", 0.1, 0.001, 2, 0.001);
sus = hslider("sus", 0.5, 0, 1, 0.01);
rel = hslider("rel", 0.1, 0.001, 5, 0.001);

detune2 = hslider("detune2", 1.01, 0.5, 2.0, 0.001);
detune3 = hslider("detune3", 0.99, 0.5, 2.0, 0.001);

// Envelopes
env = en.adsr(atk, dec, sus, rel, gate);
filt_env = en.adsr(atk, dec, 0.1, rel, gate);

// 3 Oscillators (Moog style)
osc1 = os.sawtooth(freq);
osc2 = os.sawtooth(freq * detune2);
osc3 = os.square(freq * detune3);

sig = (osc1 + osc2 + osc3) / 3.0;

// Moog 24dB Ladder Filter (from ve.moog_vcf in stdfaust.lib)
process = sig : ve.moog_vcf(res, cutoff * (1 + filt_env)) * env;
