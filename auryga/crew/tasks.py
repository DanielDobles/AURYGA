from __future__ import annotations

from crewai import Agent, Task


def build_tasks(agents: dict[str, Agent]) -> list[Task]:
    theory_task = Task(
        description=(
            "Create a song_matrix.json for a Melodic Techno track.\n"
            "Requirements:\n"
            "- BPM: choose between 124, 125, or 126\n"
            "- Scale: choose a minor, Dorian, or Phrygian scale with a specific root note\n"
            "- Chord progression: 4 to 8 chords using Roman numeral notation, "
            "include the actual MIDI note numbers for each chord\n"
            "- Song structure: define sections (intro, buildup, drop, breakdown, outro) "
            "with bar counts and which instruments play in each section\n"
            "- Tempo: include beat duration in seconds (60/BPM)\n\n"
            "Write the file using the write_file tool with filename 'song_matrix.json'.\n"
            "Output ONLY valid JSON. No comments inside the JSON."
        ),
        expected_output="song_matrix.json written to workspace with complete song parameters.",
        agent=agents["theorist"],
    )

    design_task = Task(
        description=(
            "Read song_matrix.json using the read_file tool.\n"
            "Then write FOUR separate Faust .dsp files:\n\n"
            "1. kick.dsp — Analog-modeled kick drum:\n"
            "   - Sine oscillator with pitch envelope (150Hz → 45Hz)\n"
            "   - Amplitude envelope (fast attack, ~200ms decay)\n"
            "   - Soft clipping / saturation for punch\n"
            "   - Gate input parameter: gate = checkbox(\"gate\");\n\n"
            "2. snare.dsp — Layered snare:\n"
            "   - Noise burst through resonant bandpass filter\n"
            "   - Sine body at ~180Hz\n"
            "   - Combined with amplitude envelope\n"
            "   - Gate input parameter\n\n"
            "3. bass.dsp — Melodic bass:\n"
            "   - Detuned sawtooth oscillators\n"
            "   - Low-pass filter with envelope\n"
            "   - Frequency input parameter: freq = hslider(\"freq\", 55, 20, 500, 0.01);\n"
            "   - Gate input parameter\n\n"
            "4. synth.dsp — Melodic pad/lead:\n"
            "   - Multiple detuned oscillators\n"
            "   - Chorus or phaser effect\n"
            "   - Filter with LFO modulation\n"
            "   - Frequency and gate input parameters\n\n"
            "CRITICAL RULES:\n"
            "- Every file MUST start with: import(\"stdfaust.lib\");\n"
            "- Every file MUST end with: process = ...;\n"
            "- ZERO sequencing or timing code\n"
            "- Use write_file tool for each file separately"
        ),
        expected_output="Four .dsp files (kick.dsp, snare.dsp, bass.dsp, synth.dsp) written to workspace.",
        agent=agents["sound_designer"],
        context=[theory_task],
    )

    produce_task = Task(
        description=(
            "Read song_matrix.json and all .dsp files from workspace.\n"
            "Write FOUR SuperCollider .scd files for NRT sequencing:\n\n"
            "1. seq_kick.scd — Kick pattern:\n"
            "   - SynthDef that wraps the Faust kick UGen\n"
            "   - Score with kick triggers on beats (4/4 pattern)\n"
            "   - Use Score.recordNRT to render to 'kick_stem.wav'\n\n"
            "2. seq_snare.scd — Snare pattern:\n"
            "   - Snare hits on beats 2 and 4\n"
            "   - Plus ghost notes on some 16th subdivisions\n\n"
            "3. seq_bass.scd — Bass sequence:\n"
            "   - Follow chord progression from song_matrix.json\n"
            "   - Rhythmic pattern (not sustained notes)\n\n"
            "4. seq_synth.scd — Synth/pad sequence:\n"
            "   - Chord voicings from song_matrix.json\n"
            "   - Longer sustain, pad-style\n\n"
            "CRITICAL RULES FOR EVERY .scd FILE:\n"
            "- Calculate beat duration: beatDur = 60 / BPM\n"
            "- Use Score([ ... ]) with explicit OSC messages:\n"
            "  [time, [\\s_new, \\synthName, nodeID, 0, 0, \\param, value]]\n"
            "- Configure ServerOptions: numOutputBusChannels = 2, sampleRate = 44100\n"
            "- Call Score.recordNRT(oscFilePath, outputFilePath, ...)\n"
            "- END every file with: 0.exit;\n"
            "- Do NOT use Server.default, s.boot, or any real-time server commands\n"
            "- Do NOT use Pbind, Pdef, or Pattern classes (they require a running server)\n"
            "- Use write_file tool for each file"
        ),
        expected_output="Four seq_*.scd files written to workspace.",
        agent=agents["producer"],
        context=[theory_task, design_task],
    )

    mix_task = Task(
        description=(
            "Read song_matrix.json and list all workspace files.\n"
            "Write master.scd — the final mix and render script.\n\n"
            "ARCHITECTURE:\n"
            "- ServerOptions: numOutputBusChannels = 10, sampleRate = 44100\n"
            "  Channels: 0-1 master, 2-3 kick, 4-5 bass, 6-7 snare, 8-9 synth\n\n"
            "- SynthDef \\kick: Faust kick UGen → Out.ar(2, sig.dup)\n"
            "- SynthDef \\snare: Faust snare UGen → Out.ar(6, sig.dup)\n"
            "- SynthDef \\bass: Faust bass UGen → Out.ar(4, sig.dup)\n"
            "- SynthDef \\synth: Faust synth UGen → Out.ar(8, sig.dup)\n\n"
            "- SynthDef \\masterBus (runs on group AFTER instruments):\n"
            "  a) Read kick from bus 2-3\n"
            "  b) Read bass from bus 4-5, apply sidechain compression using Compander "
            "     with kick as control signal (threshold: -20dB, ratio: 4:1)\n"
            "  c) Read snare from bus 6-7\n"
            "  d) Read synth from bus 8-9, add FreeVerb2 (mix: 0.3, room: 0.7) "
            "     and CombL delay (delaytime: 3/4 beat, decaytime: 2s)\n"
            "  e) Sum all to stereo and write to bus 0-1\n"
            "  f) Also pass-through each instrument bus to its output channel pair for stems\n\n"
            "- Build a complete Score:\n"
            "  - First message: allocate buses and groups\n"
            "  - Schedule masterBus synth at time 0 (tail of group)\n"
            "  - Schedule instrument synths following the song structure from song_matrix.json\n"
            "  - Total duration = sum of all section bar counts × 4 × beatDur\n\n"
            "- Call Score.recordNRT:\n"
            "  outputFilePath: \"master_10ch.wav\"\n"
            "  headerFormat: \"wav\", sampleFormat: \"int24\"\n"
            "  options: configured ServerOptions\n\n"
            "- End with 0.exit;\n\n"
            "Write using write_file tool with filename 'master.scd'."
        ),
        expected_output="master.scd written to workspace with complete NRT mix and stem rendering.",
        agent=agents["mix_engineer"],
        context=[theory_task, design_task, produce_task],
    )

    qa_task = Task(
        description=(
            "Audit ALL files in ./workspace/.\n"
            "Use list_workspace to get the file list, then read_file on each one.\n\n"
            "FOR EACH .dsp FILE CHECK:\n"
            "- import(\"stdfaust.lib\"); is present\n"
            "- process = ... ; exists\n"
            "- All parentheses () are balanced\n"
            "- All braces {} are balanced\n"
            "- No markdown artifacts (```, #, **) remain\n"
            "- Semicolons terminate statements\n\n"
            "FOR EACH .scd FILE CHECK:\n"
            "- 0.exit; is present (CRITICAL — without it sclang hangs forever)\n"
            "- All parentheses (), braces {}, brackets [] are balanced\n"
            "- Score.recordNRT or Score.new is called\n"
            "- ServerOptions is configured\n"
            "- No markdown artifacts remain\n"
            "- SynthDef names are quoted with backslash (\\name)\n\n"
            "FOR song_matrix.json:\n"
            "- Valid JSON (no trailing commas, no comments)\n\n"
            "If ANY issue is found: fix it and rewrite the file using write_file.\n"
            "Report a summary of all files checked and all fixes applied."
        ),
        expected_output="All files validated and corrected. Summary of checks and fixes.",
        agent=agents["qa_linter"],
        context=[design_task, produce_task, mix_task],
    )

    tasks = [theory_task, design_task, produce_task, mix_task, qa_task]

    if "audio_critic" in agents:
        audio_task = Task(
            description=(
                "After the remote pipeline has rendered the WAV files, "
                "analyze the audio output.\n\n"
                "Use list_workspace to find all .wav files.\n"
                "For each WAV file, provide a structured analysis:\n\n"
                "1. KICK ANALYSIS:\n"
                "   - Punch and transient quality (1-10)\n"
                "   - Sub-bass presence around 40-60Hz\n"
                "   - Does it cut through the mix?\n\n"
                "2. BASS ANALYSIS:\n"
                "   - Harmonic richness and movement (1-10)\n"
                "   - Sidechain ducking effectiveness\n"
                "   - Frequency separation from kick\n\n"
                "3. SNARE/PERCUSSION ANALYSIS:\n"
                "   - Crispness and presence (1-10)\n"
                "   - Groove and swing quality\n\n"
                "4. SYNTH/PAD ANALYSIS:\n"
                "   - Spatial quality and width (1-10)\n"
                "   - Harmonic content and texture\n"
                "   - Effect quality (reverb, delay)\n\n"
                "5. OVERALL MIX:\n"
                "   - Frequency balance (1-10)\n"
                "   - Dynamic range\n"
                "   - Does it sound like professional Melodic Techno?\n\n"
                "Write your analysis using write_file with filename 'audio_critique.json'."
            ),
            expected_output="Structured audio analysis with scores for each element.",
            agent=agents["audio_critic"],
            context=[mix_task, qa_task],
        )
        tasks.append(audio_task)

    return tasks
