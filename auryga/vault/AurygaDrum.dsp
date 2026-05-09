import("stdfaust.lib");
declare name "AurygaDrum";

gate = button("gate");
freq = hslider("freq", 50, 20, 1000, 0.01);
decay = hslider("decay", 0.5, 0.01, 2, 0.01);
pitch_mod = hslider("pitch_mod", 100, 0, 1000, 0.1);
noise_mix = hslider("noise_mix", 0.1, 0, 1, 0.01);
noise_cutoff = hslider("noise_cutoff", 5000, 100, 15000, 1);
drive = hslider("drive", 1, 1, 10, 0.01);

amp_env = en.ar(0.001, decay, gate);
p_env = en.ar(0.001, decay * 0.2, gate);

body_freq = freq + (p_env * pitch_mod);
body = os.osc(body_freq);

ns = no.noise : fi.lowpass(2, noise_cutoff);
sig = (body * (1 - noise_mix) + ns * noise_mix) * amp_env;

// Soft clipping saturation
process = ef.cubicnl(drive, 0.1, sig);
