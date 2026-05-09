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
                f"Read song_matrix.json. Define the DSP patch for '{inst}'.\n"
                "CHOOSE ONE OF THESE PRE-BUILT ENGINES FROM THE VAULT:\n"
                "1. AurygaDrum: For Kicks and Snares. Parameters: {freq (20-1000), decay (0.01-2), pitch_mod (0-1000), noise_mix (0-1), noise_cutoff (100-15000), drive (1-10)}\n"
                "2. AurygaSubtractive: For Bass and Leads. Parameters: {freq (20-20k), cutoff (20-20k), res (0.1-10), env_mod (0-10k), atk, dec, sus, rel, osc_mix (0-1), detune (0-0.1)}\n"
                "3. AurygaFM: For Bells and FM Bass/Pads. Parameters: {freq, ratio (0.1-10), index (0-10), atk, dec, sus, rel}\n"
                "4. AurygaMinimoog: Classic 3-oscillator Moog emulation with 24dB ladder filter (from GitHub). Parameters: {freq, cutoff, res (0-1), atk, dec, sus, rel, detune2, detune3}\n"
                "Write a valid JSON object describing the chosen engine and its exact parameter values for this instrument to achieve a Melodic Techno sound.\n"
                "Example Format:\n"
                "{\n"
                '  "engine": "AurygaDrum",\n'
                '  "parameters": {\n'
                '    "freq": 45,\n'
                '    "decay": 0.8,\n'
                '    ... \n'
                '  }\n'
                "}\n"
                f"MANDATORY: Use the `write_file` tool to save exactly ONE file named 'patch_{inst}.json'. Do NOT write Faust code."
            ),
            expected_output=f"patch_{inst}.json written to workspace.",
            agent=agents["sound_designer"],
            context=[theory_task],
        ))

        produce_tasks.append(Task(
            description=(
                f"Read song_matrix.json and patch_{inst}.json.\n"
                f"Write the SuperCollider .scd file for 'seq_{inst}.scd'.\n"
                f"1. Create a SynthDef named \\{inst}_synth that wraps the engine chosen in the JSON (e.g. AurygaDrum.ar(...args)). "
                "   The Faust UGens in SC use the exact parameter names from the Faust file.\n"
                "2. The SynthDef MUST expose the parameters defined in the patch JSON as SynthDef arguments.\n"
                f"3. Create a rhythmic Score sequence for the '{inst}' based on song_matrix.json.\n"
                f"4. The Score OSC messages MUST pass the parameter values from the patch JSON into the synth triggers.\n"
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
