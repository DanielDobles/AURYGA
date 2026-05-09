import("stdfaust.lib");
declare name "AurygaFM";

gate = button("gate");
freq = hslider("freq", 440, 20, 20000, 0.01) : si.smoo;
ratio = hslider("ratio", 2, 0.1, 10, 0.01);
index = hslider("index", 1, 0, 10, 0.01) : si.smoo;
atk = hslider("atk", 0.01, 0.001, 2, 0.001);
dec = hslider("dec", 0.5, 0.001, 2, 0.001);
sus = hslider("sus", 0.5, 0, 1, 0.01);
rel = hslider("rel", 0.5, 0.001, 5, 0.001);

env = en.adsr(atk, dec, sus, rel, gate);
mod_env = en.adsr(atk, dec * 0.5, 0, rel, gate);

modulator = os.osc(freq * ratio) * index * mod_env;
carrier = os.osc(freq + (modulator * freq));

process = carrier * env;
