from __future__ import annotations

import numpy as np

from app.simulation.world_state import Meme, WorldState, clamp, clamp_array


def update_social_network(state: WorldState) -> None:
    citizens = state.citizens
    rng = state.rng(72)
    if not state.memes:
        return

    district_ideology = np.array([district.political_leaning for district in state.districts], dtype=np.float32)
    district_stress = np.zeros(len(state.districts), dtype=np.float32)
    counts = np.bincount(citizens.home_district, minlength=len(state.districts))
    stress_sums = np.bincount(citizens.home_district, weights=citizens.stress, minlength=len(state.districts))
    district_stress = np.divide(stress_sums, np.maximum(1, counts))

    meme_scores = []
    for meme in state.memes:
        alignment = 1 - np.abs(citizens.ideology - meme.ideology) / 2
        social_heat = district_stress[citizens.home_district] * meme.outrage
        novelty_decay = max(0.08, meme.novelty - meme.age * 0.006)
        score = alignment * 0.38 + social_heat * 0.32 + citizens.media_susceptibility * 0.22 + novelty_decay * 0.08
        meme_scores.append(score)
    scores = np.vstack(meme_scores)
    choices = np.argmax(scores + rng.normal(0, 0.025, scores.shape), axis=0)
    adoption_probability = np.clip(np.max(scores, axis=0) * 0.08, 0.01, 0.18)
    adopting = rng.random(citizens.size) < adoption_probability
    citizens.meme_id[adopting] = choices[adopting].astype(np.int16)

    for meme in state.memes:
        meme.age += 1
        adopted = citizens.meme_id == meme.id
        raw_adoption = float(np.mean(adopted)) if citizens.size else 0.0
        meme.adoption = clamp(meme.adoption * 0.76 + raw_adoption * 0.24)
        meme.outrage = clamp(meme.outrage * 0.98 + float(np.mean(citizens.stress[adopted])) * 0.02 if adopted.any() else meme.outrage * 0.98)
        meme.novelty = clamp(meme.novelty * 0.992)

    if state.tick > 0 and state.tick % 36 == 0:
        parent = max(state.memes, key=lambda item: item.adoption * (0.5 + item.outrage))
        new_id = max(meme.id for meme in state.memes) + 1
        fragments = ["Ghost", "Patch", "Rent", "Signal", "Strike", "Solar", "Grid", "Human"]
        state.memes.append(
            Meme(
                id=new_id,
                text=f"{rng.choice(fragments)} {rng.choice(fragments)} {int(rng.integers(10, 99))}",
                ideology=float(np.clip(parent.ideology + rng.normal(0, parent.mutation), -1, 1)),
                outrage=float(np.clip(parent.outrage + rng.normal(0, 0.08), 0.05, 1)),
                novelty=0.95,
                adoption=0.01,
                mutation=float(np.clip(parent.mutation + rng.normal(0, 0.02), 0.02, 0.18)),
            )
        )
        state.memes = sorted(state.memes, key=lambda meme: meme.adoption + meme.novelty * 0.1, reverse=True)[:10]

    dominant_ideologies = np.array([meme.ideology for meme in state.memes], dtype=np.float32)
    selected_meme = np.clip(citizens.meme_id, 0, len(state.memes) - 1)
    citizens.ideology = np.clip(citizens.ideology * 0.996 + dominant_ideologies[selected_meme] * 0.004, -1, 1).astype(np.float32)
    citizens.stress = clamp_array(citizens.stress + citizens.media_susceptibility * 0.003 * np.maximum(0, np.abs(citizens.ideology)))

    state.metrics["polarization"] = float(np.std(citizens.ideology) * 1.8)

