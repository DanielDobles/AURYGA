from __future__ import annotations

from crewai import Agent, Task


def build_tasks(agents: dict[str, Agent]) -> list[Task]:
    theory_task = Task(
        description=(
            "Create a song_matrix.json for a Melodic Techno track.\n"
            "User's creative direction: {prompt}\n"
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

    design_tasks = []
    produce_tasks = []
    instruments = ["kick", "snare", "bass", "synth"]

    for inst in instruments:
        design_tasks.append(Task(
            description=(
                f"Read song_matrix.json. Write the Faust .dsp file for '{inst}.dsp'.\n"
                f"MANDATORY METADATA: You MUST include `declare name \"{inst}\";` right after the import. This is strictly required for SuperCollider binding.\n"
                "CRITICAL FAUST SYNTAX RULES (NO HALLUCINATIONS):\n"
                "- Oscillators: Use `os.sawtooth(freq)`, `os.osc(freq)`, or `no.noise`.\n"
                "- Envelopes: Use `en.adsr(attack, decay, sustain, release, gate)`. NO `envelope()`.\n"
                "- Filters: Use `fi.lowpass(order, cutoff)`. Pipe it, do not pass signal as arg.\n"
                "- Smoothing: Use `si.smoo`.\n"
                "- Routing: `process = os.sawtooth(freq) : fi.lowpass(2, cutoff) * en.adsr(0.1,0.1,0.5,0.1,gate);`\n"
                "- Every file MUST start with: `import(\"stdfaust.lib\");`\n"
                "- Every file MUST end with a valid `process = ...;` block.\n"
                f"MANDATORY: Use the `write_file` tool to save exactly ONE file named '{inst}.dsp'."
            ),
            expected_output=f"{inst}.dsp written to workspace.",
            agent=agents["sound_designer"],
            context=[theory_task],
        ))

        produce_tasks.append(Task(
            description=(
                f"Read song_matrix.json and {inst}.dsp. Write the SuperCollider .scd file for 'seq_{inst}.scd'.\n"
                f"1. SynthDef MUST wrap the Faust UGen named EXACTLY '{inst}' (from the declare name directive).\n"
                "2. Create a rhythmic sequence based on song_matrix.json.\n"
                "CRITICAL RULES:\n"
                "- Calculate beat duration: beatDur = 60 / BPM\n"
                "- Use Score([ ... ]) with explicit OSC messages.\n"
                "- Configure ServerOptions: numOutputBusChannels = 2, sampleRate = 44100\n"
                f"- Call Score.recordNRT(oscFilePath, '{inst}_stem.wav', ...)\n"
                "- END the file with: 0.exit;\n"
                "- Do NOT use Pbind, Pdef, or Pattern classes.\n"
                f"MANDATORY: Use the `write_file` tool to save exactly ONE file named 'seq_{inst}.scd'."
            ),
            expected_output=f"seq_{inst}.scd written to workspace.",
            agent=agents["producer"],
            context=[theory_task] + design_tasks,
        ))

    mix_task = Task(
        description=(
            "Read song_matrix.json and list all workspace files.\n"
            "Write master.scd — the final mix and render script.\n\n"
            "ARCHITECTURE:\n"
            "- ServerOptions: numOutputBusChannels = 10, sampleRate = 44100\n"
            "  Channels: 0-1 master, 2-3 kick, 4-5 bass, 6-7 snare, 8-9 synth\n\n"
            "- SynthDef \\masterBus (runs on group AFTER instruments):\n"
            "  a) Read kick from bus 2-3\n"
            "  b) Read bass from bus 4-5, apply sidechain compression using Compander\n"
            "  c) Read snare from bus 6-7\n"
            "  d) Read synth from bus 8-9, add FreeVerb2 and CombL delay\n"
            "  e) Sum all to stereo and write to bus 0-1\n"
            "  f) Also pass-through each instrument bus to its output channel pair\n\n"
            "- Call Score.recordNRT:\n"
            "  outputFilePath: \"master_10ch.wav\"\n"
            "- End with 0.exit;\n\n"
            "MANDATORY: Use the `write_file` tool with filename 'master.scd'."
        ),
        expected_output="master.scd written to workspace with complete NRT mix and stem rendering.",
        agent=agents["mix_engineer"],
        context=[theory_task] + design_tasks + produce_tasks,
    )

    tasks = [theory_task] + design_tasks + produce_tasks + [mix_task]

    return tasks
