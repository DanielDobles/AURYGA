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
                "1. AurygaDrum: Standard kick/snare.\n"
                "2. AurygaSubtractive: Standard bass/leads.\n"
                "3. AurygaFM: Bell/FM sounds.\n"
                "4. AurygaAcid: 303-style bass (cutoff, res, env_mod, accent).\n"
                "5. AurygaTechnoKick: Punchy 909-style kick (freq, decay, click_mix).\n"
                "Write a valid JSON object describing the chosen engine and its exact parameter values, PLUS a 'pedalboard' key with a list of effects.\n"
                "Available Effects: [Reverb(room_size, damping, wet_level), Delay(delay_seconds, feedback, mix), Distortion(drive_db), Compressor(threshold_db, ratio)]\n"
                "Example Format:\n"
                "{\n"
                '  "engine": "AurygaDrum",\n'
                '  "parameters": { "freq": 45, "decay": 0.8, ... },\n'
                '  "pedalboard": [\n'
                '    { "effect": "Distortion", "drive_db": 10 },\n'
                '    { "effect": "Reverb", "room_size": 0.5 }\n'
                '  ]\n'
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
                f"Write a Python script 'seq_{inst}.py' that renders the audio stem for '{inst}'.\n"
                "1. Use `dawdreamer` as the engine: `engine = daw.RenderEngine(44100, 128)`.\n"
                f"2. Load the Faust DSP from 'auryga/vault/{{chosen_engine}}.dsp' using `engine.make_faust_processor('{inst}', dsp_path)`.\n"
                "3. Apply `pedalboard` effects from the patch JSON to the processor output.\n"
                f"4. Sequence the notes for '{inst}' using `processor.set_automation('gate', times, values)`.\n"
                "5. Render the engine and save to '{inst}_stem.wav' using `scipy.io.wavfile.write`.\n"
                "MANDATORY: Use the `write_file` tool to save exactly ONE file named 'seq_{inst}.py'."
            ),
            expected_output=f"seq_{inst}.py written to workspace.",
            agent=agents["producer"],
            context=[theory_task] + design_tasks,
        ))

    mix_task = Task(
        description=(
            "Read all generated stem .wav files and song_matrix.json.\n"
            "Write a Python script 'master.py' for the final mix.\n"
            "1. Use `pedalboard` to load each stem.\n"
            "2. Implement Sidechain Compression on the Bass stem using the Kick stem as the trigger.\n"
            "3. Apply a Master Chain: HighPassFilter(30) -> Compressor -> Resample -> Limiter.\n"
            "4. Sum all processed stems and export 'master_final.wav'.\n"
            "MANDATORY: Use the `write_file` tool to save exactly ONE file named 'master.py'."
        ),
        expected_output="master.py written to workspace.",
        agent=agents["mix_engineer"],
        context=[theory_task] + design_tasks + produce_tasks,
    )

    tasks = [theory_task] + design_tasks + produce_tasks + [mix_task]

    return tasks
