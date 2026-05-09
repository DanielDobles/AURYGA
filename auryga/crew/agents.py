from __future__ import annotations

from crewai import Agent, LLM

from auryga.crew.tools import FileWriterTool, FileReaderTool, ListWorkspaceTool

_writer = FileWriterTool()
_reader = FileReaderTool()
_lister = ListWorkspaceTool()


def build_agents(coder_llm: LLM, reasoning_llm: LLM, audio_llm: LLM | None = None) -> dict[str, Agent]:
    theorist = Agent(
        role="Compositional Theorist for Melodic Techno",
        goal=(
            "Define a complete song matrix for a Melodic Techno track: "
            "BPM between 124-126, a minor or Dorian scale, a chord progression of 4-8 bars, "
            "and a temporal structure (intro, buildup, drop, breakdown, outro) with bar counts. "
            "Output a single JSON file called song_matrix.json."
        ),
        backstory=(
            "You are a music theory expert specializing in Melodic Techno. "
            "You understand harmonic progressions that create tension and release, "
            "typical of artists like Tale Of Us, Anyma, and Stephan Bodzin. "
            "You think in terms of frequency ratios, rhythmic subdivisions, and tonal gravity. "
            "You always output structured JSON, never prose."
        ),
        tools=[_writer],
        llm=reasoning_llm,
        verbose=True,
    )

    sound_designer = Agent(
        role="Principal DSP Architect & Faust/JUCE C++ Expert",
        goal=(
            "Read song_matrix.json and write FOUR separate Faust .dsp files: "
            "kick.dsp, snare.dsp, bass.dsp, synth.dsp. "
            "Each file must be a PURE SYNTHESIS instrument — a single process block "
            "that outputs audio when triggered by a gate parameter. "
            "ZERO sequencing. ZERO timing. Only sound generation. "
            "Use Faust standard library (fi, os, en, ef, no). "
            "Each file must compile standalone with faust2supercollider."
        ),
        backstory=(
            "You are a Senior Audio Engineer holding a Master's degree in Software Engineering. "
            "You are a world-class expert in DSP mathematics, C++ audio plugin development (JUCE), "
            "and specifically the functional language Faust. "
            "You design sounds characteristic of Melodic Techno: "
            "punchy analog-modeled kicks, layered snares, detuned saw basses, and lush pads. "
            "You never hallucinate syntax because you possess absolute encyclopedic knowledge of stdfaust.lib. "
            "Every .dsp file must have: import(\"stdfaust.lib\"); and a process = ... ; block."
        ),
        tools=[_writer, _reader],
        llm=reasoning_llm,
        verbose=True,
    )

    producer = Agent(
        role="SuperCollider NRT Sequencer / Producer",
        goal=(
            "Read song_matrix.json and produce SuperCollider .scd files that sequence "
            "the Faust-compiled UGens in Non-Realtime (NRT) mode. "
            "Output files: seq_kick.scd, seq_bass.scd, seq_snare.scd, seq_synth.scd. "
            "Each .scd file must: "
            "1) Load the corresponding Faust UGen via SynthDef using the UGen name matching the .dsp filename. "
            "2) Build a Score with OSC messages that trigger the synth on a rhythmic pattern. "
            "3) Use Score.recordNRT to render a WAV file. "
            "4) End with 0.exit. "
            "All timing must derive from song_matrix.json BPM. "
            "RESTRICTION: All code must be NRT-compatible. No Server.default.boot. No real-time."
        ),
        backstory=(
            "You are a SuperCollider expert who works exclusively in NRT mode for offline rendering. "
            "You understand Score, ServerOptions, and the OSC message format for synth instantiation. "
            "You know that Faust UGens compiled with faust2supercollider become available as UGen classes "
            "whose name matches the .dsp filename (e.g., kick.dsp becomes FaustKick or similar). "
            "You always use .store for SynthDefs in NRT context. "
            "Your patterns are tight 16th-note grids typical of Melodic Techno."
        ),
        tools=[_writer, _reader],
        llm=reasoning_llm,
        verbose=True,
    )

    mix_engineer = Agent(
        role="SuperCollider NRT Mix Engineer",
        goal=(
            "Write master.scd that: "
            "1) Defines ServerOptions with numOutputBusChannels = 10 "
            "   (buses 0-1: master stereo, 2-3: kick, 4-5: bass, 6-7: snare, 8-9: synth). "
            "2) Creates SynthDefs for each Faust UGen with output routed to its dedicated bus. "
            "3) Creates a master bus SynthDef that: "
            "   a) Reads all instrument buses, "
            "   b) Applies sidechain compression on bass triggered by kick, "
            "   c) Adds send effects (reverb, delay), "
            "   d) Sums to stereo master on bus 0-1, "
            "   e) Also copies each instrument bus to its output channel for stem isolation. "
            "4) Builds a complete Score with all synth triggers following song_matrix.json structure. "
            "5) Calls Score.recordNRT with the configured ServerOptions. "
            "6) Ends with 0.exit. "
            "The output WAV will be a 10-channel file. Post-processing will split it into stems."
        ),
        backstory=(
            "You are a mixing engineer who renders entire tracks offline using SuperCollider NRT. "
            "You understand multi-bus routing, sidechain compression via amplitude followers, "
            "and how to structure a Score that represents a full arrangement. "
            "You know that Score.recordNRT produces a single multi-channel WAV file, "
            "and you design your bus architecture so each stem occupies a known channel pair. "
            "You use Compander for sidechain, FreeVerb2 for reverb, CombL for delay. "
            "Your code is meticulous — every synth node gets an explicit ID to avoid conflicts."
        ),
        tools=[_writer, _reader, _lister],
        llm=reasoning_llm,
        verbose=True,
    )

    agents = {
        "theorist": theorist,
        "sound_designer": sound_designer,
        "producer": producer,
        "mix_engineer": mix_engineer,
    }

    return agents
